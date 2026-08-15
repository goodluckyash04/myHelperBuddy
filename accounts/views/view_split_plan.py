"""
Split Plan views — Phase 5 of the finance-first rebuild.

Features:
- SplitPlan create: Takes total amount and N months, auto-generates N Entry(entry_type='split_installment') rows.
- SplitPlan list: Shows progress of installments (paid vs remaining).
"""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Account, Entry, SplitPlan


@login_required
def split_plan_list(request: HttpRequest) -> HttpResponse:
    """List all SplitPlans and show progress (installments completed vs total)."""
    split_plans = (
        SplitPlan.objects
        .filter(created_by=request.user)
        .select_related('account')
        .order_by('-created_at')
    )
    
    plan_data = []
    today = date.today()
    
    for plan in split_plans:
        # All generated installments for this plan
        installments = Entry.objects.filter(
            created_by=request.user,
            linked_split=plan,
            entry_type='split_installment'
        ).order_by('date')
        
        # A simple heuristic: an installment is "paid" if its date is in the past
        # (Alternatively, we could add an 'is_paid' boolean to Entry, but keeping it simple based on date)
        paid_installments = [inst for inst in installments if inst.date <= today]
        
        plan_data.append({
            'plan': plan,
            'installments': installments,
            'paid_count': len(paid_installments),
            'total_count': plan.num_months,
            'progress_percent': int((len(paid_installments) / plan.num_months) * 100) if plan.num_months else 0
        })

    return render(request, 'finance/split_plan_list.html', {'plan_data': plan_data})


@login_required
def split_plan_create(request: HttpRequest) -> HttpResponse:
    """Create a new SplitPlan and auto-generate N future installments."""
    user = request.user
    accounts = Account.objects.filter(created_by=user, is_active=True).order_by('name')

    if request.method == 'GET':
        return render(request, 'finance/split_plan_form.html', {
            'accounts': accounts,
            'today': date.today().isoformat(),
        })

    title = request.POST.get('title', '').strip()
    total_amount_str = request.POST.get('total_amount', '').strip()
    num_months_str = request.POST.get('num_months', '').strip()
    account_id = request.POST.get('account_id', '')
    start_month_str = request.POST.get('start_month', '')

    errors = []
    if not title:
        errors.append('Title is required.')
        
    try:
        total_amount = float(total_amount_str)
        if total_amount <= 0:
            errors.append('Total amount must be positive.')
    except (ValueError, TypeError):
        total_amount = None
        errors.append('Invalid total amount.')
        
    try:
        num_months = int(num_months_str)
        if num_months <= 0:
            errors.append('Number of months must be at least 1.')
    except (ValueError, TypeError):
        num_months = None
        errors.append('Invalid number of months.')
        
    if not account_id:
        errors.append('Please select an account.')

    start_month = None
    if start_month_str:
        try:
            start_month = date.fromisoformat(start_month_str)
            # Ensure start_month is the first of the month
            start_month = start_month.replace(day=1)
        except ValueError:
            errors.append('Invalid start month.')

    if errors:
        for err in errors:
            messages.error(request, err)
        return render(request, 'finance/split_plan_form.html', {
            'accounts': accounts,
            'form_data': request.POST,
            'today': date.today().isoformat(),
        })

    account = get_object_or_404(Account, pk=account_id, created_by=user)
    
    with transaction.atomic():
        plan = SplitPlan.objects.create(
            title=title,
            total_amount=total_amount,
            num_months=num_months,
            start_month=start_month or date.today().replace(day=1),
            account=account,
            created_by=user,
        )
        
        # Auto-generate N Entry rows
        # We need to compute the installment amount. Let's make it equal.
        installment_amount = round(total_amount / num_months, 2)
        
        # We might have a rounding error (e.g. 100 / 3 = 33.33 * 3 = 99.99)
        # So we adjust the last installment.
        entries_to_create = []
        current_date = plan.start_month
        
        for i in range(num_months):
            amount = installment_amount
            if i == num_months - 1:
                # Last installment takes the remainder
                amount = total_amount - (installment_amount * (num_months - 1))
                amount = round(amount, 2)
                
            entries_to_create.append(Entry(
                account=account,
                entry_type='split_installment',
                amount=amount,
                date=current_date,
                note=f"{plan.title} ({i+1}/{num_months})",
                linked_split=plan,
                created_by=user,
            ))
            
            # Increment month
            next_month = current_date.month + 1
            next_year = current_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            current_date = current_date.replace(year=next_year, month=next_month)
            
        Entry.objects.bulk_create(entries_to_create)

    messages.success(request, f'Split Plan "{title}" created with {num_months} installments.')
    return redirect('finance:split_plan_list')
