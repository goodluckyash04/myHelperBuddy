"""
Loan and Investment views — Phase 4 of the finance-first rebuild.

Features:
- Loan list, create, edit — tracks loan principal, EMI, account
- "Log EMI" one-tap action — creates Entry(entry_type='loan_emi')
- Investment list, create, edit — tracks SIP / recurring investment
- "Log Contribution" one-tap action — creates Entry(entry_type='investment_contribution')
"""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Account, Entry, Loan, Investment


# ============================================================================
# Loan Views
# ============================================================================

@login_required
def loan_list(request: HttpRequest) -> HttpResponse:
    """List all loans for the current user."""
    loans = Loan.objects.filter(created_by=request.user).select_related('account').order_by('name')

    # Compute total EMI paid per loan
    loan_data = []
    for loan in loans:
        emi_count = Entry.objects.filter(
            created_by=request.user, linked_loan=loan, entry_type='loan_emi'
        ).count()
        loan_data.append({'loan': loan, 'emi_count': emi_count})


    return render(request, 'finance/loan_list.html', {'loan_data': loan_data})


@login_required
def loan_create(request: HttpRequest) -> HttpResponse:
    """Create a new loan."""
    user = request.user
    accounts = Account.objects.filter(created_by=user, is_active=True).order_by('name')

    if request.method == 'GET':
        return render(request, 'finance/loan_form.html', {
            'accounts': accounts,
            'mode': 'create',
            'today': date.today().isoformat(),
            'form_data': {'name': '', 'principal': '', 'monthly_emi': '', 'account_id': '', 'start_date': ''},
        })

    name = request.POST.get('name', '').strip()
    principal_str = request.POST.get('principal', '').strip()
    emi_str = request.POST.get('monthly_emi', '').strip()
    account_id = request.POST.get('account_id', '')
    start_date = request.POST.get('start_date', '')

    errors = []
    if not name:
        errors.append('Loan name is required.')
    try:
        principal = float(principal_str)
    except (ValueError, TypeError):
        principal = None
        errors.append('Invalid principal amount.')
    try:
        emi = float(emi_str)
    except (ValueError, TypeError):
        emi = None
        errors.append('Invalid EMI amount.')
    if not account_id:
        errors.append('Please select an account.')

    if errors:
        for err in errors:
            messages.error(request, err)
        return render(request, 'finance/loan_form.html', {
            'accounts': accounts,
            'mode': 'create',
            'form_data': request.POST,
            'today': date.today().isoformat(),
        })

    account = get_object_or_404(Account, pk=account_id, created_by=user)
    Loan.objects.create(
        name=name,
        principal=principal,
        monthly_emi=emi,
        account=account,
        start_date=start_date or date.today(),
        is_active=True,
        created_by=user,
    )
    messages.success(request, f'Loan "{name}" created.')
    return redirect('finance:loan_list')


