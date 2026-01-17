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
    
    Supports:
        - RECEIVABLE: Money to be received from counterparty
        - PAYABLE: Money to be paid to counterparty
        - RECEIVED: Money already received (auto-completed)
        - PAID: Money already paid (auto-completed)
    
    Features:
        - Installment creation with multiple frequency options
        - File attachments for invoices/receipts
        - Tags for categorization
        - Payment method tracking
        - Due date management
        - Reference and invoice numbers
    
    Args:
        request: HTTP POST request with transaction details
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    from accounts.services.ledger_utils import create_installment_transactions
    
    user = request.user
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    try:
        # Extract core form data
        transaction_type = request.POST.get('transaction_type', 'RECEIVABLE').upper()
        transaction_date_str = request.POST.get('transaction_date')
        amount = decimal.Decimal(request.POST.get('amount', 0.0))
        counterparty = request.POST.get('counterparty', '').upper()
        description = request.POST.get('description', '')
        
        # Parse transaction date
        from datetime import datetime
        if transaction_date_str:
            transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
        else:
            transaction_date = datetime.today().date()
        
        # Extract additional fields
        counterparty_contact = request.POST.get('counterparty_contact', '')
        counterparty_email = request.POST.get('counterparty_email', '')
        reference_number = request.POST.get('reference_number', '')
        invoice_number = request.POST.get('invoice_number', '')
        payment_method = request.POST.get('payment_method', '')
        due_date_str = request.POST.get('due_date', '')
        notes = request.POST.get('notes', '')
        
        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Handle tags (comma-separated)
        tags_str = request.POST.get('tags', '')
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        
        # Handle file attachment
        attachment = request.FILES.get('attachment')
        
        # Installment configuration
        enable_installments = request.POST.get('enable_installments') == 'on'
        num_installments = int(request.POST.get('no_of_installments') or 1)
        installment_frequency = request.POST.get('installment_frequency', 'MONTHLY')
        custom_days = request.POST.get('custom_days')
        
        # Validate transaction type
        valid_types = ['RECEIVABLE', 'RECEIVED', 'PAYABLE', 'PAID']
        if transaction_type not in valid_types:
            raise ValueError(f"Invalid transaction type: {transaction_type}")
        
        # Determine status based on transaction type
        if transaction_type in ['RECEIVED', 'PAID']:
            status = 'COMPLETED'
            completion_date = datetime.today().date()
            paid_amount = amount  # Fully paid
        else:
            status = 'PENDING'
            completion_date = None
            paid_amount = decimal.Decimal('0')
        
        # Common fields for all transactions
        common_fields = {
            'counterparty': counterparty,
            'counterparty_contact': counterparty_contact,
            'counterparty_email': counterparty_email,
            'description': description,
            'reference_number': reference_number,
            'invoice_number': invoice_number,
            'payment_method': payment_method if payment_method else None,
            'notes': notes,
            'tags': tags,
            'status': status,
            'completion_date': completion_date,
            'paid_amount': paid_amount,
            'attachment': attachment,
            'transaction_type': transaction_type,
        }
        
        # Create transaction(s)
        if enable_installments and num_installments > 1:
            # Create installments using utility function
            parent, installments = create_installment_transactions(
                user=user,
                base_amount=amount,
                num_installments=num_installments,
                frequency=installment_frequency,
                start_date=transaction_date,
                custom_days=int(custom_days) if custom_days else None,
                due_date=due_date,
                **common_fields
            )
            
            messages.success(
                request,
                f'{transaction_type} transaction created with {num_installments} installments'
            )
        else:
            # Create single transaction
            LedgerTransaction.objects.create(
                created_by=user,
                transaction_date=transaction_date,
                amount=amount,
                due_date=due_date,
                **common_fields
            )
            
            messages.success(
                request,
                f'{transaction_type} transaction added successfully'
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
        messages.error(request, f"An unexpected error occurred: {str(e)}")
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
        - Receivables = RECEIVABLE (Pending) + RECEIVABLE (Completed as RECEIVED)
        - Payables = PAYABLE (Pending) + PAYABLE (Completed as PAID)
    
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
            transaction_type: Either "PAID" or "RECEIVED"
            
        Returns:
            Aggregation expression for sum
        """
        if transaction_type == "PAID":
            txn_types = ["PAYABLE", "PAID"]
        else:
            txn_types = ["RECEIVABLE", "RECEIVED"]
        
        return Coalesce(
            Sum('amount', filter=Q(
                (Q(transaction_type=txn_types[0], status='COMPLETED') |
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
            total_receivable=get_sum("RECEIVABLE") - get_paid_and_received_sums("RECEIVED"),
            total_payable=get_sum("PAYABLE") - get_paid_and_received_sums("PAID")
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
def get_ledger_transactions_by_party(
    request: HttpRequest,
    id: str
) -> HttpResponse:
    """
    Display ledger transactions filtered by counterparty or other criteria.
    Supports comprehensive filtering and pagination.
    
    URL Parameters:
        - status: Filter by status (ALL, PENDING, PARTIAL, COMPLETED, CANCELLED)
        - type: Filter by transaction type (ALL, RECEIVABLE, PAYABLE, RECEIVED, PAID)
        - search: Search in counterparty or description
        - start_date: Filter from this date (YYYY-MM-DD)
        - end_date: Filter to this date (YYYY-MM-DD)
        - min_amount: Minimum transaction amount
        - max_amount: Maximum transaction amount
        - overdue: Show only overdue transactions (true/false)
        - tags: Filter by tags (comma-separated)
        - per_page: Results per page (10, 25, 50, 100)
        - page: Page number
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Q
    from datetime import datetime, date
    from decimal import Decimal, InvalidOperation
    
    user = request.user
    filter_type = id
    counterparty = id if id not in ['all', 'completed', 'pending'] else None
    
    # Get filter parameters from URL
    status_filter = request.GET.get('status', 'ALL')
    type_filter = request.GET.get('type', 'ALL')
    search_query = request.GET.get('search', '').strip()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    min_amount_str = request.GET.get('min_amount', '').strip()
    max_amount_str = request.GET.get('max_amount', '').strip()
    overdue_only = request.GET.get('overdue', '').lower() == 'true'
    tags_filter = request.GET.get('tags', '').strip()
    per_page = int(request.GET.get('per_page', 25))
    page_number = request.GET.get('page', 1)
    
    # Ensure per_page is within allowed values
    if per_page not in [10, 25, 50, 100]:
        per_page = 25
    
    # Start with base query
    transactions = LedgerTransaction.objects.filter(
        created_by=user,
        is_deleted=False
    ).select_related('created_by')
    
    # Apply counterparty filter if applicable
    if filter_type not in ["all", "completed", "pending"]:
        transactions = transactions.filter(counterparty__iexact=counterparty)
    
    # Apply status filter
    if status_filter != 'ALL':
        if filter_type == "completed" or status_filter == 'COMPLETED':
            transactions = transactions.filter(status='COMPLETED')
        elif filter_type == "pending" or status_filter == 'PENDING':
            transactions = transactions.filter(status='PENDING')
        elif status_filter in ['PARTIAL', 'CANCELLED']:
            transactions = transactions.filter(status=status_filter)
    
    # Apply transaction type filter
    if type_filter != 'ALL':
        transactions = transactions.filter(transaction_type=type_filter)
    
    # Apply search filter (counterparty or description)
    if search_query:
        transactions = transactions.filter(
            Q(counterparty__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(reference_number__icontains=search_query) |
            Q(invoice_number__icontains=search_query)
        )
    
    # Apply date range filters
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            transactions = transactions.filter(transaction_date__gte=start_date)
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            transactions = transactions.filter(transaction_date__lte=end_date)
        except ValueError:
            pass
    
    # Apply amount range filters
    if min_amount_str:
        try:
            min_amount = Decimal(min_amount_str)
            transactions = transactions.filter(amount__gte=min_amount)
        except (ValueError, InvalidOperation):
            pass
    
    if max_amount_str:
        try:
            max_amount = Decimal(max_amount_str)
            transactions = transactions.filter(amount__lte=max_amount)
        except (ValueError, InvalidOperation):
            pass
    
    # Apply overdue filter
    if overdue_only:
        today = date.today()
        transactions = transactions.filter(
            due_date__lt=today,
            status__in=['PENDING', 'PARTIAL']
        )
    
    # Apply tags filter
    if tags_filter:
        tag_list = [tag.strip() for tag in tags_filter.split(',') if tag.strip()]
        if tag_list:
            # Filter transactions that have any of the specified tags
            q_objects = Q()
            for tag in tag_list:
                q_objects |= Q(tags__contains=[tag])
            transactions = transactions.filter(q_objects)
    
    # Order by transaction date (most recent first)
    transactions = transactions.order_by('-transaction_date', '-id')
    
    # Get total count before pagination
    total_count = transactions.count()
    
    # Paginate results
    paginator = Paginator(transactions, per_page)
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    # Calculate range for display
    start_index = (page_obj.number - 1) * per_page + 1 if total_count > 0 else 0
    end_index = min(start_index + per_page - 1, total_count) if total_count > 0 else 0
    
    context = {
        "user": user,
        'transaction_data': page_obj,  # Paginated results
        'page_obj': page_obj,
        'current_filter': filter_type,
        'counter_party': counterparty,
        'counterparties': get_counter_parties(user),
        # Filter values to preserve state
        'filters': {
            'status': status_filter,
            'type': type_filter,
            'search': search_query,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'min_amount': min_amount_str,
            'max_amount': max_amount_str,
            'overdue': overdue_only,
            'tags': tags_filter,
            'per_page': per_page,
        },
        # Pagination info
        'total_count': total_count,
        'start_index': start_index,
        'end_index': end_index,
    }
    
    return render(request, 'ledger_transaction/ledgerTransaction.html', context)


# ============================================================================
# Status Management
# ============================================================================

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
    
    GET: Returns transaction details as JSON for editing
    POST: Updates transaction with new data
    
    Args:
        request: HTTP request (GET or POST)
        id: Transaction ID
        
    Returns:
        HttpResponse: JSON response (GET) or redirect (POST)
    """
    user = request.user
    
    try:
        entry = get_object_or_404(LedgerTransaction, id=id, created_by=user)
        
        # GET: Return transaction details for editing
        if request.method == "GET":
            return JsonResponse({
                'id': entry.id,
                'transaction_type': entry.transaction_type,
                'transaction_date': entry.transaction_date.strftime('%Y-%m-%d'),
                'amount': str(entry.amount),
                'counterparty': entry.counterparty,
                'counterparty_contact': entry.counterparty_contact or '',
                'counterparty_email': entry.counterparty_email or '',
                'description': entry.description,
                'reference_number': entry.reference_number or '',
                'invoice_number': entry.invoice_number or '',
                'due_date': entry.due_date.strftime('%Y-%m-%d') if entry.due_date else '',
                'payment_method': entry.payment_method or '',
                'notes': entry.notes or '',
                'tags': ','.join(entry.tags) if entry.tags else '',
                'status': entry.status,
            })
        
        # POST: Update transaction
        from datetime import datetime
        
        # Update basic fields
        entry.transaction_type = request.POST.get('transaction_type', entry.transaction_type).upper()
        
        transaction_date_str = request.POST.get('transaction_date')
        if transaction_date_str:
            entry.transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
        
        entry.amount = decimal.Decimal(request.POST.get('amount', entry.amount))
        entry.description = request.POST.get('description', entry.description)
        
        # Update counterparty details
        counterparty = request.POST.get('counterparty', entry.counterparty)
        if counterparty == 'other':
            counterparty = request.POST.get('counterparty_txt', '').upper()
        entry.counterparty = counterparty.upper()
        
        entry.counterparty_contact = request.POST.get('counterparty_contact', '')
        entry.counterparty_email = request.POST.get('counterparty_email', '')
        
        # Update transaction details
        entry.reference_number = request.POST.get('reference_number', '')
        entry.invoice_number = request.POST.get('invoice_number', '')
        entry.notes = request.POST.get('notes', '')
        
        # Update dates
        due_date_str = request.POST.get('due_date', '')
        if due_date_str:
            entry.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        else:
            entry.due_date = None
        
        # Update payment method
        payment_method = request.POST.get('payment_method', '')
        entry.payment_method = payment_method if payment_method else None
        
        # Update tags
        tags_str = request.POST.get('tags', '')
        entry.tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        
        # Handle file attachment (only if new file uploaded)
        if 'attachment' in request.FILES:
            entry.attachment = request.FILES['attachment']
        
        entry.save()
        
        messages.success(request, 'Transaction updated successfully')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
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


# ============================================================================
# Payment Recording
# ============================================================================

@login_required
def record_payment(request: HttpRequest, id: int) -> HttpResponse:
    """
    Record a payment against a ledger transaction.
    
    Supports partial payments - creates PaymentRecord and updates transaction status.
    
    Args:
        request: HTTP POST request with payment details
        id: Ledger transaction ID
        
    Returns:
        HttpResponse: Redirect or JSON response with success/error
    """
    from accounts.services.ledger_utils import record_payment as record_payment_util
    
    user = request.user
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    try:
        # Extract payment details
        payment_date_str = request.POST.get('payment_date')
        amount_paid = decimal.Decimal(request.POST.get('amount_paid', 0))
        payment_method = request.POST.get('payment_method')
        reference_number = request.POST.get('reference_number', '')
        notes = request.POST.get('notes', '')
        receipt_file = request.FILES.get('receipt_file')
        
        # Parse payment date
        from datetime import datetime
        if payment_date_str:
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        else:
            payment_date = datetime.today().date()
        
        # Record payment using utility function
        payment = record_payment_util(
            transaction_id=id,
            user=user,
            payment_date=payment_date,
            amount_paid=amount_paid,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            receipt_file=receipt_file
        )
        
        messages.success(
            request,
            f'Payment of ₹{amount_paid} recorded successfully'
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except ValueError as e:
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        traceback.print_exc()
        return HttpResponseServerError()


@login_required
def get_transaction_payments(request: HttpRequest, id: int) -> JsonResponse:
    """
    Get all payments for a transaction (AJAX endpoint).
    
    Args:
        request: HTTP GET request
        id: Transaction ID
        
    Returns:
        JSON response with payment history
    """
    user = request.user
    
    try:
        transaction = LedgerTransaction.objects.get(
            id=id,
            created_by=user
        )
        
        payments = transaction.payments.all().order_by('-payment_date')
        
        payment_list = [{
            'id': payment.id,
            'payment_date': payment.payment_date.strftime('%Y-%m-%d'),
            'amount_paid': str(payment.amount_paid),
            'payment_method': payment.get_payment_method_display(),
            'reference_number': payment.reference_number,
            'notes': payment.notes,
            'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M')
        } for payment in payments]
        
        return JsonResponse({
            'success': True,
            'payments': payment_list,
            'total_paid': str(transaction.paid_amount),
            'remaining': str(transaction.remaining_amount),
            'payment_percentage': transaction.get_payment_percentage()
        })
        
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================================================
# Enhanced Summary & Reports
# ============================================================================

@login_required
def get_counterparty_summary(request: HttpRequest) -> JsonResponse:
    """
    Get summary of all counterparties with balances (AJAX endpoint).
    
    Returns:
        JSON response with counterparty summaries
    """
    from accounts.services.ledger_utils import get_all_counterparties_summary
    
    user = request.user
    
    try:
        summaries = get_all_counterparties_summary(user)
        
        # Convert Decimal to string for JSON serialization
        for summary in summaries:
            summary['total_receivable'] = str(summary['total_receivable'])
            summary['total_payable'] = str(summary['total_payable'])
            summary['net_balance'] = str(summary['net_balance'])
            summary['overdue_receivable'] = str(summary['overdue_receivable'])
            summary['overdue_payable'] = str(summary['overdue_payable'])
        
        return JsonResponse({
            'success': True,
            'summaries': summaries
        })
        
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def get_aging_report(request: HttpRequest) -> JsonResponse:
    """
    Get aging analysis report (AJAX endpoint).
    
    Args:
        request: HTTP GET request with optional counterparty parameter
        
    Returns:
        JSON response with aging buckets
    """
    from accounts.services.ledger_utils import get_aging_report as get_aging_util
    
    user = request.user
    counterparty = request.GET.get('counterparty')
    
    try:
        report = get_aging_util(user, counterparty)
        
        # Convert Decimals to strings
        for category in ['receivables', 'payables']:
            for bucket in report[category]:
                report[category][bucket] = str(report[category][bucket])
        
        return JsonResponse({
            'success': True,
            'report': report,
            'counterparty': counterparty
        })
        
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def get_cash_flow_projection(request: HttpRequest) -> JsonResponse:
    """
    Get cash flow projection (AJAX endpoint).
    
    Args:
        request: HTTP GET request with optional days_ahead parameter
        
    Returns:
        JSON response with daily projections
    """
    from accounts.services.ledger_utils import get_cash_flow_projection as get_projection_util
    
    user = request.user
    days_ahead = int(request.GET.get('days_ahead', 30))
    
    try:
        projections = get_projection_util(user, days_ahead)
        
        # Convert data for JSON
        for proj in projections:
            proj['date'] = proj['date'].strftime('%Y-%m-%d')
            proj['receivable'] = str(proj['receivable'])
            proj['payable'] = str(proj['payable'])
            proj['net'] = str(proj['net'])
        
        return JsonResponse({
            'success': True,
            'projections': projections
        })
        
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

