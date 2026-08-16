"""
Dashboard view — Finance-first rebuild (Phase 1–6).

Serves the root /dashboard/ — shows this month's financials,
active loans/investments overdue for logging, top expense categories,
active split plans, and ledger summary.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from accounts.models import Entry, SplitPlan, LedgerEntry, Loan, Investment, Category


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """
    Main dashboard:
    - This month's total expense / income / net savings
    - Top 5 expense categories this month
    - Loans/Investments with no entry logged THIS month (action items)
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

    # ── 2. Top 5 expense categories this month ──────────────────────────────
    top_categories = (
        month_entries
        .filter(entry_type='expense', category__isnull=False)
        .values('category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:5]
    )

    # ── 3. Loans with no EMI logged this month ──────────────────────────────
    active_loans = Loan.objects.filter(created_by=user, is_active=True)
    loans_needing_emi = []
    for loan in active_loans:
        has_this_month = Entry.objects.filter(
            created_by=user,
            linked_loan=loan,
            entry_type='loan_emi',
            date__gte=start_of_month,
            date__lte=today,
        ).exists()
        if not has_this_month:
            loans_needing_emi.append(loan)

    # ── 4. Investments with no contribution logged this month ───────────────
    active_investments = Investment.objects.filter(created_by=user, is_active=True)
    investments_needing_log = []
    for inv in active_investments:
        has_this_month = Entry.objects.filter(
            created_by=user,
            linked_investment=inv,
            entry_type='investment_contribution',
            date__gte=start_of_month,
            date__lte=today,
        ).exists()
        if not has_this_month:
            investments_needing_log.append(inv)

    # ── 5. Active split plans ───────────────────────────────────────────────
    active_splits_qs = SplitPlan.objects.filter(
        created_by=user
    ).order_by('-created_at')[:5]

    # Annotate monthly installment for display
    active_splits = []
    for plan in active_splits_qs:
        denom = plan.num_months or 1
        plan.monthly_installment = plan.total_amount / denom
        active_splits.append(plan)

    # ── 6. Ledger summary (open entries only) ───────────────────────────────
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
        'top_categories': top_categories,
        'loans_needing_emi': loans_needing_emi,
        'investments_needing_log': investments_needing_log,
        'active_splits': active_splits,
        'ledger_given': ledger_given,
        'ledger_taken': ledger_taken,
        'net_ledger': net_ledger,
    })
