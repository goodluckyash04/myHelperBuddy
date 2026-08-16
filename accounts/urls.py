"""
URL Configuration for Accounts App

This module defines URL patterns for all account-related views including:
- Authentication and user management (Google OAuth only)
- Finance (new, full standalone pages via finance/ sub-app)
- Profile and dashboard
"""

from django.urls import path, include

# ============================================================================
# View Imports - Authentication
# ============================================================================

from .views.view_auth import (
    authenticate_user,
    changePassword,
    confirm_password_reset,
    forgotPassword,
    generate_refresh_token,
    get_auth,
    login,
    logout,
)

# ============================================================================
# View Imports - General Views
# ============================================================================

from .views.views import (
    about,
    index,
    manual_backup,
    profile,
    redirect_to_streamlit,
    update_profile,
    utilities,
)

# ============================================================================
# URL Patterns
# ============================================================================

from accounts.views.view_dashboard import dashboard

urlpatterns = [
    # Finance CRUD (Phase 3+) — Account, Category, Entry, Loans, Investments, Ledger
    path('finance/', include('accounts.finance_urls', namespace='finance')),

    # ========================================================================
    # Home & Core Pages
    # ========================================================================
    path("", index, name="index"),
    path("utilities/", utilities, name="utilities"),
    path("profile/", profile, name="profile"),
    path("update-profile/", update_profile, name="update-profile"),
    path("manual-backup/", manual_backup, name="manual-backup"),
    path("dashboard/", dashboard, name="dashboard"),
    path("about/", about, name="about"),

    # ========================================================================
    # Authentication & User Management
    # ========================================================================
    path("login", login, name="login"),
    path("logout/", logout, name="logout"),
    path("forgotPassword/", forgotPassword, name="forgotPassword"),
    path("changePassword/", changePassword, name="changePassword"),
    path("generate-refresh-token/", generate_refresh_token, name="generate-refresh-token"),
    path("get-auth/", get_auth, name="get-auth"),
    path("user-authentication/", authenticate_user, name="user-authentication"),

    # ========================================================================
    # Advanced Utilities
    # ========================================================================
    path("advance-utils/", redirect_to_streamlit, name="advance-utils"),

    # ========================================================================
    # Password Reset
    # ========================================================================
    path("reset/<uidb64>/<token>/", confirm_password_reset, name="confirm-password-reset"),
]
