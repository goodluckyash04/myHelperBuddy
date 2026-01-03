import json
import re
from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.services.security_services import security_service

from ..decorators import auth_user
from ..models import LedgerTransaction, RefreshToken, Transaction
from ..utilitie_functions import convert_decimal, format_amount
from .view_reminder import calculate_reminder


def get_counter_parties(user):
    return (
        LedgerTransaction.objects.filter(created_by=user)
        .values_list("counterparty", flat=True)
        .distinct()
    )


def calculate_financial_overview(transactions):
    """Optimized using database aggregations instead of Python loops."""
    from django.db.models import Sum, DecimalField
    
    aggregations = transactions.aggregate(
        income=Sum('amount', filter=Q(type__iexact='income', is_deleted=False), output_field=DecimalField()),
        expense=Sum('amount', filter=Q(
            type__iexact='expense',
            status__iexact='completed'
        ) & ~Q(category__iexact='investment'), output_field=DecimalField()),
        investment=Sum('amount', filter=Q(
            category__iexact='investment',
            status__iexact='completed'
        ), output_field=DecimalField()),
        overdue=Sum('amount', filter=Q(
            category__iexact='emi',
            status__iexact='pending'
        ), output_field=DecimalField()),
    )
    
    income = aggregations['income'] or 0
    expense = aggregations['expense'] or 0
    investment = aggregations['investment'] or 0
    overdue = aggregations['overdue'] or 0
    
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


def calculate_category_wise_expenses(transactions):
    """Optimized using database aggregations grouped by category."""
    from django.db.models import Sum
    
    category_data = transactions.filter(
        type__iexact="Expense", 
        date__lte=datetime.now().date()
    ).values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    category_wise_data = {item['category']: item['total'] for item in category_data}
    return category_wise_data


def calculate_monthly_savings(transactions, user):
    current_date = timezone.now()

    last_12_months = [(current_date - relativedelta(months=i)).month for i in range(12)]
    last_12_months_years = [
        (current_date - relativedelta(months=i)).year for i in range(12)
    ]

    transactions = (
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
                for transaction in transactions
                if transaction["date__month"] == month
                and transaction["date__year"] == year
            ),
            {},
        )
        total_expense = month_data.get("total_expense") or 0
        total_income = month_data.get("total_income") or 0

        savings = total_income - total_expense
        label = datetime(year, month, 1).strftime("%b'%y")  # Format as Jan'24
        savings_data[label] = float(savings)

    return savings_data


