"""
URL configuration for finance features (Account, Category, Entry CRUD).
Namespace: finance
"""

from django.urls import path
from accounts.views.view_finance import (
    account_list,
    account_create,
    account_edit,
    category_list,
    category_create,
    category_edit,
    entry_list,
    entry_create,
    entry_edit,
    entry_delete,
)
from accounts.views.view_loan_investment import (
    loan_list,
    loan_create,
    loan_edit,
    loan_log_emi,
    investment_list,
    investment_create,
    investment_edit,
    investment_log_contribution,
)
from accounts.views.view_split_plan import (
    split_plan_list,
    split_plan_create,
)
from accounts.views.view_ledger import (
    ledger_contact_list,
    ledger_contact_create,
    ledger_contact_edit,
    ledger_detail,
    ledger_entry_add,
    ledger_settle_up,
)
from accounts.views.view_import import (
    import_upload,
    import_review,
    import_commit,
)

app_name = 'finance'

urlpatterns = [
    # Account CRUD
    path('accounts/', account_list, name='account_list'),
    path('accounts/new/', account_create, name='account_create'),
    path('accounts/<int:pk>/edit/', account_edit, name='account_edit'),

    # Category CRUD
    path('categories/', category_list, name='category_list'),
    path('categories/new/', category_create, name='category_create'),
    path('categories/<int:pk>/edit/', category_edit, name='category_edit'),

    # Entry CRUD (expense/income)
    path('entries/', entry_list, name='entry_list'),
    path('entries/new/', entry_create, name='entry_create'),
    path('entries/<int:pk>/edit/', entry_edit, name='entry_edit'),
    path('entries/<int:pk>/delete/', entry_delete, name='entry_delete'),

    # Loan CRUD & Action
    path('loans/', loan_list, name='loan_list'),
    path('loans/new/', loan_create, name='loan_create'),
    path('loans/<int:pk>/edit/', loan_edit, name='loan_edit'),
    path('loans/<int:pk>/log-emi/', loan_log_emi, name='loan_log_emi'),

    # Investment CRUD & Action
    path('investments/', investment_list, name='investment_list'),
    path('investments/new/', investment_create, name='investment_create'),
    path('investments/<int:pk>/edit/', investment_edit, name='investment_edit'),
    path('investments/<int:pk>/log-contribution/', investment_log_contribution, name='investment_log_contribution'),

    # Split Plans
    path('splits/', split_plan_list, name='split_plan_list'),
    path('splits/new/', split_plan_create, name='split_plan_create'),

    # Ledger
    path('ledger/', ledger_contact_list, name='ledger_contact_list'),
    path('ledger/contact/new/', ledger_contact_create, name='ledger_contact_create'),
    path('ledger/contact/<int:pk>/edit/', ledger_contact_edit, name='ledger_contact_edit'),
    path('ledger/<int:pk>/', ledger_detail, name='ledger_detail'),
    path('ledger/<int:pk>/add/', ledger_entry_add, name='ledger_entry_add'),
    path('ledger/<int:pk>/settle/', ledger_settle_up, name='ledger_settle_up'),

    # Import
    path('import/', import_upload, name='import_upload'),
    path('import/review/', import_review, name='import_review'),
    path('import/commit/', import_commit, name='import_commit'),
]
