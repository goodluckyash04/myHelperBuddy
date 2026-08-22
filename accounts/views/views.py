"""
Core views for the MyHelperBuddy accounts application.

This module contains main views for dashboard, profile, utilities,
and various analytics/statistics calculations.
"""

import json
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, DecimalField
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.decorators import auth_user
from accounts.models import (
    UtilityModule,
    LedgerTransaction,
    RefreshToken,
    Transaction,
)
from accounts.services.security_services import security_service
from accounts.services.module_registry import module_registry
from accounts.utilitie_functions import convert_decimal, format_amount



# ============================================================================
# Helper Functions
# ============================================================================


def get_counter_parties(user):
    """
    Retrieve distinct counterparty names for a given user.

    Args:
        user: The Django user object.

    Returns:
        QuerySet: Distinct counterparty names.
    """
    return (
        LedgerTransaction.objects.filter(created_by=user)
        .order_by("counterparty")
        .values_list("counterparty", flat=True)
        .distinct()
    )

import json
def get_counterparty_tabs_json(user):
    """Returns a JSON string mapping counterparties to their available tabs."""
    qs = LedgerTransaction.objects.filter(created_by=user, is_deleted=False).values_list('counterparty', 'tab_name').distinct()
    data = {}
    for cp, tab in qs:
        tab = tab or 'General'
        if cp not in data:
            data[cp] = []
        if tab not in data[cp]:
            data[cp].append(tab)
    return json.dumps(data)


def calculate_financial_overview(transactions) -> Dict[str, str]:
    """
    Calculate financial overview metrics using database aggregations.

    Optimized to use database aggregations instead of Python loops.

    Args:
        transactions: QuerySet of Transaction objects.

    Returns:
        Dict containing formatted financial metrics:
            - Income, Expense, Saving, EMI Due, Investment, Split Due
    """
    aggregations = transactions.aggregate(
        income=Sum(
            "amount",
            filter=Q(type__iexact="income", is_deleted=False),
            output_field=DecimalField(),
        ),
        expense=Sum(
            "amount",
            filter=Q(type__iexact="expense", status__iexact="completed")
            & ~Q(category__iexact="investment"),
            output_field=DecimalField(),
        ),
        investment=Sum(
            "amount",
            filter=Q(category__iexact="investment", status__iexact="completed"),
            output_field=DecimalField(),
        ),
        overdue=Sum(
            "amount",
            filter=Q(category__iexact="emi", status__iexact="pending"),
            output_field=DecimalField(),
        ),
        split_due=Sum(
            "amount",
            filter=Q(source__type__iexact="split", status__iexact="pending", is_deleted=False),
            output_field=DecimalField(),
        ),
        split_paid=Sum(
            "amount",
            filter=Q(source__type__iexact="split", status__iexact="completed", is_deleted=False),
            output_field=DecimalField(),
        ),
    )

    income = aggregations["income"] or 0
    expense = aggregations["expense"] or 0
    investment = aggregations["investment"] or 0
    overdue = aggregations["overdue"] or 0
    split_due = aggregations["split_due"] or 0
    split_paid = aggregations["split_paid"] or 0

    return {
        "Income": format_amount(income),
        "Expense": format_amount(expense),
        "Investment": format_amount(investment),
        "EMI Due": format_amount(overdue),
        "Split Due": format_amount(split_due),
        "Saving": format_amount(income - expense - investment - split_due),
    }

def calculate_category_wise_expenses(transactions) -> Dict[str, Any]:
    """
    Calculate expenses grouped by category.

    Optimized using database aggregations grouped by category.

    Args:
        transactions: QuerySet of Transaction objects.

    Returns:
        Dict mapping category names to total amounts.
    """
    category_data = (
        transactions.filter(type__iexact="Expense", date__lte=datetime.now().date())
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    result = {}
    for item in category_data:
        cat = item["category"]
        if cat and cat.lower() == "emi":
            cat = "Shopping"
            
        result[cat] = result.get(cat, 0) + float(item["total"] or 0)
        
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def calculate_monthly_savings(transactions, user) -> Dict[str, float]:
    """
    Calculate monthly savings for the last 12 months.

    Args:
        transactions: QuerySet of Transaction objects.
        user: The Django user object.

    Returns:
        Dict mapping month labels (e.g., "Jan'24") to savings amounts.
    """
    current_date = timezone.now()

    last_12_months = [
        (current_date - relativedelta(months=i)).month for i in range(12)
    ]
    last_12_months_years = [
        (current_date - relativedelta(months=i)).year for i in range(12)
    ]

    monthly_data = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            date__year__in=last_12_months_years,
            date__month__in=last_12_months,
        )
        .values("date__year", "date__month")
        .annotate(
            total_expense=Sum("amount", filter=Q(type="Expense")),
            total_income=Sum("amount", filter=Q(type="Income")),
        )
    )

    savings_data = {}
    for i in range(12):
        month = last_12_months[i]
        year = last_12_months_years[i]

        month_data = next(
            (
                transaction
                for transaction in monthly_data
                if transaction["date__month"] == month
                and transaction["date__year"] == year
            ),
            {},
        )
        total_expense = month_data.get("total_expense") or 0
        total_income = month_data.get("total_income") or 0

        savings = total_income - total_expense
        label = datetime(year, month, 1).strftime("%b'%y")
        savings_data[label] = float(savings)

    return savings_data


