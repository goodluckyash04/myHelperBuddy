"""
Authentication and user management views.

This module handles all authentication-related functionality including:
- User login, signup, and logout
- Password management (change, forgot password)
- Email OTP verification
- Username/email availability checks
- Google OAuth refresh token generation (admin only)
- User authentication API endpoint
"""

import datetime
import json
import traceback
from random import randint
from typing import Dict, Any, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout as auth_logout,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_POST, require_http_methods

from accounts.models import UserProfile
from accounts.services.email_services import EmailService
from accounts.services.google_services import GoogleDriveService
from accounts.services.security_services import security_service
from ..utilitie_functions import mask_email, validate_password


# ============================================================================
# Authentication Views
# ============================================================================

def login(request: HttpRequest) -> HttpResponse:
    """
    Handle user login with username/password authentication.
    
    GET: Display login form
    POST: Authenticate user and redirect to dashboard
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Login page or redirect to dashboard
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "GET":
        msg = request.session.pop('forgot_password_msg', '')
        return render(request, "auth/login.html", {"msg": msg})

    username = request.POST.get('username', '').lower()
    password = request.POST.get('password', '')
    
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        auth_login(request, user)
        # Backward compatibility - can be removed in future
        request.session["username"] = user.username
        return redirect("dashboard")
    
    return render(request, "auth/login.html", {"msg": "Invalid Credentials"})


def signup(request: HttpRequest) -> HttpResponse:
    """
    Handle new user registration with email OTP verification.
    
    GET: Display signup form
    POST: Validate input, verify OTP, and create new user
    
    Requirements:
        - Unique username and email
        - Strong password (min 8 chars, uppercase, number, special char)
        - Valid OTP sent to email (expires in 10 minutes)
        
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Signup page or redirect to login on success
    """
    if request.method == "GET":
        return render(request, "auth/signup.html")

    # Extract form data
    username = request.POST.get('username', '').lower().strip()
    password = request.POST.get('password', '')
    rpassword = request.POST.get('rpassword', '')
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    otp = request.POST.get('otp', '').strip()

    context = {
        'username': username,
        'name': name,
        'email': email
    }

    # Validation checks
    if not all([username, password, rpassword, name, email, otp]):
        context['msg'] = "All fields are required."
        return render(request, "auth/signup.html", context=context)

    if User.objects.filter(username=username).exists():
        context['msg'] = "Username already exists."
        return render(request, "auth/signup.html", context=context)
    
    if User.objects.filter(email=email).exists():
        context['msg'] = "Email already exists."
        return render(request, "auth/signup.html", context=context)
    
    if not validate_password(password):
        context['msg'] = "Password must have at least 8 characters, an uppercase letter, a number, and a special character."
        return render(request, "auth/signup.html", context=context)

    if password != rpassword:
        context['msg'] = "Passwords do not match."
        return render(request, "auth/signup.html", context=context)
    
    # Verify OTP from session
    session_data = request.session.get("email")
    if not session_data or email != session_data.get("email_id"):
        context['msg'] = "Please verify your email first!"
        return render(request, "auth/signup.html", context=context)
    
    # Check OTP expiry (10 minutes)
    try:
        first_attempt_time = datetime.datetime.strptime(
            session_data['created_at'], 
            "%d/%m/%Y %H:%M:%S"
        )
        if (datetime.datetime.now() - first_attempt_time).total_seconds() > 600:
            context['msg'] = "OTP has expired. Please request a new one."
            return render(request, "auth/signup.html", context=context)
    except (ValueError, KeyError) as e:
        context['msg'] = "Invalid session data. Please try again."
        return render(request, "auth/signup.html", context=context)
    
    # Verify OTP value
    try:
        if session_data['OTP'] != int(otp):
            context['msg'] = "Invalid OTP. Please check your email."
            return render(request, "auth/signup.html", context=context)
    except (ValueError, KeyError):
        context['msg'] = "Invalid OTP format."
        return render(request, "auth/signup.html", context=context)
    
    # Clear session data after verification
    del request.session['email']

    # Create user
    try:
        # Split name into first and last names
        name_parts = name.rsplit(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # UserProfile is automatically created via post_save signal
        # (see accounts/signals.py)
        
        return render(request, "auth/login.html", {
            "msg": "Account created successfully! Please log in."
        })
        
    except Exception as e:
        traceback.print_exc()
        messages.error(request, "An error occurred during registration.")
        context['msg'] = "Registration failed. Please try again."
        return render(request, "auth/signup.html", context=context)


def logout(request: HttpRequest) -> HttpResponse:
    """
    Log out the current user and redirect to home page.
    
    Clears Django auth session and legacy username session.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Redirect to index page
    """
    auth_logout(request)
    
    # Clean up legacy session data
    request.session.pop('username', None)
    
    return redirect('index')


# ============================================================================
# Password Management
# ============================================================================

def forgotPassword(request: HttpRequest) -> HttpResponse:
    """
    Handle password reset via email.
    
    Generates a random password and emails it to the user.
    Accepts username or email as identifier.
    
    GET: Display forgot password form
    POST: Generate new password and send via email
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Forgot password page or redirect to login
    """
    if request.method == "GET":
        return render(request, "auth/forgotPassword.html")

    try:
        username = request.POST.get("username", "").lower().strip()
        user = User.objects.get(Q(username=username) | Q(email=username))

        # Generate random password
        new_password = get_random_string(12)
        
        # Send email
        subject = "Password Reset Request"
        message = (
            f"Your password has been reset.\n\n"
            f"New Password: {new_password}\n\n"
            f"Please change this password after logging in.\n"
            f"Do not share this password with anyone."
        )
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False
        )

        # Update password
        user.set_password(new_password)
        user.save()

        # Show success message
        masked_email = mask_email(user.email)
        request.session['forgot_password_msg'] = f"New password sent to {masked_email}"

        return redirect('login')
        
    except User.DoesNotExist:
        return render(request, "auth/forgotPassword.html", {
            "msg": "No account found with that username or email."
        })
    except Exception as e:
        traceback.print_exc()
        return render(request, "auth/forgotPassword.html", {
            "msg": "An error occurred. Please try again later."
        })


@login_required
@require_POST
def changePassword(request: HttpRequest) -> HttpResponse:
    """
    Change password for authenticated user.
    
    Validates old password, ensures new password meets requirements,
    and keeps user logged in after password change.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Redirect to profile page
    """
    try:
        user = request.user
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('password', '')
        confirm_password = request.POST.get('c_password', '')

        # Validate old password
        if not user.check_password(old_password):
            messages.error(request, "Old password is incorrect.")
            return redirect('profile')

        # Validate new password strength
        if not validate_password(new_password):
            messages.error(request, 
                "Password must have at least 8 characters, an uppercase letter, "
                "a number, and a special character."
            )
            return redirect('profile')

        # Validate password confirmation
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('profile')

        # Update password
        user.set_password(new_password)
        user.save()
        
        # Keep user logged in after password change
        auth_login(request, user)
        
        messages.success(request, "Password updated successfully!")
        return redirect('profile')
        
    except Exception as e:
        traceback.print_exc()
        messages.error(request, "An error occurred while changing password.")
        return redirect('profile')


# ============================================================================
# OTP Management
# ============================================================================

@require_POST
def send_otp(request: HttpRequest) -> JsonResponse:
    """
    Send OTP to user's email for signup verification.
    
    Features:
        - Generates 6-digit random OTP
        - Rate limiting: max 3 attempts per 30 minutes
        - OTP valid for 10 minutes
        - Checks if email already registered
        
    Args:
        request: HTTP request object with JSON body containing email
        
    Returns:
        JsonResponse: Status and message
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({
                "status": "error",
                "message": "Email is required"
            })

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                "status": "error",
                "message": "Email already in use"
            })
        
        # Generate OTP
        otp = randint(100000, 999999)
        
        # Rate limiting check
        session_data = request.session.get("email")
        current_time = datetime.datetime.now()
        attempt_count = 0
        
        if session_data and session_data.get('email_id') == email:
            attempt_count = session_data.get('attempt', 0)
            
            try:
                first_attempt_time = datetime.datetime.strptime(
                    session_data['created_at'], 
                    "%d/%m/%Y %H:%M:%S"
                )
                
                # Reset counter if 30 minutes have passed
                time_diff = (current_time - first_attempt_time).total_seconds()
                if time_diff > 1800:
                    attempt_count = 0
                elif attempt_count >= 3:
                    # Calculate remaining wait time
                    remain_minutes = round((1800 - time_diff) / 60)
                    return JsonResponse({
                        "status": "error",
                        "message": f"Too many attempts. Please try again in {remain_minutes} minutes."
                    })
            except (ValueError, KeyError):
                attempt_count = 0

        # Store OTP in session
        request.session["email"] = {
            "email_id": email,
            "OTP": otp,
            "created_at": current_time.strftime("%d/%m/%Y %H:%M:%S"),
            "attempt": attempt_count + 1
        }

        # Send OTP email
        email_service = EmailService()
        email_sent = email_service.send_email(
            subject="Email Verification - OTP Code",
            recipient_list=[email, settings.ADMIN_EMAIL],
            template_name="email_templates/otp_verification.html",
            context={"otp": otp},
            is_html=True,
        )

        if not email_sent:
            return JsonResponse({
                "status": "error",
                "message": "Failed to send email. Please check your email address."
            })
        
        return JsonResponse({"status": "Success"})
        
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid request format"
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            "status": "error",
            "message": "An error occurred. Please try again."
        })


