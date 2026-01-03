"""
Ledger Transaction Management Views

Handles ledger transactions for tracking receivables and payables
with counterparties (customers, vendors, etc.).

Features:
- Transaction creation with installment support
- Counterparty balance tracking (receivables vs payables)
- Transaction status management (Pending/Completed)
- Update and delete operations
- Soft delete with undo functionality
- Bulk operations support
"""

import datetime
import decimal
import json
import traceback
from typing import Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseServerError,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import LedgerTransaction
from accounts.views.view_financial_instrument import desired_date
from accounts.views.views import get_counter_parties


# ============================================================================
# Transaction Creation
# ============================================================================

@login_required
def add_ledger_transaction(request: HttpRequest) -> HttpResponse:
    """
    Create new ledger transaction(s) with optional installments.
    
    Transaction Types:
        - Receivable: Money to be received from counterparty
        - Payable: Money to be paid to counterparty
        - Received: Money already received (auto-completed)
        - Paid: Money already paid (auto-completed)
    
    Features:
        - Automatically creates multiple installments if specified
        - Auto-completes 'Received' and 'Paid' transactions
        - Validates for duplicate transactions
    
    Args:
        request: HTTP POST request with transaction details
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    try:
        # Extract form data
        transaction_type = request.POST.get('transaction_type', 'Receivable')
        transaction_date = request.POST.get('transaction_date')
        amount = decimal.Decimal(request.POST.get('amount', 0.0))
        counterparty = request.POST.get('counterparty', '').upper()
        description = request.POST.get('description', '')
        no_of_installments = int(request.POST.get('no_of_installments') or 1)
        
        # Check for duplicate transaction
        try:
            existing = LedgerTransaction.objects.get(
                transaction_type=transaction_type,
                transaction_date=transaction_date,
                amount=amount,
                counterparty=counterparty,
                description=description,
                created_by=user
            )
            if existing:
                raise ValueError(f"Duplicate {transaction_type} transaction already exists")
        except ObjectDoesNotExist:
            pass  # No duplicate, proceed with creation
        
        # Determine status based on transaction type
        is_completed = transaction_type in ('Received', 'Paid')
        status = 'Completed' if is_completed else 'Pending'
        completion_date = datetime.datetime.today() if is_completed else None
        
        # Create transaction(s)
        for index in range(no_of_installments):
            LedgerTransaction.objects.create(
                transaction_type=transaction_type,
                transaction_date=desired_date(transaction_date, index),
                amount=amount,
                status=status,
                completion_date=completion_date,
                counterparty=counterparty,
                description=description,
                created_by=user
            )
        
        installment_text = f" with {no_of_installments} installments" if no_of_installments > 1 else ""
        messages.success(
            request,
            f'{transaction_type} transaction added successfully{installment_text}'
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except ValidationError as e:
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    except ValueError as e:
        traceback.print_exc()
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        traceback.print_exc()
        return HttpResponseServerError()


# ============================================================================
# Dashboard & Listing
# ============================================================================

@login_required
def ledger_transaction_details(request: HttpRequest) -> HttpResponse:
    """
    Display counterparty balances and summary.
    
    Calculates for each counterparty:
        - Total receivables (money to receive)
        - Total payables (money to pay)
        - Net balance (receivables - payables)
    
    Formula:
        - Receivables = Receivable (Pending) + Receivable (Completed as Received)
        - Payables = Payable (Pending) + Payable (Completed as Paid)
    
    Args:
        request: HTTP GET request
        
    Returns:
        HttpResponse: Rendered counterparty summary page
    """
    user = request.user
    
    def get_paid_and_received_sums(transaction_type: str):
        """
        Calculate sum of completed transactions.
        
        Args:
            transaction_type: Either "Paid" or "Received"
            
        Returns:
            Aggregation expression for sum
        """
        if transaction_type == "Paid":
            txn_types = ["Payable", "Paid"]
        else:
            txn_types = ["Receivable", "Received"]
        
        return Coalesce(
            Sum('amount', filter=Q(
                (Q(transaction_type=txn_types[0], status='Completed') |
                 Q(transaction_type=txn_types[1])) &
                Q(created_by=user, is_deleted=False)
            )),
            Value(0, output_field=DecimalField())
        )
    
    def get_sum(transaction_type: str):
        """Get total sum for a transaction type."""
        return Coalesce(
            Sum('amount', filter=Q(
                transaction_type=transaction_type,
                created_by=user,
                is_deleted=False
            )),
            Value(0, output_field=DecimalField())
        )
    
    try:
        # Calculate balances per counterparty
        receivables_payables = LedgerTransaction.objects.filter(
            created_by=user
        ).values('counterparty').annotate(
            total_receivable=get_sum("Receivable") - get_paid_and_received_sums("Received"),
            total_payable=get_sum("Payable") - get_paid_and_received_sums("Paid")
        ).annotate(
            total=ExpressionWrapper(
                F('total_receivable') - F('total_payable'),
                output_field=DecimalField()
            )
        )
        
        counterparties = get_counter_parties(user)
        
        context = {
            'user': user,
            'receivables_payables': receivables_payables,
            'counterparties': counterparties
        }
        
        return render(request, 'ledger_transaction/counterparty.html', context)
        
    except Exception as e:
        traceback.print_exc()
        messages.error(request, "An error occurred while loading balances")
        return render(request, "ledger_transaction/counterparty.html", {"user": user})


@login_required
def ledger_transaction(request: HttpRequest, id: str) -> HttpResponse:
    """
    List ledger transactions with filtering.
    
    Filter Options:
        - "all": All transactions
        - "completed": Completed transactions only
        - "pending": Pending transactions only
        - {counterparty_name}: Transactions for specific counterparty
    
    Args:
        request: HTTP GET request
        id: Filter identifier (all/completed/pending/counterparty_name)
        
    Returns:
        HttpResponse: Rendered transaction list page
    """
    user = request.user
    filter_type = id
    
    # Build query based on filter
    if filter_type == "all":
        transactions = LedgerTransaction.objects.filter(
            created_by=user,
            is_deleted=False
        ).select_related('created_by').order_by('-transaction_date')
    
    elif filter_type == "completed":
        transactions = LedgerTransaction.objects.filter(
            created_by=user,
            is_deleted=False,
            status="Completed"
        ).select_related('created_by').order_by('-transaction_date')
    
    elif filter_type == "pending":
        transactions = LedgerTransaction.objects.filter(
            created_by=user,
            is_deleted=False,
            status="Pending"
        ).select_related('created_by').order_by('-transaction_date')
    
    else:
        # Filter by counterparty name (case-insensitive)
        counterparty = filter_type
        transactions = LedgerTransaction.objects.filter(
            created_by=user,
            is_deleted=False,
            counterparty__iexact=counterparty
        ).select_related('created_by').order_by('-transaction_date')
    
    context = {
        "user": user,
        'transaction_data': transactions,
        'current_filter': filter_type
    }
    
    return render(request, 'ledger_transaction/ledgerTransaction.html', context)


# ============================================================================
# Status Management
# ============================================================================

@login_required
def update_ledger_transaction_status(
    request: HttpRequest,
    id: Optional[int] = None
) -> HttpResponse:
    """
    Toggle transaction status between Pending and Completed.
    
    Supports:
        - Single transaction update (GET with id)
        - Bulk update (POST with record_ids)
    
    Only works for Receivable/Payable transactions.
    Received/Paid transactions cannot have status changed.
    
    Args:
        request: HTTP request (GET or POST)
        id: Transaction ID for single update (optional)
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    try:
        # Get list of transactions to update
        if request.method == "GET":
            transaction_list = [id]
        else:
            transaction_list = request.POST.getlist('record_ids', [])
        
        updated_count = 0
        skipped_count = 0
        
        for txn_id in transaction_list:
            entry = LedgerTransaction.objects.get(id=txn_id, created_by=user)
            
            # Only update Receivable/Payable transactions
            if entry.transaction_type in ("Receivable", "Payable"):
                current_status = entry.status
                entry.status = "Completed" if current_status == "Pending" else "Pending"
                entry.completion_date = (
                    datetime.datetime.today() if current_status == "Pending" else None
                )
                entry.save()
                updated_count += 1
            else:
                skipped_count += 1
        
        # Show appropriate message
        if updated_count > 0:
            messages.success(
                request,
                f'{updated_count} transaction(s) status updated'
            )
        if skipped_count > 0 and len(transaction_list) == 1:
            messages.info(
                request,
                f'Cannot update status of {entry.transaction_type} transaction'
            )
        
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        traceback.print_exc()
        messages.error(request, "An error occurred while updating status")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# ============================================================================
