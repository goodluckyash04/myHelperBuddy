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

    Args:
        request: Django HTTP request object.

    Returns:
        HttpResponse: Rendered dashboard with analytics data.
    """
    user = request.user

    # Fetch transactions once and reuse
    transactions = Transaction.objects.filter(created_by=user, is_deleted=False)

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

    context = {
        "data": json.dumps(analytics, default=convert_decimal),
        "financial_data": financial_data,
        "user_info": user_info,
        "user": user,
        "todays_reminders": todays_reminders[:5],  # Show top 5 reminders
        "pending_tasks": pending_tasks,
        "today": today,
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
