"""
Dashboard view — Phase 9 of the finance-first rebuild.
"""

from datetime import date
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from accounts.models import Entry, SplitPlan, LedgerContact, LedgerEntry


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """
    Main dashboard displaying:
    - This month's total expense/income
    - Upcoming split installments
    - Ledger summary (net owed to/by you)
    """
    user = request.user
    today = date.today()
    start_of_month = today.replace(day=1)
    
    # 1. This month's total expense / income
    month_entries = Entry.objects.filter(
        created_by=user,
        date__gte=start_of_month,
        date__lte=today,
    )
    
    # We include both standard expenses and split/loan/investment in expense totals if they are money out.
    # Actually, loan_emi, investment_contribution, split_installment are all expenses.
    expense_types = ['expense', 'loan_emi', 'investment_contribution', 'split_installment']
    
    totals = month_entries.aggregate(
        income=Sum('amount', filter=Q(entry_type='income')),
        expense=Sum('amount', filter=Q(entry_type__in=expense_types))
    )
    
    total_income = totals['income'] or 0
    total_expense = totals['expense'] or 0
    
    # 2. Upcoming Split Installments
    # We can check which split plans are active and haven't finished.
    # We just fetch active split plans for simplicity.
    active_splits = SplitPlan.objects.filter(
        created_by=user
    ).order_by('-created_at')[:5]
    
    # 3. Ledger Summary
    # Calculate global net given / net taken
    ledger_totals = LedgerEntry.objects.filter(
        created_by=user,
        status='open'
    ).aggregate(
        given=Sum('amount', filter=Q(entry_type='given')),
        taken=Sum('amount', filter=Q(entry_type='taken'))
    )
    
    total_given = ledger_totals['given'] or 0
    total_taken = ledger_totals['taken'] or 0
    net_ledger = total_taken - total_given
    
    return render(request, 'finance/dashboard.html', {
        'total_income': total_income,
        'total_expense': total_expense,
        'net_savings': total_income - total_expense,
        'active_splits': active_splits,
        'ledger_given': total_given,
        'ledger_taken': total_taken,
        'net_ledger': net_ledger,
    })
