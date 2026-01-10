"""
Core views for the MyHelperBuddy accounts application.

This module contains main views for dashboard, profile, utilities,
and various analytics/statistics calculations.
"""

import json
import re
from datetime import datetime
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
    Task,
    Transaction,
)
from accounts.services.module_registry import module_registry
from accounts.services.security_services import security_service
from accounts.utilitie_functions import convert_decimal, format_amount
from accounts.views.view_reminder import calculate_reminder


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
        .values_list("counterparty", flat=True)
        .distinct()
    )


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
    )

    income = aggregations["income"] or 0
    expense = aggregations["expense"] or 0
    investment = aggregations["investment"] or 0
    overdue = aggregations["overdue"] or 0

    # Split due requires regex match, so we still need Python loop for this
    split_due = sum(
        entry.amount
        for entry in transactions.filter(status__iexact="pending")
        if re.search(r"Split\s\d{1,2}$", entry.description, re.IGNORECASE)
    )

    return {
        "Income": format_amount(income),
        "Expense": format_amount(expense),
        "Saving": format_amount(income - expense - investment - split_due),
        "EMI Due": format_amount(overdue),
        "Investment": format_amount(investment),
        "Split Due": format_amount(split_due),
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

    return {item["category"]: item["total"] for item in category_data}


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


def calculate_weekly_spending(transactions, user) -> Dict[str, list]:
    """
    Calculate daily spending for the last 30 days.
    
    Used for Weekly Spending Trend chart to identify spending patterns.

    Args:
        transactions: QuerySet of Transaction objects.
        user: The Django user object.

    Returns:
        Dict containing date labels and daily expense amounts.
    """
    from datetime import timedelta
    
    current_date = timezone.now().date()
    start_date = current_date - timedelta(days=29)  # Last 30 days including today
    
    daily_data = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            type="Expense",
            date__gte=start_date,
            date__lte=current_date,
        )
        .values("date")
        .annotate(total=Sum("amount"))
        .order_by("date")
    )
    
    # Create a complete date range with 0 for days with no expenses
    date_dict = {item["date"]: float(item["total"]) for item in daily_data}
    
    labels = []
    amounts = []
    
    for i in range(30):
        date = start_date + timedelta(days=i)
        labels.append(date.strftime("%d %b"))
        amounts.append(date_dict.get(date, 0))
    
    return {
        "labels": labels,
        "amounts": amounts,
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


def calculate_key_metrics(transactions, user) -> Dict[str, Any]:
    """
    Calculate key summary metrics for dashboard cards.
    
    Provides:
    - Average daily spending for current month
    - Month-over-month spending change
    - Spending trend vs 3-month average
    - Largest expense with details

    Args:
        transactions: QuerySet of Transaction objects.
        user: The Django user object.

    Returns:
        Dict containing key metrics for dashboard display.
    """
    from datetime import timedelta
    
    current_date = timezone.now()
    current_month_start = current_date.replace(day=1).date()
    
    # Calculate days in current month so far
    days_in_month = (current_date.date() - current_month_start).days + 1
    
    # Current month data
    current_month_expense = float(
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            type="Expense",
            date__gte=current_month_start,
            date__lte=current_date.date()
        ).aggregate(total=Sum("amount"))["total"] or 0
    )
    
    # Average daily spending
    avg_daily_spending = current_month_expense / days_in_month if days_in_month > 0 else 0
    
    # Last month data for comparison
    last_month_start = (current_date - relativedelta(months=1)).replace(day=1).date()
    last_month_end = current_month_start - timedelta(days=1)
    
    last_month_expense = float(
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            type="Expense",
            date__gte=last_month_start,
            date__lte=last_month_end
        ).aggregate(total=Sum("amount"))["total"] or 0
    )
    
    # Month-over-month change
    if last_month_expense > 0:
        mom_change = ((current_month_expense - last_month_expense) / last_month_expense) * 100
        mom_direction = "up" if mom_change > 0 else "down"
    else:
        mom_change = 0
        mom_direction = "neutral"
    
    # 3-month average for trend analysis
    three_months_ago = (current_date - relativedelta(months=3)).date()
    
    three_month_avg = float(
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            type="Expense",
            date__gte=three_months_ago,
            date__lt=current_month_start
        ).aggregate(total=Sum("amount"))["total"] or 0
    ) / 3
    
    # Spending trend
    if three_month_avg > 0:
        if current_month_expense > three_month_avg * 1.1:
            spending_trend = "higher"
        elif current_month_expense < three_month_avg * 0.9:
            spending_trend = "lower"
        else:
            spending_trend = "normal"
    else:
        spending_trend = "normal"
    
    # Largest expense this month
    largest = (
        Transaction.objects.filter(
            created_by=user,
            is_deleted=False,
            type="Expense",
            date__gte=current_month_start,
            date__lte=current_date.date()
        )
        .order_by("-amount")
        .first()
    )
    
    largest_expense = {
        "amount": float(largest.amount) if largest else 0,
        "category": largest.category if largest else "N/A",
        "date": largest.date if largest else None,
    }
    
    return {
        "avg_daily_spending": round(avg_daily_spending, 2),
        "mom_change": round(abs(mom_change), 1),
        "mom_direction": mom_direction,
        "spending_trend": spending_trend,
        "largest_expense": largest_expense,
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
            'end': today,
            'label': 'All Time'
        }
    }
    
    return ranges.get(period, ranges['this_month'])