def calculate_year_wise_data(transactions, user) -> Dict[str, list]:
    """
    Calculate yearly income and expense data.

    Args:
        transactions: QuerySet of Transaction objects.
        user: The Django user object.

    Returns:
        Dict containing lists of income, expense, and year labels.
    """
    current_date = timezone.now()

    if current_date.month == 12:
        first_day_of_next_month = datetime(current_date.year + 1, 1, 1)
    else:
        first_day_of_next_month = datetime(
            current_date.year, current_date.month + 1, 1
        )

    yearly_data = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            date__lte=first_day_of_next_month,
        )
        .values("date__year")
        .annotate(
            total_expense=Sum("amount", filter=Q(type="Expense")),
            total_income=Sum("amount", filter=Q(type="Income")),
        )
    )

    return {
        "income": [item["total_income"] for item in yearly_data],
        "expense": [item["total_expense"] for item in yearly_data],
        "label": [item["date__year"] for item in yearly_data],
    }


def calculate_current_month_category_expenses(transactions, user) -> Dict[str, list]:
    """
    Calculate current month's category-wise expenses with balance.

    Args:
        transactions: QuerySet of Transaction objects.
        user: The Django user object.

    Returns:
        Dict containing labels and amounts for current month categories.
    """
    current_date = timezone.now()
    current_year = current_date.year
    current_month = current_date.month

    category_expenses = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            date__month=current_month,
            date__year=current_year,
            type="Expense",
        )
        .values("category")
        .annotate(amount=Sum("amount"))
    )

    total = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            date__month=current_month,
            date__year=current_year,
        )
        .values("type")
        .annotate(amount=Sum("amount"))
    )

    category_wise = {
        "labels": [item["category"] for item in category_expenses],
        "amount": [item["amount"] for item in category_expenses],
    }

    income_total = next(
        (item["amount"] for item in total if item["type"] == "Income"), 0
    )
    expense_total = next(
        (item["amount"] for item in total if item["type"] == "Expense"), 0
    )

    category_wise["labels"].append("Balance")
    category_wise["amount"].append(income_total - expense_total)

    return category_wise


def calculate_monthly_income_expense(transactions, user) -> Dict[str, list]:
    """
    Calculate monthly income and expense for the last 12 months.
    
    This provides data for the Cash Flow Trend chart showing income,
    expense, and net savings over time.

    Args:
        transactions: QuerySet of Transaction objects.
        user: The Django user object.

    Returns:
        Dict containing lists of labels, income, expense, and savings.
    """
    current_date = timezone.now()
    
    last_12_months = [
        (current_date - relativedelta(months=i)).month for i in range(12)
    ]
    last_12_months_years = [
        (current_date - relativedelta(months=i)).year for i in range(12)
    ]

    monthly_data = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            date__year__in=last_12_months_years,
            date__month__in=last_12_months,
        )
        .values("date__year", "date__month")
        .annotate(
            total_expense=Sum("amount", filter=Q(type="Expense")),
            total_income=Sum("amount", filter=Q(type="Income")),
        )
    )

    labels = []
    income_data = []
    expense_data = []
    savings_data = []

    for i in range(12):
        month = last_12_months[i]
        year = last_12_months_years[i]

        month_data = next(
            (
                transaction
                for transaction in monthly_data
                if transaction["date__month"] == month
                and transaction["date__year"] == year
            ),
            {},
        )
        
        total_expense = float(month_data.get("total_expense") or 0)
        total_income = float(month_data.get("total_income") or 0)
        savings = total_income - total_expense
        
        label = datetime(year, month, 1).strftime("%b'%y")
        
        labels.append(label)
        income_data.append(total_income)
        expense_data.append(total_expense)
        savings_data.append(savings)

    return {
        "labels": labels,
        "income": income_data,
        "expense": expense_data,
        "savings": savings_data,
    }


