"""
Finance views — Account, Category, and Entry CRUD.

This module implements the core expense/income tracking functionality:
- Account list, create, edit (bank/cash/wallet accounts)
- Category list, create, edit (expense/income categories)
- Entry create, list (with filters), edit, delete
"""

import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Account, Category, Entry


# ============================================================================
# Account Views
# ============================================================================

@login_required
def account_list(request: HttpRequest) -> HttpResponse:
    """List all accounts for the current user."""
    accounts = Account.objects.filter(created_by=request.user).order_by('name')
    return render(request, 'finance/account_list.html', {'accounts': accounts})


@login_required
def account_create(request: HttpRequest) -> HttpResponse:
    """Create a new account."""
    if request.method == 'GET':
        return render(request, 'finance/account_form.html', {
            'account_types': Account.ACCOUNT_TYPE_CHOICES,
            'mode': 'create',
        })

    name = request.POST.get('name', '').strip()
    account_type = request.POST.get('account_type', 'bank')

    if not name:
        messages.error(request, 'Account name is required.')
        return render(request, 'finance/account_form.html', {
            'account_types': Account.ACCOUNT_TYPE_CHOICES,
            'mode': 'create',
            'form_data': {'name': name, 'account_type': account_type},
        })

    Account.objects.create(
        name=name,
        account_type=account_type,
        is_active=True,
        created_by=request.user,
    )
    messages.success(request, f'Account "{name}" created.')
    return redirect('finance:account_list')


@login_required
def account_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit an existing account."""
    account = get_object_or_404(Account, pk=pk, created_by=request.user)

    if request.method == 'GET':
        return render(request, 'finance/account_form.html', {
            'account': account,
            'account_types': Account.ACCOUNT_TYPE_CHOICES,
            'mode': 'edit',
        })

    name = request.POST.get('name', '').strip()
    account_type = request.POST.get('account_type', account.account_type)
    is_active = request.POST.get('is_active') == 'on'

    if not name:
        messages.error(request, 'Account name is required.')
        return render(request, 'finance/account_form.html', {
            'account': account,
            'account_types': Account.ACCOUNT_TYPE_CHOICES,
            'mode': 'edit',
        })

    account.name = name
    account.account_type = account_type
    account.is_active = is_active
    account.save()

    messages.success(request, f'Account "{name}" updated.')
    return redirect('finance:account_list')


# ============================================================================
# Category Views
# ============================================================================

@login_required
def category_list(request: HttpRequest) -> HttpResponse:
    """List all categories for the current user."""
    categories = Category.objects.filter(created_by=request.user).order_by('category_type', 'name')
    return render(request, 'finance/category_list.html', {'categories': categories})


@login_required
def category_create(request: HttpRequest) -> HttpResponse:
    """Create a new category."""
    if request.method == 'GET':
        return render(request, 'finance/category_form.html', {
            'category_types': Category.CATEGORY_TYPE_CHOICES,
            'mode': 'create',
        })

    name = request.POST.get('name', '').strip()
    category_type = request.POST.get('category_type', 'expense')

    if not name:
        messages.error(request, 'Category name is required.')
        return render(request, 'finance/category_form.html', {
            'category_types': Category.CATEGORY_TYPE_CHOICES,
            'mode': 'create',
        })

    Category.objects.create(
        name=name,
        category_type=category_type,
        is_active=True,
        created_by=request.user,
    )
    messages.success(request, f'Category "{name}" created.')
    return redirect('finance:category_list')


@login_required
def category_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit an existing category."""
    category = get_object_or_404(Category, pk=pk, created_by=request.user)

    if request.method == 'GET':
        return render(request, 'finance/category_form.html', {
            'category': category,
            'category_types': Category.CATEGORY_TYPE_CHOICES,
            'mode': 'edit',
        })

    name = request.POST.get('name', '').strip()
    category_type = request.POST.get('category_type', category.category_type)
    is_active = request.POST.get('is_active') == 'on'

    if not name:
        messages.error(request, 'Category name is required.')
        return render(request, 'finance/category_form.html', {
            'category': category,
            'category_types': Category.CATEGORY_TYPE_CHOICES,
            'mode': 'edit',
        })

    category.name = name
    category.category_type = category_type
    category.is_active = is_active
    category.save()

    messages.success(request, f'Category "{name}" updated.')
    return redirect('finance:category_list')