def calculate_comparison_data(user, period1: str, period2: str) -> Dict[str, Any]:
    """
    Calculate comparison between two time periods.
    
    Compares financial metrics between two periods for analysis.

    Args:
        user: The Django user object.
        period1: First period identifier (e.g., 'this_month').
        period2: Second period identifier (e.g., 'last_month').

    Returns:
        Dict with period1 data, period2 data, and percentage changes.
    """
    # Get date ranges for both periods
    range1 = get_date_range(period1)
    range2 = get_date_range(period2)
    
    # Fetch transactions for each period
    txn1 = Transaction.objects.filter(
        created_by=user,
        is_deleted=False,
        date__gte=range1['start'],
        date__lte=range1['end']
    )
    
    txn2 = Transaction.objects.filter(
        created_by=user,
        is_deleted=False,
        date__gte=range2['start'],
        date__lte=range2['end']
    )
    
    # Calculate totals for period 1
    p1_income = float(txn1.filter(type='Income').aggregate(
        total=Sum('amount'))['total'] or 0)
    p1_expense = float(txn1.filter(type='Expense').aggregate(
        total=Sum('amount'))['total'] or 0)
    p1_savings = p1_income - p1_expense
    
    # Calculate totals for period 2
    p2_income = float(txn2.filter(type='Income').aggregate(
        total=Sum('amount'))['total'] or 0)
    p2_expense = float(txn2.filter(type='Expense').aggregate(
        total=Sum('amount'))['total'] or 0)
    p2_savings = p2_income - p2_expense
    
    # Calculate percentage changes
    def calc_change(current, previous):
        if previous == 0:
            return 0
        return round(((current - previous) / previous) * 100, 1)
    
    return {
        'period1': {
            'label': range1['label'],
            'income': p1_income,
            'expense': p1_expense,
            'savings': p1_savings,
        },
        'period2': {
            'label': range2['label'],
            'income': p2_income,
            'expense': p2_expense,
            'savings': p2_savings,
        },
        'changes': {
            'income': calc_change(p1_income, p2_income),
            'expense': calc_change(p1_expense, p2_expense),
            'savings': calc_change(p1_savings, p2_savings),
        }
    }


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