# Update & Edit
# ============================================================================

@login_required
def update_ledger_transaction(request: HttpRequest, id: int) -> HttpResponse:
    """
    Update ledger transaction details.
    
    GET: Returns transaction details as JSON
    POST: Updates transaction fields
    
    Args:
        request: HTTP request (GET or POST)
        id: Transaction ID
        
    Returns:
        HttpResponse: JSON response (GET) or redirect (POST)
    """
    user = request.user
    
    try:
        entry = get_object_or_404(LedgerTransaction, id=id, created_by=user)
        
        # GET: Return transaction details
        if request.method == "GET":
            return JsonResponse({
                'id': entry.id,
                'transaction_type': entry.transaction_type,
                'transaction_date': entry.transaction_date,
                'amount': entry.amount,
                'description': entry.description
            })
        
        # POST: Update transaction
        entry.transaction_type = request.POST['transaction_type']
        entry.transaction_date = request.POST['transaction_date']
        entry.amount = decimal.Decimal(request.POST['amount'])
        entry.description = request.POST['description']
        entry.save()
        
        messages.success(request, 'Transaction updated successfully')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        traceback.print_exc()
        return HttpResponseServerError()


@login_required
def update_counterparty_name(request: HttpRequest, id: str) -> HttpResponse:
    """
    Update counterparty name for all transactions.
    
    Changes the counterparty name for all transactions
    with the specified counterparty.
    
    Args:
        request: HTTP POST request with JSON body containing newCounterparty
        id: Current counterparty name
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    try:
        # Parse JSON data
        data = json.loads(request.body)
        new_counterparty = data.get('newCounterparty', '').strip()
        
        if not new_counterparty:
            messages.error(request, 'Counterparty name is required')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
        # Update all transactions with this counterparty
        transactions = LedgerTransaction.objects.filter(
            counterparty=id,
            created_by=user
        )
        
        update_count = 0
        for entry in transactions:
            entry.counterparty = new_counterparty.upper()
            entry.save()
            update_count += 1
        
        messages.success(
            request,
            f'Counterparty updated for {update_count} transaction(s)'
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except json.JSONDecodeError:
        messages.error(request, 'Invalid JSON data')
        return HttpResponseServerError()
    except Exception as e:
        messages.error(request, 'An unexpected error occurred')
        traceback.print_exc()
        return HttpResponseServerError()


# ============================================================================
# Deletion & Undo
# ============================================================================

@login_required
def delete_ledger_transaction(request: HttpRequest, id: int) -> HttpResponse:
    """
    Soft delete a ledger transaction.
    
    Args:
        request: HTTP request
        id: Transaction ID
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    try:
        transaction = LedgerTransaction.objects.get(
            created_by=user,
            id=id,
            is_deleted=False
        )
        transaction.is_deleted = True
        transaction.deleted_at = datetime.datetime.today()
        transaction.save()
        
        messages.success(request, "Transaction deleted successfully")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        traceback.print_exc()
        return HttpResponseServerError()


