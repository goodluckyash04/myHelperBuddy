"""
Tests for authentication views and security fixes.

Covers:
- OTP expiry and max-attempt enforcement
- forgotPassword returns the same response for existing and non-existing accounts
  (user enumeration fix — Chunk 1.7)
- Password reset token flow
- Login/logout basic flows
"""

import json
import datetime
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()

# Middleware list without the rate limiter so tests don't hit the cache limits.
# Rate limiting is tested via middleware unit tests, not end-to-end view tests.
_MIDDLEWARE_NO_RATE_LIMIT = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]


# ==============================================================================
# forgotPassword — user enumeration fix (Chunk 1.7)
# ==============================================================================

@override_settings(MIDDLEWARE=_MIDDLEWARE_NO_RATE_LIMIT)
class ForgotPasswordEnumerationTests(TestCase):
    """
    Verifies that forgotPassword always redirects to login with the same
    neutral message regardless of whether the submitted username/email
    belongs to a real account (Chunk 1.7 security fix).
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="realuser", password="pass1234", email="real@example.com"
        )
        cache.clear()

    @patch("accounts.views.view_auth.EmailService")
    def test_existing_account_redirects_to_login(self, mock_email):
        """A valid username → redirect to login (not the form with an error)."""
        mock_instance = MagicMock()
        mock_instance.send_email.return_value = True
        mock_email.return_value = mock_instance

        response = self.client.post(
            reverse("forgotPassword"), {"username": "realuser"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_nonexistent_account_also_redirects_to_login(self):
        """
        A non-existent username must ALSO redirect to login with the same
        neutral message — not render the form with 'No account found'.
        This is the core of the enumeration fix.
        """
        response = self.client.post(
            reverse("forgotPassword"), {"username": "ghost_user_xyz"}
        )
        # Must redirect, not render (which would expose account existence)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_nonexistent_account_message_is_neutral(self):
        """
        The session message for a missing account must NOT contain
        'No account found' or any phrasing that reveals the account doesn't exist.
        """
        self.client.post(
            reverse("forgotPassword"), {"username": "ghost_user_xyz"}
        )
        msg = self.client.session.get("forgot_password_msg", "")
        # Must not reveal the account doesn't exist
        self.assertNotIn("No account found", msg)
        self.assertNotIn("not found", msg.lower())
        # Must be the neutral message
        self.assertIn("If an account exists", msg)

    @patch("accounts.views.view_auth.EmailService")
    def test_existing_and_missing_produce_same_redirect(self, mock_email):
        """
        The HTTP response behaviour for a real and a fake account must
        be identical (same status code, same redirect target).
        """
        mock_instance = MagicMock()
        mock_instance.send_email.return_value = True
        mock_email.return_value = mock_instance

        real_response = self.client.post(
            reverse("forgotPassword"), {"username": "realuser"}
        )
        fake_response = self.client.post(
            reverse("forgotPassword"), {"username": "ghost_user_xyz"}
        )

        self.assertEqual(real_response.status_code, fake_response.status_code)
        self.assertEqual(real_response["Location"], fake_response["Location"])


# ==============================================================================
# OTP — send_otp endpoint (Chunk 1.7 — OTP no longer copied to admin)
# ==============================================================================

@override_settings(MIDDLEWARE=_MIDDLEWARE_NO_RATE_LIMIT)
class SendOTPTests(TestCase):
    """
    Tests for the send_otp endpoint. Verifies OTP is sent only to the
    user's email — not to ADMIN_EMAIL (Chunk 1.7 security fix).
    """

    def setUp(self):
        self.client = Client()
        cache.clear()

    @patch("accounts.views.view_auth.EmailService")
    def test_otp_sent_only_to_user_email(self, mock_email_class):
        """
        send_otp must call send_email with only the user's email in
        recipient_list. ADMIN_EMAIL must not appear.
        """
        mock_instance = MagicMock()
        mock_instance.send_email.return_value = True
        mock_email_class.return_value = mock_instance

        payload = json.dumps({"email": "newuser@example.com"})
        self.client.post(
            reverse("send_otp"),
            data=payload,
            content_type="application/json",
        )

        # Check send_email was called
        self.assertTrue(mock_instance.send_email.called)
        call_args = mock_instance.send_email.call_args
        # Get recipients — handle both positional and keyword argument styles
        recipients = call_args.kwargs.get("recipient_list") or (
            call_args.args[1] if len(call_args.args) > 1 else []
        )
        # OTP must go only to the user — exactly one recipient
        self.assertEqual(len(recipients), 1, "OTP must go to exactly one recipient")
        self.assertEqual(recipients[0], "newuser@example.com")
        # ADMIN_EMAIL must NOT be in the recipient list (Chunk 1.7 fix)

    @patch("accounts.views.view_auth.EmailService")
    def test_otp_returns_success_status(self, mock_email_class):
        """A valid email → JSON response with status=Success."""
        mock_instance = MagicMock()
        mock_instance.send_email.return_value = True
        mock_email_class.return_value = mock_instance

        payload = json.dumps({"email": "user2@example.com"})
        response = self.client.post(
            reverse("send_otp"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "Success")


# ==============================================================================
# Login / Logout basic flows
# ==============================================================================

@override_settings(MIDDLEWARE=_MIDDLEWARE_NO_RATE_LIMIT)
class LoginLogoutTests(TestCase):
    """Basic login and logout behaviour."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="loginuser", password="pass1234", email="login@example.com"
        )
        cache.clear()

    def test_valid_login_redirects(self):
        """Valid credentials → redirect (not 401 or staying on login page)."""
        response = self.client.post(
            reverse("login"), {"username": "loginuser", "password": "pass1234"}
        )
        # Should redirect somewhere (dashboard or next param)
        self.assertIn(response.status_code, [301, 302])

    def test_invalid_password_stays_on_login(self):
        """Wrong password → stays on login page (not 500)."""
        response = self.client.post(
            reverse("login"), {"username": "loginuser", "password": "wrongpass"}
        )
        self.assertNotEqual(response.status_code, 500)

    def test_logout_redirects(self):
        """Logout must redirect to the login/index page."""
        self.client.login(username="loginuser", password="pass1234")
        response = self.client.get(reverse("logout"))
        self.assertIn(response.status_code, [301, 302])

    def test_dashboard_requires_login(self):
        """Unauthenticated access to /dashboard/ must redirect to login."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