# ============================================================================
# Validation Endpoints
# ============================================================================

@require_POST
def check_username(request: HttpRequest) -> JsonResponse:
    """
    Check if username is available for registration.
    
    Validates:
        - Username is at least 3 characters
        - Username is not already taken
        
    Args:
        request: HTTP request object with JSON body containing username
        
    Returns:
        JsonResponse: {available: bool, message: str}
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').lower().strip()
        
        if not username:
            return JsonResponse({
                "available": False,
                "message": "Username is required"
            })
        
        if len(username) < 3:
            return JsonResponse({
                "available": False,
                "message": "Username must be at least 3 characters"
            })
        
        exists = User.objects.filter(username=username).exists()
        
        return JsonResponse({
            "available": not exists,
            "message": "Username is available" if not exists else "Username already taken"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "available": False,
            "message": "Invalid request format"
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            "available": False,
            "message": "Error checking username"
        })


@require_POST
def check_email(request: HttpRequest) -> JsonResponse:
    """
    Check if email is available for registration.
    
    Args:
        request: HTTP request object with JSON body containing email
        
    Returns:
        JsonResponse: {available: bool, message: str}
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({
                "available": False,
                "message": "Email is required"
            })
        
        exists = User.objects.filter(email=email).exists()
        
        return JsonResponse({
            "available": not exists,
            "message": "Email is available" if not exists else "Email already registered"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "available": False,
            "message": "Invalid request format"
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            "available": False,
            "message": "Error checking email"
        })