# ============================================================================
# Entry Views
# ============================================================================

@login_required
def entry_list(request: HttpRequest) -> HttpResponse:
    """
    List entries for the current user.
    Supports filtering by date range, account, category, and entry_type.
    Defaults to current month.
    """
    user = request.user

    # --- Filter params ---
    entry_type_filter = request.GET.get('type', '')   # expense/income/all
    account_id = request.GET.get('account', '')
    category_id = request.GET.get('category', '')
    period = request.GET.get('period', 'this_month')

    # --- Date range ---
    today = date.today()
    if period == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
    elif period == 'last_month':
        first_of_this = today.replace(day=1)
        last_month_end = first_of_this - timedelta(days=1)
        start_date = last_month_end.replace(day=1)
        end_date = last_month_end
    elif period == 'last_7':
        start_date = today - timedelta(days=6)
        end_date = today
    elif period == 'last_30':
        start_date = today - timedelta(days=29)
        end_date = today
    else:  # 'all'
        start_date = None
        end_date = None

    # --- Queryset ---
    entries = Entry.objects.filter(
        created_by=user,
        entry_type__in=['expense', 'income'],  # Only expense/income in this view
    ).select_related('account', 'category').order_by('-date', '-created_at')

    if start_date:
        entries = entries.filter(date__gte=start_date)
    if end_date:
        entries = entries.filter(date__lte=end_date)
    if entry_type_filter in ('expense', 'income'):
        entries = entries.filter(entry_type=entry_type_filter)
    if account_id:
        entries = entries.filter(account_id=account_id)
    if category_id:
        entries = entries.filter(category_id=category_id)

    # --- Summary totals ---
    totals = entries.aggregate(
        total_expense=Sum('amount', filter=Q(entry_type='expense')),
        total_income=Sum('amount', filter=Q(entry_type='income')),
    )
    total_expense = totals['total_expense'] or 0
    total_income = totals['total_income'] or 0

    # --- Filter options ---
    accounts = Account.objects.filter(created_by=user, is_active=True).order_by('name')
    categories = Category.objects.filter(created_by=user, is_active=True).order_by('name')

    # --- Pagination (25 rows per page) ---
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(entries, 25)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    return render(request, 'finance/entry_list.html', {
        'entries': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'accounts': accounts,
        'categories': categories,
        'total_expense': total_expense,
        'total_income': total_income,
        'net': total_income - total_expense,
        'filters': {
            'period': period,
            'type': entry_type_filter,
            'account': account_id,
            'category': category_id,
        },
    })


