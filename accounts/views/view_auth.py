"""
Authentication and user management views.

This module handles all authentication-related functionality including:
- User login and logout (Google OAuth via django-allauth)
- Password management (change, forgot password via email link)
- User authentication API endpoint
"""

import datetime
import json
import traceback
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
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_POST, require_http_methods

from accounts.models import UserProfile
from accounts.services.email_services import EmailService
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
        return render(request, "auth/forgotPassword.html", {
            "msg": "No account found with that username or email."
        })
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
# API Endpoints
# ============================================================================

def get_auth(request: HttpRequest) -> HttpResponse:
    """
    Display Google OAuth authorization page.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Rendered auth token page
    """
    return render(request, "auth/getAuthToken.html")


def generate_refresh_token(request: HttpRequest) -> HttpResponse:
    """
    Google Drive refresh token generation has been removed per PROJECT_PLAN.md Section 1.3.
    This stub remains to avoid breaking any existing bookmarks/links.
    """
    messages.info(request, "This feature has been removed.")
    return redirect('profile')


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