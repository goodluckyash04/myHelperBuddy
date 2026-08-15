"""
URL Configuration for Accounts App

This module defines URL patterns for all account-related views including:
- Authentication and user management (Google OAuth only)
- Transactions (income/expense tracking)
- Financial instruments (loans, SIPs, splits) — legacy, to be replaced in Phase 2+
- Ledger transactions (receivables/payables) — legacy, to be replaced in Phase 3+
- Profile and dashboard
"""

from django.urls import path, include

# ============================================================================
# View Imports - Authentication
# ============================================================================


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
# View Imports - Financial Instruments
# ============================================================================

from .views.view_financial_instrument import (
    create_finance,
    fetch_financial_transaction,
    finance_details,
    remove_instrument,
    update_finance_detail,
    update_instrument_status,
)

# ============================================================================
# View Imports - Ledger Transactions
# ============================================================================

from .views.view_ledger_transaction import (
    add_ledger_transaction,
    delete_ledger_transaction,
    fetch_deleted_ledger_transaction,
    get_ledger_transactions_by_party,
    ledger_transaction_details,
    undo_ledger_transaction,
    update_counterparty_name,
    update_ledger_transaction,
    update_ledger_transaction_status,
    # Enhanced endpoints
    record_payment,
    get_transaction_payments,
    get_counterparty_summary,
    get_aging_report,
    get_cash_flow_projection,
)

# ============================================================================
# View Imports - Transactions
# ============================================================================

from .views.view_transaction import (
    create_transaction,
    delete_transaction,
    fetch_deleted_transaction,
    transaction_detail,
    undo_transaction,
    update_transaction,
    update_transaction_status,
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
    # Finance CRUD (Phase 3+) — Account, Category, Entry
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
    # Transaction Management (Income/Expense) — legacy, Phase 2 will replace
    # ========================================================================
    path("create-transaction/", create_transaction, name="create-transaction"),
    path("transaction-detail/", transaction_detail, name="transaction-detail"),
    path("deleted-transaction-detail/", fetch_deleted_transaction, name="deleted-transaction-detail"),
    path("update-transaction/<int:id>", update_transaction, name="update-transaction"),
    path("update-transaction-status/<int:id>", update_transaction_status, name="update-transaction-status"),
    path("delete-transaction/", delete_transaction, name="delete-transaction"),
    path("delete-transaction/<int:id>", delete_transaction, name="delete-transaction"),
    path("undo-transaction/", undo_transaction, name="undo-transaction"),
    path("undo-transaction/<int:id>", undo_transaction, name="undo-transaction"),

    # ========================================================================
    # Financial Instruments (Loans, SIPs, Splits) — legacy, Phase 4/5 will replace
    # ========================================================================
    path("create-finance/", create_finance, name="create-finance"),
    path("finance-details/", finance_details, name="finance-details"),
    path("update-finance-detail/<int:id>", update_finance_detail, name="update-finance-detail"),
    path("fetch-financial-transaction/<int:id>", fetch_financial_transaction, name="fetch-financial-transaction"),
    path("update-instrument-status/<int:id>", update_instrument_status, name="update-instrument-status"),
    path("remove-instrument/<int:id>", remove_instrument, name="remove-instrument"),

    # ========================================================================
    # Ledger Transactions (Receivables/Payables) — legacy, Phase 6 will replace
    # ========================================================================
    path("create-ledger-transaction/", add_ledger_transaction, name="create-ledger-transaction"),
    path("ledger-transaction-details/", ledger_transaction_details, name="ledger-transaction-details"),
    path("ledger-transaction/<str:id>", get_ledger_transactions_by_party, name="ledger-transaction"),
    path("update-ledger-transaction-status/<int:id>", update_ledger_transaction_status, name="update-ledger-transaction-status"),
    path("update-ledger-transaction-status/", update_ledger_transaction_status, name="update-ledger-transaction-status"),
    path("delete-ledger-transaction/<int:id>", delete_ledger_transaction, name="delete-ledger-transaction"),
    path("update-ledger-transaction/<int:id>", update_ledger_transaction, name="update-ledger-transaction"),
    path("update-counterparty-name/<str:id>", update_counterparty_name, name="update-counterparty-name"),
    path("deleted-ledger-transaction/", fetch_deleted_ledger_transaction, name="deleted-ledger-transaction"),
    path("undo-ledger-transaction/", undo_ledger_transaction, name="undo-ledger-transaction"),
    path("undo-ledger-transaction/<int:id>", undo_ledger_transaction, name="undo-ledger-transaction"),

    # Enhanced Ledger Endpoints
    path("record-payment/<int:id>", record_payment, name="record-payment"),
    path("transaction-payments/<int:id>", get_transaction_payments, name="transaction-payments"),
    path("counterparty-summary/", get_counterparty_summary, name="counterparty-summary"),
    path("aging-report/", get_aging_report, name="aging-report"),
    path("cash-flow-projection/", get_cash_flow_projection, name="cash-flow-projection"),

    # ========================================================================
    # Advanced Utilities
    # ========================================================================
    path("advance-utils/", redirect_to_streamlit, name="advance-utils"),

    # ========================================================================
    # Password Reset
    # ========================================================================
    path("reset/<uidb64>/<token>/", confirm_password_reset, name="confirm-password-reset"),
]