@login_required
def fetch_deleted_ledger_transaction(request: HttpRequest) -> HttpResponse:
    """
    Display all deleted ledger transactions.
    
    Args:
        request: HTTP GET request
        
    Returns:
        HttpResponse: Rendered deleted entries page
    """
    user = request.user
    
    try:
        deleted_transactions = LedgerTransaction.objects.filter(
            created_by=user,
            is_deleted=True
        ).order_by('-deleted_at')
        
        context = {
            "data": deleted_transactions,
            "user": user
        }
        
        return render(request, 'ledger_transaction/deletedLedgerEntries.html', context)
        
    except Exception as e:
        traceback.print_exc()
        messages.error(request, "An error occurred while loading deleted transactions")
        return redirect('utilities')


@login_required
def undo_ledger_transaction(
    request: HttpRequest,
    id: Optional[int] = None
) -> HttpResponse:
    """
    Restore deleted ledger transaction(s).
    
    Supports:
        - Single transaction restore (GET with id)
        - Bulk restore (POST with record_ids)
    
    Args:
        request: HTTP request (GET or POST)
        id: Transaction ID for single restore (optional)
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    try:
        # Get list of transactions to restore
        if request.method == "GET":
            undo_list = [id]
        else:
            undo_list = request.POST.getlist('record_ids', [])
        
        restored_count = 0
        for txn_id in undo_list:
            entry = LedgerTransaction.objects.get(
                id=txn_id,
                created_by=user,
                is_deleted=True
            )
            if entry:
                entry.is_deleted = False
                entry.deleted_at = None
                entry.save()
                restored_count += 1
        
        messages.success(request, f'{restored_count} transaction(s) restored')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, "An error occurred while restoring transactions")
        traceback.print_exc()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
