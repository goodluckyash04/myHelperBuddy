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
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_POST, require_http_methods

from accounts.models import UserProfile
from accounts.services.email_services import EmailService
from accounts.services.google_services import GoogleDriveService, get_drive_service
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

def forgotPassword(request: HttpRequest) -> HttpResponse:  # now sends reset link, not raw password
    """
    Initiate a secure password reset via a time-limited email link.

    GET:  Display the forgot-password form.
    POST: Generate a signed reset token, send a link to the user's email.
          The raw password is NEVER sent — only a URL-safe signed token.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Forgot-password page or redirect to login with success flash
    """
    if request.method == "GET":
        return render(request, "auth/forgotPassword.html")

    try:
        username = request.POST.get("username", "").lower().strip()
        user = User.objects.get(Q(username=username) | Q(email=username))

        # generate a signed, time-limited token (no raw password ever sent)
        token = default_token_generator.make_token(user)
        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"{settings.SITE_URL}/reset/{uid}/{token}/"

        subject = "Password Reset — myHelperBuddy"
        message = (
            f"Hi {user.first_name or user.username},\n\n"
            f"We received a request to reset your password.\n"
            f"Click the link below to set a new password (valid for 1 hour):\n\n"
            f"{reset_url}\n\n"
            f"If you did not request this, please ignore this email.\n"
            f"Your password will NOT change unless you click the link above."
        )
        if settings.EMAIL_SERVICE:
            email_service = EmailService()
            email_service.send_email(
                subject=subject,
                recipient_list=[user.email],
                message=message,
                is_html=False,
            )
            masked_email = mask_email(user.email)
            request.session['forgot_password_msg'] = f"Reset link sent to {masked_email}"
        else:
            request.session['forgot_password_msg'] = "Unable to send email. Please try again later."

        return redirect('login')

    except User.DoesNotExist:
        # Always redirect with the same message regardless of whether the account exists.
        # Returning a different message for missing accounts allows user enumeration
        # — an attacker could probe usernames to find valid accounts.
        request.session['forgot_password_msg'] = (
            "If an account exists with that username or email, a reset link has been sent."
        )
        return redirect('login')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return render(request, "auth/forgotPassword.html", {
            "msg": "An error occurred. Please try again later."
        })


def confirm_password_reset(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    """
    Confirm a password-reset request and allow the user to set a new password.

    GET:  Validate the token — show the new-password form if valid.
    POST: Set the new password if token is still valid and passwords match.

    Args:
        request: HTTP request object
        uidb64:  URL-safe base64-encoded user PK from the reset link
        token:   Signed reset token from the reset link

    Returns:
        HttpResponse: Reset form, success redirect, or error page
    """
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "auth/password_reset_invalid.html", {
            "msg": "This password reset link is invalid or has expired (links expire after 1 hour)."
        })

    if request.method == "GET":
        return render(request, "auth/password_reset_confirm.html", {
            "uidb64": uidb64, "token": token
        })

    # POST — set new password
    new_password     = request.POST.get("new_password", "").strip()
    confirm_password = request.POST.get("confirm_password", "").strip()

    if not new_password or new_password != confirm_password:
        return render(request, "auth/password_reset_confirm.html", {
            "uidb64": uidb64, "token": token,
            "msg": "Passwords do not match or are empty."
        })

    from ..utilitie_functions import validate_password
    if not validate_password(new_password):
        return render(request, "auth/password_reset_confirm.html", {
            "uidb64": uidb64, "token": token,
            "msg": "Password must be ≥8 chars with uppercase, lowercase, digit, and special character."
        })

    user.set_password(new_password)
    user.save()

    request.session['forgot_password_msg'] = "Password updated successfully. Please log in."
    return redirect('login')


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
        # Send OTP only to the user's own email.
        # DO NOT include ADMIN_EMAIL — sending live OTPs to the admin is a security risk:
        # it exposes user authentication codes and breaks OTP secrecy.
        email_sent = email_service.send_email(
            subject="Email Verification - OTP Code",
            recipient_list=[email],
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

    GET: Return authorization URL or clear existing token.
         NOTE: This does NOT initialise a Drive service — it only builds the
         redirect URL, so no token refresh happens on a plain GET.
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

    if request.method == "GET":
        # Check if clearing existing token
        if request.session.get("token"):
            del request.session["token"]
            return redirect("profile")

        # Build the OAuth URL without initialising the full Drive service.
        # `get_authentication_code()` only reads settings — no token fetch needed.
        auth_url = GoogleDriveService.get_authentication_code_url()
        return JsonResponse({"auth_url": auth_url})

    # POST: Exchange authorization code for a refresh token.
    # We intentionally bypass `__init__` (and its token fetch) because the
    # refresh token doesn’t exist yet; only `get_refresh_token()` is needed.
    try:
        data = json.loads(request.body)
        code = data.get("code", "")

        if GoogleDriveService.exchange_code_for_refresh_token(code, user):
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