"""
Dashboard view — Finance-first rebuild (Phase 1–3).

Serves the root /dashboard/ — shows this month's financials,
active split plans, and ledger summary. No tasks, no reminders.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from accounts.models import Entry, SplitPlan, LedgerEntry


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """
    Main dashboard:
    - This month's total expense / income / net savings
    - Active split plans (most recent 5)
    - Ledger summary (net open balance)
    """
    user = request.user
    today = date.today()
    start_of_month = today.replace(day=1)

    # ── 1. This month's financials ──────────────────────────────────────────
    expense_types = ['expense', 'loan_emi', 'investment_contribution', 'split_installment']
    month_entries = Entry.objects.filter(
        created_by=user,
        date__gte=start_of_month,
        date__lte=today,
    )
    totals = month_entries.aggregate(
        income=Sum('amount', filter=Q(entry_type='income')),
        expense=Sum('amount', filter=Q(entry_type__in=expense_types)),
    )
    total_income = totals['income'] or Decimal('0')
    total_expense = totals['expense'] or Decimal('0')

    # ── 2. Active split plans ───────────────────────────────────────────────
    active_splits_qs = SplitPlan.objects.filter(
        created_by=user
    ).order_by('-created_at')[:5]

    # Annotate monthly installment for display
    active_splits = []
    for plan in active_splits_qs:
        denom = plan.num_months or 1
        plan.monthly_installment = plan.total_amount / denom
        active_splits.append(plan)

    # ── 3. Ledger summary (open entries only) ───────────────────────────────
    ledger_totals = LedgerEntry.objects.filter(
        created_by=user,
        status='open',
    ).aggregate(
        given=Sum('amount', filter=Q(entry_type='given')),
        taken=Sum('amount', filter=Q(entry_type='taken')),
    )
    ledger_given = ledger_totals['given'] or Decimal('0')
    ledger_taken = ledger_totals['taken'] or Decimal('0')
    # positive = you owe them; negative = they owe you
    net_ledger = ledger_taken - ledger_given

    return render(request, 'dashboard.html', {
        'today': today,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_savings': total_income - total_expense,
        'active_splits': active_splits,
        'ledger_given': ledger_given,
        'ledger_taken': ledger_taken,
        'net_ledger': net_ledger,
    })
