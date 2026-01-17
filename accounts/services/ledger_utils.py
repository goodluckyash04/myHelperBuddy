"""
Ledger Management Utility Functions

Provides helper functions for:
- Installment generation
- Balance calculations
- Overdue detection
- Aging analysis
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db.models import Q, Sum
from django.utils import timezone

from accounts.models import LedgerTransaction, PaymentRecord


# ============================================================================
# Installment Generation
# ============================================================================

def create_installment_transactions(
    user,
    base_amount: Decimal,
    num_installments: int,
    frequency: str,  # 'MONTHLY', 'WEEKLY', 'CUSTOM'
    start_date: date,
    custom_days: Optional[int] = None,
    **common_fields
) -> Tuple[LedgerTransaction, List[LedgerTransaction]]:
    """
    Create parent transaction and multiple installment transactions.
    
    Args:
        user: User creating the transactions
        base_amount: Total amount to be divided into installments
        num_installments: Number of installments to create
        frequency: Frequency of installments ('MONTHLY', 'WEEKLY', 'CUSTOM')
        start_date: Start date for first installment
        custom_days: Custom interval in days (required if frequency='CUSTOM')
        **common_fields: Other fields to apply to all transactions
        
    Returns:
        Tuple of (parent_transaction, list_of_installments)
    """
    installment_amount = base_amount / num_installments
    
    # Create parent transaction (summary record)
    parent = LedgerTransaction.objects.create(
        created_by=user,
        amount=base_amount,
        total_installments=num_installments,
        transaction_date=start_date,
        **common_fields
    )
    
    # Create child installments
    installments = []
    for i in range(num_installments):
        due_date = calculate_due_date(start_date, i, frequency, custom_days)
        
        installment = LedgerTransaction.objects.create(
            created_by=user,
            parent_transaction=parent,
            installment_number=i + 1,
            total_installments=num_installments,
            amount=installment_amount,
            transaction_date=start_date,
            due_date=due_date,
            **common_fields
        )
        installments.append(installment)
    
    return parent, installments


def calculate_due_date(
    start_date: date, 
    installment_index: int, 
    frequency: str,
    custom_days: Optional[int] = None
) -> date:
    """
    Calculate due date for an installment.
    
    Args:
        start_date: Base start date
        installment_index: Index of installment (0-based)
        frequency: 'MONTHLY', 'WEEKLY', or 'CUSTOM'
        custom_days: Custom interval in days
        
    Returns:
        Due date for the installment
    """
    if frequency == 'MONTHLY':
        # Add months (approximate by adding 30 days per month)
        months = installment_index
        return start_date + timedelta(days=30 * months)
    
    elif frequency == 'WEEKLY':
        weeks = installment_index
        return start_date + timedelta(weeks=weeks)
    
    elif frequency == 'CUSTOM':
        if custom_days is None:
            raise ValueError("custom_days required for CUSTOM frequency")
        return start_date + timedelta(days=custom_days * installment_index)
    
    else:
        raise ValueError(f"Invalid frequency: {frequency}")


# ============================================================================
# Balance Calculations
# ============================================================================

def calculate_counterparty_balance(counterparty: str, user) -> Dict:
    """
    Calculate net balance with a counterparty.
    
    Args:
        counterparty: Name of the counterparty
        user: User to calculate balance for
        
    Returns:
        Dictionary with balance details:
        {
            'total_receivable': Decimal,
            'total_payable': Decimal,
            'net_balance': Decimal,
            'status': 'OWE_YOU' | 'YOU_OWE' | 'SETTLED',
            'overdue_receivable': Decimal,
            'overdue_payable': Decimal
        }
    """
    today = timezone.now().date()
    
    # Get all active transactions for this counterparty
    transactions = LedgerTransaction.objects.filter(
        created_by=user,
        counterparty__iexact=counterparty,
        is_deleted=False
    )
    
    # Calculate receivables (what you are owed)
    receivable_pending = transactions.filter(
        transaction_type='RECEIVABLE',
        status__in=['PENDING', 'PARTIAL']
    ).aggregate(
        total=Sum('remaining_amount')
    )['total'] or Decimal('0')
    
    # Calculate payables (what you owe)
    payable_pending = transactions.filter(
        transaction_type='PAYABLE',
        status__in=['PENDING', 'PARTIAL']
    ).aggregate(
        total=Sum('remaining_amount')
    )['total'] or Decimal('0')
    
    # Calculate overdue amounts
    overdue_receivable = transactions.filter(
        transaction_type='RECEIVABLE',
        status__in=['PENDING', 'PARTIAL'],
        due_date__lt=today
    ).aggregate(
        total=Sum('remaining_amount')
    )['total'] or Decimal('0')
    
    overdue_payable = transactions.filter(
        transaction_type='PAYABLE',
        status__in=['PENDING', 'PARTIAL'],
        due_date__lt=today
    ).aggregate(
        total=Sum('remaining_amount')
    )['total'] or Decimal('0')
    
    # Calculate net balance
    net_balance = receivable_pending - payable_pending
    
    # Determine status
    if net_balance > 0:
        status = 'OWE_YOU'
    elif net_balance < 0:
        status = 'YOU_OWE'
    else:
        status = 'SETTLED'
    
    return {
        'total_receivable': receivable_pending,
        'total_payable': payable_pending,
        'net_balance': net_balance,
        'status': status,
        'overdue_receivable': overdue_receivable,
        'overdue_payable': overdue_payable
    }


def get_all_counterparties_summary(user) -> List[Dict]:
    """
    Get balance summary for all counterparties.
    
    Args:
        user: User to get summary for
        
    Returns:
        List of dictionaries with counterparty summaries
    """
    # Get all unique counterparties
    counterparties = LedgerTransaction.objects.filter(
        created_by=user,
        is_deleted=False
    ).values_list('counterparty', flat=True).distinct()
    
    summaries = []
    for counterparty in counterparties:
        balance = calculate_counterparty_balance(counterparty, user)
        summaries.append({
            'counterparty': counterparty,
            **balance
        })
    
    # Sort by absolute net balance (largest first)
    summaries.sort(key=lambda x: abs(x['net_balance']), reverse=True)
    
    return summaries


# ============================================================================
# Payment Recording
# ============================================================================

def record_payment(
    transaction_id: int,
    user,
    payment_date: date,
    amount_paid: Decimal,
    payment_method: str,
    reference_number: str = "",
    notes: str = "",
    receipt_file=None
) -> PaymentRecord:
    """
    Record a payment against a ledger transaction.
    
    Args:
        transaction_id: ID of the ledger transaction
        user: User recording the payment
        payment_date: Date of payment
        amount_paid: Amount being paid
        payment_method: Method of payment
        reference_number: Optional reference number
        notes: Optional payment notes
        receipt_file: Optional receipt file
        
    Returns:
        Created PaymentRecord instance
        
    Raises:
        ValueError: If payment amount exceeds remaining amount
    """
    transaction = LedgerTransaction.objects.get(
        id=transaction_id,
        created_by=user
    )
    
    # Validate payment amount
    if amount_paid > transaction.remaining_amount:
        raise ValueError(
            f"Payment amount ₹{amount_paid} exceeds remaining amount "
            f"₹{transaction.remaining_amount}"
        )
    
    # Create payment record
    payment = PaymentRecord.objects.create(
        ledger_transaction=transaction,
        created_by=user,
        payment_date=payment_date,
        amount_paid=amount_paid,
        payment_method=payment_method,
        reference_number=reference_number,
        notes=notes,
        receipt_file=receipt_file
    )
    
    # The PaymentRecord.save() method will automatically update the parent transaction
    
    return payment


# ============================================================================
# Overdue Detection & Aging
# ============================================================================

def get_overdue_transactions(user, transaction_type: Optional[str] = None) -> List[LedgerTransaction]:
    """
    Get all overdue transactions for a user.
    
    Args:
        user: User to get overdue transactions for
        transaction_type: Optional filter by type ('RECEIVABLE' or 'PAYABLE')
        
    Returns:
        List of overdue transactions
    """
    today = timezone.now().date()
    
    query = LedgerTransaction.objects.filter(
        created_by=user,
        is_deleted=False,
        status__in=['PENDING', 'PARTIAL'],
        due_date__lt=today
    ).select_related('created_by')
    
    if transaction_type:
        query = query.filter(transaction_type=transaction_type)
    
    return list(query.order_by('due_date'))


def get_aging_report(user, counterparty: Optional[str] = None) -> Dict:
    """
    Get aging analysis of receivables and payables.
    
    Args:
        user: User to generate report for
        counterparty: Optional filter by counterparty
        
    Returns:
        Dictionary with aging buckets:
        {
            'receivables': {
                'current': Decimal,
                '0_30': Decimal,
                '31_60': Decimal,
                '61_90': Decimal,
                '90_plus': Decimal
            },
            'payables': {...}
        }
    """
    today = timezone.now().date()
    
    def calculate_aging(transaction_type: str) -> Dict:
        query = LedgerTransaction.objects.filter(
            created_by=user,
            is_deleted=False,
            transaction_type=transaction_type,
            status__in=['PENDING', 'PARTIAL']
        )
        
        if counterparty:
            query = query.filter(counterparty__iexact=counterparty)
        
        buckets = {
            'current': Decimal('0'),
            '0_30': Decimal('0'),
            '31_60': Decimal('0'),
            '61_90': Decimal('0'),
            '90_plus': Decimal('0')
        }
        
        for txn in query:
            if not txn.due_date or txn.due_date >= today:
                buckets['current'] += txn.remaining_amount
            else:
                days_overdue = (today - txn.due_date).days
                if days_overdue <= 30:
                    buckets['0_30'] += txn.remaining_amount
                elif days_overdue <= 60:
                    buckets['31_60'] += txn.remaining_amount
                elif days_overdue <= 90:
                    buckets['61_90'] += txn.remaining_amount
                else:
                    buckets['90_plus'] += txn.remaining_amount
        
        return buckets
    
    return {
        'receivables': calculate_aging('RECEIVABLE'),
        'payables': calculate_aging('PAYABLE')
    }


# ============================================================================
# Cash Flow Projection
# ============================================================================

def get_cash_flow_projection(user, days_ahead: int = 30) -> List[Dict]:
    """
    Project upcoming cash flow based on due dates.
    
    Args:
        user: User to project for
        days_ahead: Number of days to project ahead
        
    Returns:
        List of daily projections:
        [{
            'date': date,
            'receivable': Decimal,
            'payable': Decimal,
            'net': Decimal
        }]
    """
    today = timezone.now().date()
    end_date = today + timedelta(days=days_ahead)
    
    # Get all pending transactions with due dates in range
    transactions = LedgerTransaction.objects.filter(
        created_by=user,
        is_deleted=False,
        status__in=['PENDING', 'PARTIAL'],
        due_date__range=[today, end_date]
    ).order_by('due_date')
    
    # Group by date
    projection = {}
    for txn in transactions:
        if txn.due_date not in projection:
            projection[txn.due_date] = {
                'date': txn.due_date,
                'receivable': Decimal('0'),
                'payable': Decimal('0'),
                'net': Decimal('0')
            }
        
        if txn.transaction_type == 'RECEIVABLE':
            projection[txn.due_date]['receivable'] += txn.remaining_amount
        elif txn.transaction_type == 'PAYABLE':
            projection[txn.due_date]['payable'] += txn.remaining_amount
        
        projection[txn.due_date]['net'] = (
            projection[txn.due_date]['receivable'] - 
            projection[txn.due_date]['payable']
        )
    
    # Convert to sorted list
    return sorted(projection.values(), key=lambda x: x['date'])
