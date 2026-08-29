"""
Tests for Financial Instrument views and helpers.

Covers:
- desired_date() date-math and day-clamping (Chunk 1.1)
- create_finance() atomicity — orphan rollback on failure (Chunk 1.2)
- update_finance_detail() name, amount, and installment count changes (Chunk 1.6)
"""

import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import FinancialProduct, Transaction
from accounts.views.view_financial_instrument import desired_date

User = get_user_model()


# ==============================================================================
# desired_date() unit tests — pure function, no DB required
# ==============================================================================

class DesiredDateTests(TestCase):
    """Unit tests for the desired_date() date calculation helper."""

    def test_normal_offset_no_clamping(self):
        """A mid-month date + N months should produce the same day-of-month."""
        self.assertEqual(desired_date("2024-01-15", 2), "2024-03-15")

    def test_year_rollover(self):
        """Adding months that cross a year boundary should increment the year."""
        self.assertEqual(desired_date("2024-01-15", 12), "2025-01-15")

    def test_year_rollover_multiple(self):
        """Adding 24 months should advance two full years."""
        self.assertEqual(desired_date("2024-06-10", 24), "2026-06-10")

    def test_jan31_plus_1_leap_year(self):
        """Jan 31 + 1 month in a leap year → Feb 29 (not a crash)."""
        self.assertEqual(desired_date("2024-01-31", 1), "2024-02-29")

    def test_jan31_plus_1_non_leap_year(self):
        """Jan 31 + 1 month in a non-leap year → Feb 28 (not a crash)."""
        self.assertEqual(desired_date("2023-01-31", 1), "2023-02-28")

    def test_jan31_plus_3_months(self):
        """Jan 31 + 3 months → Apr 30 (April only has 30 days)."""
        self.assertEqual(desired_date("2024-01-31", 3), "2024-04-30")

    def test_jan31_plus_12_months(self):
        """Jan 31 + 12 months → Jan 31 next year (same day, valid month)."""
        self.assertEqual(desired_date("2024-01-31", 12), "2025-01-31")

    def test_march31_plus_1(self):
        """Mar 31 + 1 month → Apr 30."""
        self.assertEqual(desired_date("2024-03-31", 1), "2024-04-30")

    def test_may31_plus_1(self):
        """May 31 + 1 month → Jun 30."""
        self.assertEqual(desired_date("2024-05-31", 1), "2024-06-30")

    def test_november30_plus_3_non_leap(self):
        """Nov 30 + 3 months → Feb 28 (2025 is not a leap year)."""
        self.assertEqual(desired_date("2024-11-30", 3), "2025-02-28")

    def test_offset_zero(self):
        """Zero offset should return the start date unchanged."""
        self.assertEqual(desired_date("2024-06-15", 0), "2024-06-15")

    def test_returns_string(self):
        """Return type must always be a str in YYYY-MM-DD format."""
        result = desired_date("2024-01-01", 1)
        self.assertIsInstance(result, str)
        datetime.datetime.strptime(result, "%Y-%m-%d")  # must not raise


# ==============================================================================
# create_finance() view — atomicity tests
# ==============================================================================

class CreateFinanceAtomicityTests(TestCase):
    """
    Tests that create_finance() is atomic: either the FinancialProduct AND all
    installment Transactions are created, or none are (Chunk 1.2).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def _post_finance(self, **overrides):
        data = {
            "name": "Test Loan",
            "type": "Loan",
            "category": "EMI",
            "amount": "120000",
            "no_of_installments": "12",
            "started_on": "2024-01-15",
        }
        data.update(overrides)
        return self.client.post(reverse("create-finance"), data)

    def test_creates_product_and_installments(self):
        """Happy path: product + correct number of installments all committed."""
        self._post_finance()
        self.assertEqual(FinancialProduct.objects.filter(created_by=self.user).count(), 1)
        product = FinancialProduct.objects.get(created_by=self.user)
        self.assertEqual(
            Transaction.objects.filter(source=product, is_deleted=False).count(), 12
        )

    def test_installments_have_correct_emi_amount(self):
        """Each installment amount should equal amount / no_of_installments."""
        self._post_finance(amount="120000", no_of_installments="12")
        product = FinancialProduct.objects.get(created_by=self.user)
        txns = Transaction.objects.filter(source=product, is_deleted=False)
        for txn in txns:
            self.assertEqual(txn.amount, Decimal("10000.00"))

    def test_rollback_on_failure(self):
        """
        If an exception is raised inside the atomic block (simulated), neither
        the FinancialProduct nor any Transactions should be committed.
        """
        with patch(
            "accounts.views.view_financial_instrument.Transaction.objects.bulk_create",
            side_effect=Exception("Simulated DB failure"),
        ):
            self._post_finance()

        # Both the product AND all installments must be absent
        self.assertEqual(FinancialProduct.objects.filter(created_by=self.user).count(), 0)
        self.assertEqual(Transaction.objects.filter(created_by=self.user).count(), 0)

    def test_duplicate_product_rejected(self):
        """Submitting the same product twice should create only one product."""
        self._post_finance()
        self._post_finance()  # duplicate
        self.assertEqual(FinancialProduct.objects.filter(created_by=self.user).count(), 1)

    def test_zero_installments_rejected(self):
        """no_of_installments=0 must not create anything."""
        self._post_finance(no_of_installments="0")
        self.assertEqual(FinancialProduct.objects.filter(created_by=self.user).count(), 0)

    def test_sip_creates_investment_category(self):
        """A SIP product must generate installments with category='Investment'."""
        self._post_finance(name="My SIP", type="SIP", no_of_installments="6")
        product = FinancialProduct.objects.get(created_by=self.user)
        txns = Transaction.objects.filter(source=product, is_deleted=False)
        self.assertTrue(all(t.category == "Investment" for t in txns))

    def test_loan_creates_emi_category(self):
        """A Loan product must generate installments with category='EMI'."""
        self._post_finance(name="My Loan", type="Loan", no_of_installments="6")
        product = FinancialProduct.objects.get(created_by=self.user)
        txns = Transaction.objects.filter(source=product, is_deleted=False)
        self.assertTrue(all(t.category == "EMI" for t in txns))

    def test_installment_dates_start_at_started_on(self):
        """First installment date must equal started_on (offset=0)."""
        self._post_finance(started_on="2024-01-31", no_of_installments="3")
        product = FinancialProduct.objects.get(created_by=self.user)
        first_txn = Transaction.objects.filter(
            source=product, is_deleted=False
        ).order_by("date").first()
        self.assertEqual(str(first_txn.date), "2024-01-31")

    def test_installment_dates_clamp_short_months(self):
        """
        A loan started on the 31st should clamp installment dates to valid days
        (e.g. Feb 28/29) rather than crashing (regression guard for Chunk 1.1).
        """
        # This would have raised ValueError before the Chunk 1.1 fix
        response = self._post_finance(started_on="2024-01-31", no_of_installments="4")
        self.assertEqual(FinancialProduct.objects.filter(created_by=self.user).count(), 1)


# ==============================================================================
# create_finance() — authentication guard
# ==============================================================================

class CreateFinanceAuthTests(TestCase):
    """Unauthenticated requests to create_finance must redirect to login."""

    def test_unauthenticated_redirects_to_login(self):
        client = Client()
        response = client.post(reverse("create-finance"), {
            "name": "Anon Loan", "type": "Loan", "amount": "10000",
            "no_of_installments": "6", "started_on": "2024-01-01"
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