def calculate_monthly_savings_rate_by_year(transactions, user) -> Dict[str, object]:
    """
    Calculate monthly savings rate (%) grouped by year, plus an all-time
    per-month average line.

    Savings rate = ((income - expense) / income) * 100, per calendar month.

    Rules:
    - If income is 0 for a month, that month's rate is None (not 0) — avoid
      implying "broke even" when there was actually no income data.
    - Months in the current year that haven't occurred yet are None, not 0.
    - The all-time average per month index (Jan..Dec) is the mean of that
      month's rate across all years where the rate is not None.
    - Only include the last 3 distinct years present in the data (or fewer
      if the account has less history — do not pad with fake years).

    Returns:
        {
            "months": ["Jan", ..., "Dec"],
            "years": [2024, 2025, 2026],   # sorted ascending, whatever's present
            "by_year": {"2024": [12 values or None], "2025": [...], "2026": [...]},
            "all_time_avg": [12 values or None]
        }
    """
    current_date = timezone.now()
    current_year = current_date.year
    current_month = current_date.month

    monthly_data = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False
        )
        .values("date__year", "date__month")
        .annotate(
            total_expense=Sum("amount", filter=Q(type="Expense")),
            total_income=Sum("amount", filter=Q(type="Income")),
        )
    )

    years_present = set(item["date__year"] for item in monthly_data if item["date__year"])
    
    if not years_present:
        return {
            "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "years": [],
            "by_year": {},
            "all_time_avg": [None] * 12
        }

    sorted_years = sorted(list(years_present))
    target_years = sorted_years[-3:]
    
    year_data = {str(year): [None] * 12 for year in target_years}
    
    for item in monthly_data:
        yr = item["date__year"]
        mth = item["date__month"]
        if yr in target_years and yr and mth:
            income = float(item["total_income"] or 0)
            expense = float(item["total_expense"] or 0)
            
            if income == 0:
                rate = None
            else:
                rate = round(((income - expense) / income) * 100, 1)
            
            if yr == current_year and mth > current_month:
                rate = None
                
            year_data[str(yr)][mth - 1] = rate
            
    all_time_avg = [None] * 12
    for m in range(12):
        valid_rates = [year_data[str(yr)][m] for yr in target_years if year_data[str(yr)][m] is not None]
        if valid_rates:
            all_time_avg[m] = round(sum(valid_rates) / len(valid_rates), 1)
            
    return {
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "years": target_years,
        "by_year": year_data,
        "all_time_avg": all_time_avg
    }


def calculate_top_expenses(transactions, user, limit=5) -> Dict[str, list]:
    """
    Calculate top expense categories for the current month.
    
    Used for Top 5 Expenses chart.

    Args:
        transactions: QuerySet of Transaction objects.
        user: The Django user object.
        limit: Number of top categories to return (default: 5).

    Returns:
        Dict containing category labels and amounts.
    """
    current_date = timezone.now()
    
    top_categories = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            type="Expense",
            date__month=current_date.month,
            date__year=current_date.year,
        )
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:limit]
    )
    
    return {
        "labels": [item["category"] for item in top_categories],
        "amounts": [float(item["total"]) for item in top_categories],
    }


def calculate_savings_rate(transactions, user) -> float:
    """
    Calculate savings rate as percentage of income for the current month.
    
    Used for Savings Rate Gauge chart.

    Args:
        transactions: QuerySet of Transaction objects.
        user: The Django user object.

    Returns:
        Float representing savings rate percentage (0-100).
    """
    current_date = timezone.now()
    
    totals = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            date__month=current_date.month,
            date__year=current_date.year,
        )
        .values("type")
        .annotate(total=Sum("amount"))
    )
    
    income = next(
        (float(item["total"]) for item in totals if item["type"] == "Income"), 0
    )
    expense = next(
        (float(item["total"]) for item in totals if item["type"] == "Expense"), 0
    )
    
    if income == 0:
        return 0.0
    
    savings_rate = ((income - expense) / income) * 100
    return round(max(0, min(100, savings_rate)), 1)  # Clamp between 0-100