# ============================================================================
# Google OAuth & API
# ============================================================================

@login_required
def generate_refresh_token(request: HttpRequest) -> HttpResponse:
    """
    Generate Google OAuth refresh token for Google Drive API access.
    
    Admin-only endpoint for managing Google Drive service integration.
    
    GET: Return authorization URL or clear existing token
    POST: Exchange authorization code for refresh token
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: JSON response with auth URL or redirect to profile
    """
    user = request.user
    
    # Restrict to superusers only
    if not user.is_superuser:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('profile')
    
    google_service = GoogleDriveService()
    
    if request.method == "GET":
        # Check if clearing existing token
        if request.session.get("token"):
            del request.session["token"]
            return redirect("profile")
        
        # Return Google OAuth authorization URL
        auth_url = google_service.get_authentication_code()
        return JsonResponse({"auth_url": auth_url})
    
    # POST: Exchange code for refresh token
    try:
        data = json.loads(request.body)
        code = data.get("code", "")
        
        if google_service.get_refresh_token(code, user):
            request.session["token_generation"] = datetime.datetime.now().strftime("%d %b %Y %H:%M")
            messages.success(request, "Refresh token generated successfully!")
        else:
            messages.error(request, "Failed to generate refresh token.")
            
        return redirect("profile")
        
    except Exception as e:
        traceback.print_exc()
        messages.error(request, "An error occurred while generating token.")
        return redirect("profile")


def get_auth(request: HttpRequest) -> HttpResponse:
    """
    Display Google OAuth authorization page.
    
    Args:
        request: HTTP request object
        
    Returns:
        HttpResponse: Rendered auth token page
    """
    return render(request, "auth/getAuthToken.html")


def authenticate_user(request: HttpRequest) -> JsonResponse:
    """
    API endpoint to validate user authentication.
    
    Supports both authenticated sessions and encrypted session key fallback.
    Used by external services (e.g., Streamlit apps) to verify user identity.
    
    Args:
        request: HTTP request object with optional encrypted session_key
        
    Returns:
        JsonResponse: User details or error message
    """
    try:
        # Check if user is already authenticated
        if request.user.is_authenticated:
            user = request.user
        else:
            # Fallback to encrypted session key
            encrypted = request.GET.get("session_key")
            if not encrypted:
                return JsonResponse({
                    "status": 400,
                    "validate": False,
                    "error": "Missing session_key"
                }, status=400)

            # Decrypt and validate
            data = security_service.decrypt_text(encrypted)
            user = User.objects.filter(
                username=data.get('username'),
                id=data.get("user_id")
            ).first()
            
            if not user:
                return JsonResponse({
                    "status": 404,
                    "validate": False,
                    "error": "User not found"
                }, status=404)
        
        # Return user details
        return JsonResponse({
            "status": 200,
            "validate": True,
            "username": user.username,
            "name": user.get_full_name(),
            "email": user.email
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            "status": 500,
            "validate": False,
            "error": "Invalid session"
        }, status=500)