# ============================================================================
# Public Views
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
def about(request):
    """
    About page view.

    Args:
        request: Django HTTP request object.

    Returns:
        HttpResponse: Rendered about page.
    """
    return render(request, "about.html", {"user": request.user})


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
    period = request.GET.get('period', 'this_month')
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
        "weekly_spending": calculate_weekly_spending(transactions, user),
        "top_expenses": calculate_top_expenses(transactions, user),
        "savings_rate": calculate_savings_rate(transactions, user),
        "income_sources": calculate_income_sources(transactions, user),
    }

    # Get today's reminders
    from accounts.views.view_reminder import calculate_reminder
    todays_reminders = calculate_reminder(user)

    # Get pending tasks till today
    from datetime import date
    today = date.today()
    pending_tasks = Task.objects.filter(
        created_by=user,
        is_deleted=False,
        status='Pending',
        complete_by_date__lte=today
    ).order_by('complete_by_date')[:10]  # Latest 10 pending tasks
    
    # Comparison mode support
    compare_mode = request.GET.get('compare', 'false') == 'true'
    comparison_data = None
    
    if compare_mode:
        period1 = request.GET.get('period1', 'this_month')
        period2 = request.GET.get('period2', 'last_month')
        comparison_data = calculate_comparison_data(user, period1, period2)

    context = {
        "data": json.dumps(analytics, default=convert_decimal),
        "financial_data": financial_data,
        "user_info": user_info,
        "user": user,
        "todays_reminders": todays_reminders[:5],  # Show top 5 reminders
        "pending_tasks": pending_tasks,
        "today": today,
        "key_metrics": calculate_key_metrics(transactions, user),
        "current_period": period,
        "period_label": date_range['label'],
        "compare_mode": compare_mode,
        "comparison_data": json.dumps(comparison_data, default=convert_decimal) if comparison_data else None,
    }

    return render(request, "dashboard.html", context=context)


@login_required
def utilities(request):
    """
    Utilities home page view.

    Displays all available utility modules for the user along with
    reminder count and counterparties.

    Args:
        request: Django HTTP request object.

    Returns:
        HttpResponse: Rendered utilities page.
    """
    user = request.user

    items = module_registry.get_modules_for_user(user)
    reminder_count = len(calculate_reminder(user))
    counterparties = get_counter_parties(user)

    return render(
        request,
        "utiltities.html",
        {
            "user": user,
            "items": items,
            "counterparties": counterparties,
            "badge": reminder_count,
        },
    )


@login_required
def profile(request):
    """
    User profile view.

    Displays user profile information, accessible modules,
    and account statistics.

    Args:
        request: Django HTTP request object.

    Returns:
        HttpResponse: Rendered profile page.
    """
    user = request.user

    # Get accessible modules with full details
    accessible_modules = [
        {
            "title": module.title,
            "icon": module.icon or "fa-puzzle-piece",
            "access_type": module.get_access_type_display(),
        }
        for module in UtilityModule.objects.filter(is_active=True)
        if module.has_access(user)
    ]

    # Calculate account statistics
    account_age = (timezone.now() - user.date_joined).days
    total_transactions = Transaction.objects.filter(
        created_by=user, is_deleted=False
    ).count()

    context = {
        "user": user,
        "service_status": get_service_status(user),
        "accessible_modules": accessible_modules,
        "account_age": account_age,
        "total_transactions": total_transactions,
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
def redirect_to_streamlit(request):
    """
    Redirect to Streamlit app with encrypted authentication token.

    Creates an encrypted token containing user ID and username,
    then redirects to the Streamlit URL with the token as a query parameter.

    Args:
        request: Django HTTP request object.

    Returns:
        HttpResponseRedirect: Redirect to Streamlit with auth token.
    """
    token = security_service.encrypt_text(
        {"user_id": request.user.id, "username": request.user.username}
    )
    return redirect(f"{settings.STREAMLIT_URL}?_id={token}")


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
        # Skip task reminders when manually triggered from UI
        call_command('backup_db', stdout=output, skip_reminders=True)
        
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