def calculate_income_sources(transactions, user) -> Dict[str, list]:
    """
    Calculate income breakdown by category for current month.
    
    Used for Income Sources chart.

    Args:
        transactions: QuerySet of Transaction objects.
        user: The Django user object.

    Returns:
        Dict containing income source labels and amounts.
    """
    current_date = timezone.now()
    
    income_data = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            type="Income",
            date__month=current_date.month,
            date__year=current_date.year,
        )
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    
    return {
        "labels": [item["category"] for item in income_data],
        "amounts": [float(item["total"]) for item in income_data],
    }


def get_date_range(period: str) -> Dict[str, Any]:
    """
    Convert period string to date range for filtering.
    
    Supports multiple period options for dashboard filtering.

    Args:
        period: Period identifier string.
            Options: 'this_month', 'last_3_months', 'last_6_months', 
                     'this_year', 'all'

    Returns:
        Dict with 'start' and 'end' date objects.
    """
    from datetime import date
    
    today = timezone.now().date()
    
    ranges = {
        'this_month': {
            'start': today.replace(day=1),
            'end': today,
            'label': 'This Month'
        },
        'last_month': {
            'start': (timezone.now() - relativedelta(months=1)).replace(day=1).date(),
            'end': (today.replace(day=1) - relativedelta(days=1)),
            'label': 'Last Month'
        },
        'last_3_months': {
            'start': (timezone.now() - relativedelta(months=3)).date(),
            'end': today,
            'label': 'Last 3 Months'
        },
        'last_6_months': {
            'start': (timezone.now() - relativedelta(months=6)).date(),
            'end': today,
            'label': 'Last 6 Months'
        },
        'this_year': {
            'start': today.replace(month=1, day=1),
            'end': today,
            'label': 'This Year'
        },
        'all': {
            'start': date(2000, 1, 1),
            'end': today + relativedelta(years=50),
            'label': 'All Time'
        }
    }
    
    return ranges.get(period, ranges['this_month'])





def get_service_status(user) -> Dict[str, bool]:
    """
    Get user's access status for all modules from database.

    Args:
        user: The Django user object.

    Returns:
        Dict mapping module titles to access status (True/False).
    """
    all_modules = UtilityModule.objects.all().order_by("display_order")
    return {module.title: module.has_access(user) for module in all_modules}


@login_required
def utilities(request):
    """
    Utilities home page view.

    Displays all available utility modules for the user.

    Args:
        request: Django HTTP request object.

    Returns:
        HttpResponse: Rendered utilities page.
    """
    user = request.user

    items = module_registry.get_modules_for_user(user)
    counterparties = get_counter_parties(user)
    counterparty_tabs_json = get_counterparty_tabs_json(user)

    return render(
        request,
        "utiltities.html",
        {
            "items": items,
            "counterparties": counterparties,
            "counterparty_tabs_json": counterparty_tabs_json,
        },
    )


# ============================================================================
# Authentication & Registration Views
# ============================================================================