def calculate_year_wise_data(transactions, user):
    current_date = timezone.now()

    if current_date.month == 12:
        first_day_of_next_month = datetime(current_date.year + 1, 1, 1)
    else:
        first_day_of_next_month = datetime(current_date.year, current_date.month + 1, 1)

    transactions = (
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
    year_wise_data = {}
    year_wise_data["income"] = [i["total_income"] for i in transactions]
    year_wise_data["expense"] = [i["total_expense"] for i in transactions]
    year_wise_data["label"] = [i["date__year"] for i in transactions]
    return year_wise_data


def calculate_current_month_category_expenses(transactions, user):
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

    category_wise = {}

    category_wise["labels"] = [i["category"] for i in category_expenses]
    category_wise["amount"] = [i["amount"] for i in category_expenses]

    income_total = next(
        (item["amount"] for item in total if item["type"] == "Income"), 0
    )
    expense_total = next(
        (item["amount"] for item in total if item["type"] == "Expense"), 0
    )

    category_wise["labels"].append("Balance")
    category_wise["amount"].append(income_total - expense_total)
    return category_wise


# ...........................................Index..................................................
def index(request):
    if request.session.get("username"):
        return redirect("dashboard")
    
    # Get active modules from database for landing page
    from accounts.models import UtilityModule
    
    # Only show modules that are marked to appear on landing page
    modules = UtilityModule.objects.filter(
        is_active=True, 
        show_on_landing=True
    ).order_by('display_order')
    
    data = [
        {
            "icon": module.icon or "fa-puzzle-piece",
            "title": module.landing_title or module.title,
            "description": module.landing_description or module.description,
        }
        for module in modules
    ]
    
    return render(request, "landing_page.html", {"data": data})


# ...........................................About..................................................
@auth_user
def about(request, user):
    return render(request, "about.html", {"user": user})


# ...........................................Dashboard..................................................
@auth_user
def dashboard(request, user):
    transactions = Transaction.objects.filter(created_by=user, is_deleted=False)

    user_info = {}
    user_info["first_txn_date"] = (
        min(entry.date for entry in transactions if entry.category.lower())
        if transactions
        else ""
    )
    user_info["account_age"] = (timezone.now() - user.date_joined).days

    # Financial Overview
    financial_data = calculate_financial_overview(transactions)

    context = {}
    # Category-wise expense calculations
    context["category_wise_data"] = calculate_category_wise_expenses(transactions)

    # Monthly savings of the last 12 months
    context["savings"] = calculate_monthly_savings(transactions, user)

    # Year-wise income and expense
    context["year_wise_data"] = calculate_year_wise_data(transactions, user)

    # Current month's category-wise expense
    context["category_wise_month"] = calculate_current_month_category_expenses(
        transactions, user
    )

    context = {
        "data": json.dumps(context, default=convert_decimal),
        "financial_data": financial_data,
        "user_info": user_info,
        "user": user,
    }

    return render(request, "dashboard.html", context=context)


# ...........................................Home Page..................................................
@auth_user
def utilities(request, user):
    from accounts.services.module_registry import module_registry
    
    # Get modules accessible to this user from the registry
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


@auth_user
def profile(request, user):
    from accounts.models import UtilityModule
    
    # Get accessible modules with full details (icons, names, etc.)
    accessible_modules = [
        {
            'title': module.title,
            'icon': module.icon or 'fa-puzzle-piece',
            'access_type': module.get_access_type_display(),
        }
        for module in UtilityModule.objects.filter(is_active=True)
        if module.has_access(user)
    ]
    
    # Calculate account statistics
    account_age = (timezone.now() - user.date_joined).days
    total_transactions = Transaction.objects.filter(created_by=user, is_deleted=False).count()
    
    context = {
        "user": user,
        "service_status": get_service_status(user),
        "accessible_modules": accessible_modules,
        "account_age": account_age,
        "total_transactions": total_transactions,
    }
    
    if user.username == settings.ADMIN:
        refresh_token_time = (
            RefreshToken.objects.filter(is_active=True).order_by("-created_at").first()
        )
        context["last_genration"] = (
            refresh_token_time.created_at if refresh_token_time else "N/A"
        )
    
    return render(request, "profile.html", context=context)


@auth_user
def update_profile(request, user):
    """Handle profile picture upload and name update"""
    if request.method == "POST":
        import json
        from django.http import JsonResponse
        
        # Handle name update
        new_name = request.POST.get('name')
        if new_name and new_name.strip():
            user.name = new_name.strip()
            user.save()
        
        # Handle profile picture upload
        if request.FILES.get('profile_picture'):
            # Delete old picture if exists
            if user.profile_picture:
                user.profile_picture.delete(save=False)
            
            user.profile_picture = request.FILES['profile_picture']
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully',
                'profile_picture_url': user.profile_picture.url if user.profile_picture else None
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Name updated successfully'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def get_service_status(user):
    """Get user's access status for all modules from database"""
    from accounts.models import UtilityModule
    
    # Get all modules and check access for this user
    all_modules = UtilityModule.objects.all().order_by('display_order')
    
    return {
        module.title: module.has_access(user)
        for module in all_modules
    }


@auth_user
def redirect_to_streamlit(request, user):
    token = security_service.encrypt_text(
        {"user_id": user.id, "username": user.username}
    )
    return redirect(f"{settings.STREAMLIT_URL}?_id={token}")