@login_required
def loan_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit an existing loan."""
    user = request.user
    loan = get_object_or_404(Loan, pk=pk, created_by=user)
    accounts = Account.objects.filter(created_by=user, is_active=True).order_by('name')

    if request.method == 'GET':
        return render(request, 'finance/loan_form.html', {
            'loan': loan,
            'accounts': accounts,
            'mode': 'edit',
        })

    loan.name = request.POST.get('name', loan.name).strip()
    try:
        loan.principal = float(request.POST.get('principal', loan.principal))
        loan.monthly_emi = float(request.POST.get('monthly_emi', loan.monthly_emi))
    except (ValueError, TypeError):
        messages.error(request, 'Invalid amount values.')
        return redirect('finance:loan_edit', pk=pk)

    account_id = request.POST.get('account_id', loan.account_id)
    loan.account = get_object_or_404(Account, pk=account_id, created_by=user)
    loan.start_date = request.POST.get('start_date', loan.start_date)
    loan.is_active = request.POST.get('is_active') == 'on'
    loan.save()

    messages.success(request, f'Loan "{loan.name}" updated.')
    return redirect('finance:loan_list')


@login_required
@require_POST
def loan_log_emi(request: HttpRequest, pk: int) -> HttpResponse:
    """
    One-tap action: log this month's EMI for a loan.
    Creates an Entry(entry_type='loan_emi') with the loan's monthly_emi amount.
    """
    user = request.user
    loan = get_object_or_404(Loan, pk=pk, created_by=user)

    emi_date = request.POST.get('date', date.today().isoformat())
    note = request.POST.get('note', f'EMI — {loan.name}')

    Entry.objects.create(
        account=loan.account,
        entry_type='loan_emi',
        amount=loan.monthly_emi,
        date=emi_date,
        category=None,
        note=note[:255],
        linked_loan=loan,
        created_by=user,
    )
    messages.success(request, f'EMI of ₹{loan.monthly_emi} logged for {loan.name}.')
    return redirect('finance:loan_list')


# ============================================================================
# Investment Views
# ============================================================================

@login_required
def investment_list(request: HttpRequest) -> HttpResponse:
    """List all investments for the current user."""
    investments = (
        Investment.objects
        .filter(created_by=request.user)
        .select_related('account')
        .order_by('name')
    )

    investment_data = []
    for inv in investments:
        contribution_count = Entry.objects.filter(
            created_by=request.user,
            linked_investment=inv,
            entry_type='investment_contribution'
        ).count()
        investment_data.append({'investment': inv, 'contribution_count': contribution_count})

    return render(request, 'finance/investment_list.html', {'investment_data': investment_data})


@login_required
def investment_create(request: HttpRequest) -> HttpResponse:
    """Create a new investment."""
    user = request.user
    accounts = Account.objects.filter(created_by=user, is_active=True).order_by('name')

    if request.method == 'GET':
        return render(request, 'finance/investment_form.html', {
            'accounts': accounts,
            'mode': 'create',
            'today': date.today().isoformat(),
            'form_data': {'name': '', 'monthly_amount': '', 'account_id': '', 'start_date': ''},
        })

    name = request.POST.get('name', '').strip()
    amount_str = request.POST.get('monthly_amount', '').strip()
    account_id = request.POST.get('account_id', '')
    start_date = request.POST.get('start_date', '')

    errors = []
    if not name:
        errors.append('Investment name is required.')
    try:
        monthly_amount = float(amount_str)
    except (ValueError, TypeError):
        monthly_amount = None
        errors.append('Invalid monthly amount.')
    if not account_id:
        errors.append('Please select an account.')

    if errors:
        for err in errors:
            messages.error(request, err)
        return render(request, 'finance/investment_form.html', {
            'accounts': accounts,
            'mode': 'create',
            'form_data': request.POST,
            'today': date.today().isoformat(),
        })

    account = get_object_or_404(Account, pk=account_id, created_by=user)
    Investment.objects.create(
        name=name,
        monthly_amount=monthly_amount,
        account=account,
        start_date=start_date or date.today(),
        is_active=True,
        created_by=user,
    )
    messages.success(request, f'Investment "{name}" created.')
    return redirect('finance:investment_list')


@login_required
def investment_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit an existing investment."""
    user = request.user
    investment = get_object_or_404(Investment, pk=pk, created_by=user)
    accounts = Account.objects.filter(created_by=user, is_active=True).order_by('name')

    if request.method == 'GET':
        return render(request, 'finance/investment_form.html', {
            'investment': investment,
            'accounts': accounts,
            'mode': 'edit',
        })

    investment.name = request.POST.get('name', investment.name).strip()
    try:
        investment.monthly_amount = float(request.POST.get('monthly_amount', investment.monthly_amount))
    except (ValueError, TypeError):
        messages.error(request, 'Invalid amount.')
        return redirect('finance:investment_edit', pk=pk)

    account_id = request.POST.get('account_id', investment.account_id)
    investment.account = get_object_or_404(Account, pk=account_id, created_by=user)
    investment.start_date = request.POST.get('start_date', investment.start_date)
    investment.is_active = request.POST.get('is_active') == 'on'
    investment.save()

    messages.success(request, f'Investment "{investment.name}" updated.')
    return redirect('finance:investment_list')


@login_required
@require_POST
def investment_log_contribution(request: HttpRequest, pk: int) -> HttpResponse:
    """
    One-tap action: log this month's contribution for an investment.
    Creates Entry(entry_type='investment_contribution').
    """
    user = request.user
    investment = get_object_or_404(Investment, pk=pk, created_by=user)

    contrib_date = request.POST.get('date', date.today().isoformat())
    note = request.POST.get('note', f'SIP — {investment.name}')

    Entry.objects.create(
        account=investment.account,
        entry_type='investment_contribution',
        amount=investment.monthly_amount,
        date=contrib_date,
        category=None,
        note=note[:255],
        linked_investment=investment,
        created_by=user,
    )
    messages.success(request, f'Contribution of ₹{investment.monthly_amount} logged for {investment.name}.')
    return redirect('finance:investment_list')