def index(request):
    """
    Landing page view for non-authenticated users.

    Displays active utility modules that are marked to show on landing page.
    Redirects to dashboard if user is already authenticated.

    Args:
        request: Django HTTP request object.

    Returns:
        HttpResponse: Rendered landing page or redirect to dashboard.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    # Get active modules from database for landing page
    modules = UtilityModule.objects.filter(
        is_active=True, show_on_landing=True
    ).order_by("display_order")

    data = [
        {
            "icon": module.icon or "fa-puzzle-piece",
            "title": module.landing_title or module.title,
            "description": module.landing_description or module.description,
        }
        for module in modules
    ]

    return render(request, "landing_page.html", {"data": data})


@login_required

@login_required
def dashboard(request):
    """
    Main dashboard view with financial analytics, reminders, and tasks.

    Displays comprehensive overview including:
    - Financial overview (income, expense, savings, etc.)
    - Today's active reminders
    - Pending tasks till today
    - Category-wise expenses
    - Monthly savings for last 12 months
    - Year-wise income and expense
    - Current month's category breakdown
    
    Supports date range filtering via ?period= parameter.

    Args:
        request: Django HTTP request object.

    Returns:
        HttpResponse: Rendered dashboard with analytics data.
    """
    user = request.user
    
    # Get period filter from query params (default: this_month)
    period = request.GET.get('period', 'all')
    date_range = get_date_range(period)

    # Fetch transactions filtered by date range
    transactions = Transaction.objects.filter(
        created_by=user, 
        is_deleted=False,
        date__gte=date_range['start'],
        date__lte=date_range['end']
    )

    # User information
    user_info = {
        "first_txn_date": (
            min(entry.date for entry in transactions if entry.category.lower())
            if transactions
            else ""
        ),
        "account_age": (timezone.now() - user.date_joined).days,
    }

    # Financial overview
    financial_data = calculate_financial_overview(transactions)

    # Analytics data
    analytics = {
        "category_wise_data": calculate_category_wise_expenses(transactions),
        "savings": calculate_monthly_savings(transactions, user),
        "year_wise_data": calculate_year_wise_data(transactions, user),
        "category_wise_month": calculate_current_month_category_expenses(
            transactions, user
        ),
        # New analytics for enhanced charts
        "monthly_cash_flow": calculate_monthly_income_expense(transactions, user),
        "monthly_savings_rate": calculate_monthly_savings_rate_by_year(transactions, user),
        "top_expenses": calculate_top_expenses(transactions, user),
        "savings_rate": calculate_savings_rate(transactions, user),
        "income_sources": calculate_income_sources(transactions, user),
    }


    context = {
        "data": json.dumps(analytics, default=convert_decimal),
        "financial_data": financial_data,
        "emi_due_display": financial_data.get("EMI Due", "₹0"),
        "split_due_display": financial_data.get("Split Due", "₹0"),
        "user_info": user_info,
        "user": user,
        "today": date.today(),
        "current_period": period,
        "period_label": date_range['label'],
        "counterparties": get_counter_parties(user),
        "counterparty_tabs_json": get_counterparty_tabs_json(user),
    }

    return render(request, "dashboard.html", context=context)


@login_required
def profile(request):
    """
    User profile view.

    Displays user profile information
    and account statistics.

    Args:
        request: Django HTTP request object.

    Returns:
        HttpResponse: Rendered profile page.
    """
    user = request.user

    # Fetch accessible modules for the user
    accessible_modules = module_registry.get_modules_for_user(user)

    # Calculate account statistics
    account_age = (timezone.now() - user.date_joined).days
    total_transactions = Transaction.objects.filter(
        created_by=user, is_deleted=False
    ).count()

    context = {
        "user": user,
        "accessible_modules": accessible_modules,
        "account_age": account_age,
        "total_transactions": total_transactions,
        "counterparties": get_counter_parties(user),
        "counterparty_tabs_json": get_counterparty_tabs_json(user),
    }

    # Add admin-specific data
    if user.is_superuser:
        refresh_token_time = (
            RefreshToken.objects.filter(is_active=True)
            .order_by("-created_at")
            .first()
        )
        context["last_genration"] = (
            refresh_token_time.created_at if refresh_token_time else "N/A"
        )

    return render(request, "profile.html", context=context)


@login_required
def update_profile(request):
    """
    Handle profile picture upload and name update via AJAX.

    Accepts POST requests with profile picture file and/or name update.
    Deletes old profile picture before saving new one.

    Args:
        request: Django HTTP request object.

    Returns:
        JsonResponse: Success/failure status with message and updated data.
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method"}, status=405
        )

    user = request.user

    # Handle name update
    new_name = request.POST.get("name")
    if new_name and new_name.strip():
        name_parts = new_name.rsplit(" ", 1)
        user.first_name = name_parts[0].strip()
        user.last_name = name_parts[1].strip() if len(name_parts) > 1 else ''
        user.save()

    # Handle profile picture upload
    if request.FILES.get("profile_picture"):
        # Delete old picture if exists
        if user.profile_picture:
            user.profile_picture.delete(save=False)

        user.profile_picture = request.FILES["profile_picture"]
        user.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Profile updated successfully",
                "profile_picture_url": (
                    user.profile_picture.url if user.profile_picture else None
                ),
            }
        )

    return JsonResponse({"success": True, "message": "Name updated successfully"})


@login_required
@login_required
def manual_backup(request):
    """
    Manually trigger database backup (superuser only).
    
    Executes the backup_db management command programmatically.
    Restricted to superusers only.
    
    Args:
        request: Django HTTP request object
        
    Returns:
        JsonResponse: Backup status and message
    """
    from django.contrib import messages
    from django.core.management import call_command
    from io import StringIO
    import sys
    
    # Restrict to superusers only
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('profile')
    
    try:
        # Capture management command output
        output = StringIO()
        call_command('backup_db', stdout=output)
        
        # Get the output
        backup_output = output.getvalue()
        
        messages.success(request, "Database backup completed successfully!")
        
        # Return JSON if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Backup completed successfully',
                'output': backup_output
            })
        
        # Redirect to profile for normal requests
        return redirect('profile')
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        
        messages.error(request, f"Backup failed: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': str(e),
                'details': error_details
            }, status=500)
        
        return redirect('profile')