@login_required
def entry_create(request: HttpRequest) -> HttpResponse:
    """
    Create a new expense or income entry.
    GET: Show form with smart defaults (last-used account, most-used category, today's date).
    POST: Validate and save.
    """
    user = request.user

    # --- Smart defaults ---
    last_entry = (
        Entry.objects
        .filter(created_by=user, entry_type__in=['expense', 'income'])
        .order_by('-created_at')
        .first()
    )
    default_account_id = last_entry.account_id if last_entry else None

    from django.db.models import Count
    most_used_category = (
        Entry.objects
        .filter(created_by=user, entry_type='expense', category__isnull=False)
        .values('category_id')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
        .first()
    )
    default_category_id = most_used_category['category_id'] if most_used_category else None

    accounts = Account.objects.filter(created_by=user, is_active=True).order_by('name')
    expense_categories = Category.objects.filter(
        created_by=user, is_active=True, category_type='expense'
    ).order_by('name')
    income_categories = Category.objects.filter(
        created_by=user, is_active=True, category_type='income'
    ).order_by('name')

    recent_chips = (
        Entry.objects
        .filter(created_by=user, entry_type='expense', category__isnull=False)
        .values('amount', 'category_id', 'category__name', 'note')
        .annotate(cnt=Count('id'))
        .order_by('-cnt', '-amount')[:5]
    )

    if request.method == 'GET':
        return render(request, 'finance/entry_form.html', {
            'mode': 'create',
            'accounts': accounts,
            'expense_categories': expense_categories,
            'income_categories': income_categories,
            'today': today_str(),
            'default_account_id': default_account_id,
            'default_category_id': default_category_id,
            'recent_chips': recent_chips,
        })

    # --- POST: save entry ---
    entry_type = request.POST.get('entry_type', 'expense')
    account_id = request.POST.get('account_id')
    amount_str = request.POST.get('amount', '').strip()
    entry_date_str = request.POST.get('date', '').strip()
    category_id = request.POST.get('category_id', '') or None
    note = request.POST.get('note', '').strip()

    errors = []
    if not account_id:
        errors.append('Please select an account.')
    if not amount_str:
        errors.append('Amount is required.')
    else:
        try:
            amount = float(amount_str)
            if amount <= 0:
                errors.append('Amount must be positive.')
        except ValueError:
            errors.append('Invalid amount.')
            amount = None
    if not entry_date_str:
        errors.append('Date is required.')

    if errors:
        for err in errors:
            messages.error(request, err)
        return render(request, 'finance/entry_form.html', {
            'mode': 'create',
            'accounts': accounts,
            'expense_categories': expense_categories,
            'income_categories': income_categories,
            'today': today_str(),
            'form_data': request.POST,
        })

    account = get_object_or_404(Account, pk=account_id, created_by=user)
    category = None
    if category_id:
        category = get_object_or_404(Category, pk=category_id, created_by=user)

    Entry.objects.create(
        account=account,
        entry_type=entry_type,
        amount=amount,
        date=entry_date_str,
        category=category,
        note=note,
        created_by=user,
    )
    messages.success(request, f'{entry_type.title()} of ₹{amount} recorded.')
    return redirect('finance:entry_list')


@login_required
def entry_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit an existing expense/income entry."""
    user = request.user
    entry = get_object_or_404(Entry, pk=pk, created_by=user)

    # Only allow editing expense/income entries in this view
    if entry.entry_type not in ('expense', 'income'):
        messages.error(request, 'This entry type cannot be edited here.')
        return redirect('finance:entry_list')

    accounts = Account.objects.filter(created_by=user, is_active=True).order_by('name')
    expense_categories = Category.objects.filter(
        created_by=user, is_active=True, category_type='expense'
    ).order_by('name')
    income_categories = Category.objects.filter(
        created_by=user, is_active=True, category_type='income'
    ).order_by('name')

    if request.method == 'GET':
        return render(request, 'finance/entry_form.html', {
            'mode': 'edit',
            'entry': entry,
            'accounts': accounts,
            'expense_categories': expense_categories,
            'income_categories': income_categories,
            'today': today_str(),
        })

    # POST: update
    entry_type = request.POST.get('entry_type', entry.entry_type)
    account_id = request.POST.get('account_id', entry.account_id)
    amount_str = request.POST.get('amount', '').strip()
    entry_date_str = request.POST.get('date', '').strip()
    category_id = request.POST.get('category_id', '') or None
    note = request.POST.get('note', '').strip()

    try:
        amount = float(amount_str)
    except (ValueError, TypeError):
        messages.error(request, 'Invalid amount.')
        return redirect('finance:entry_edit', pk=pk)

    account = get_object_or_404(Account, pk=account_id, created_by=user)
    category = None
    if category_id:
        category = get_object_or_404(Category, pk=category_id, created_by=user)

    entry.entry_type = entry_type
    entry.account = account
    entry.amount = amount
    entry.date = entry_date_str
    entry.category = category
    entry.note = note
    entry.save()

    messages.success(request, 'Entry updated.')
    return redirect('finance:entry_list')


@login_required
@require_POST
def entry_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete an entry. POST only for CSRF protection."""
    entry = get_object_or_404(Entry, pk=pk, created_by=request.user)
    entry.delete()
    messages.success(request, 'Entry deleted.')
    return redirect('finance:entry_list')


# ============================================================================
# Helpers
# ============================================================================

def today_str() -> str:
    return date.today().isoformat()
