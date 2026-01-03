"""
Transaction Management Views

Handles income and expense transaction creation, listing, updating, and management.

Features:
- Transaction creation with duplicate detection
- Advanced filtering (type, category, beneficiary, date range, status)
- Transaction statistics and calculations
- Update transaction details
- Soft delete with undo functionality
- Bulk operations support
- Status toggle (Pending/Completed)
"""

import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Case, DecimalField, Q, Sum, Value, When
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseServerError,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import FinancialProduct, Transaction


# ============================================================================
# Constants
# ============================================================================

CATEGORIES = [
    'Shopping',
    'Food',
    'Investment',
    'Utilities',
    'Groceries',
    'Medical',
    'General',
    'Gifts',
    'Entertainment',
    'EMI',
    'Salary',
    'Other'
]


# ============================================================================
# Transaction Creation
# ============================================================================

@login_required
def create_transaction(request: HttpRequest) -> HttpResponse:
    """
    Create a new income or expense transaction.
    
    Transaction Types:
        - Income: Automatically sets beneficiary='Self', status='Completed'
        - Expense: Requires beneficiary, supports pending status
    
    Features:
        - Duplicate detection
        - Amount validation (must be > 0)
        - Auto-completion for income transactions
    
    Args:
        request: HTTP POST request with transaction details
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    try:
        # Extract form data
        transaction_type = request.POST.get("type")
        category = request.POST.get("category", "Other")
        date = request.POST.get("date")
        beneficiary = request.POST.get("beneficiary", "Self").title()
        amount = float(request.POST.get("amount", 0.0))
        description = request.POST.get("description", "")
        status = request.POST.get("status", "Completed")
        mode = request.POST.get("mode", "Online")
        mode_detail = request.POST.get("mode_detail")
        
        # Validate amount
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        
        # Special handling for income transactions
        if transaction_type == 'Income':
            beneficiary = 'Self'
            status = "Completed"
            mode = None
            mode_detail = None
        
        # Check for duplicate transaction
        try:
            existing = Transaction.objects.get(
                type=transaction_type,
                category=category,
                date=date,
                amount=amount,
                beneficiary=beneficiary,
                description=description,
                status=status,
                mode=mode,
                mode_detail=mode_detail,
                created_by=user,
                is_deleted=False
            )
            if existing:
                raise ValueError("Duplicate transaction already exists")
        except ObjectDoesNotExist:
            pass  # No duplicate, proceed with creation
        
        # Create transaction
        Transaction.objects.create(
            type=transaction_type,
            category=category,
            date=date,
            amount=amount,
            beneficiary=beneficiary,
            description=description,
            status=status,
            mode=mode,
            mode_detail=mode_detail,
            created_by=user,
        )
        
        messages.success(request, f'{transaction_type} transaction added successfully')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except ValidationError as e:
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    except ValueError as e:
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        traceback.print_exc()
        return HttpResponseServerError()


# ============================================================================
# Transaction Update
# ============================================================================

@login_required
def update_transaction(request: HttpRequest, id: int) -> HttpResponse:
    """
    Update transaction details.
    
    GET: Returns transaction details as JSON
    POST: Updates transaction fields
    
    Args:
        request: HTTP request (GET or POST)
        id: Transaction ID
        
    Returns:
        HttpResponse: JSON response (GET) or redirect (POST)
    """
    try:
        entry = get_object_or_404(Transaction, id=id)
        
        # GET: Return transaction details
        if request.method == "GET":
            return JsonResponse({
                "type": entry.type,
                "category": entry.category,
                "date": entry.date,
                "amount": entry.amount,
                "description": entry.description,
                "beneficiary": entry.beneficiary,
                "mode_detail": entry.mode_detail,
                "mode": entry.mode,
                "status": entry.status
            })
        
        # POST: Update transaction
        entry.category = request.POST.get("category", entry.category)
        entry.date = request.POST.get("date", entry.date)
        entry.amount = request.POST.get("amount", entry.amount)
        entry.description = request.POST.get("description", entry.description)
        entry.beneficiary = request.POST.get("beneficiary", entry.beneficiary).title()
        
        # Handle mode_detail
        mode_detail = request.POST.get("mode_detail", entry.mode_detail)
        entry.mode_detail = mode_detail.title() if mode_detail else mode_detail
        
        # Handle mode (can be None)
        mode = request.POST.get("mode", entry.mode)
        entry.mode = mode.title() if mode else mode
        
        entry.save()
        
        messages.success(request, "Transaction updated successfully")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except ObjectDoesNotExist:
        messages.error(request, "Transaction not found")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# ============================================================================
# Transaction Listing & Filtering
# ============================================================================

@login_required
def transaction_detail(request: HttpRequest) -> HttpResponse:
    """
    Display transactions with advanced filtering and statistics.
    
    Filter Options:
        - type: Transaction type (Income/Expense)
        - category: Transaction category
        - beneficiary: Beneficiary name
        - daterange: Date range (DD/MM/YYYY - DD/MM/YYYY)
        - mode: Payment mode
        - status: Transaction status (Pending/Completed)
        - search: Search in amount, beneficiary, or description
    
    Calculations:
        - Total income
        - Total expense (excluding investments)
        - Total investment
        - Total EMI
        - Paid amount
        - Pending amount
        - Previous pending (before date range)
    
    Args:
        request: HTTP GET request with filter parameters
        
    Returns:
        HttpResponse: Rendered transaction details page
    """
    user = request.user
    
    try:
        # Extract filter parameters
        type_filter = request.GET.getlist('type', [])
        category = request.GET.get('category', '')
        beneficiary = request.GET.get('beneficiary', '')
        daterange = request.GET.get('daterange', '')
        mode = request.GET.get('mode', '')
        status = request.GET.get('status', '')
        search_query = request.GET.get("search", '').strip()
        
        # Build query filters
        filter_data = Q(created_by=user, is_deleted=False)
        filter_remaining_amount = Q(created_by=user, is_deleted=False, status="Pending")
        start_date = timezone.now().date().replace(day=1)
        
        # Search filter
        if search_query:
            if search_query.isdigit():
                # Search by amount
                filter_data &= Q(amount=search_query)
            else:
                # Search by beneficiary or description
                filter_data &= Q(
                    Q(beneficiary__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
        
        # Apply filters
        if beneficiary:
            filter_data &= Q(beneficiary__iexact=beneficiary.title())
        if type_filter:
            filter_data &= Q(type__in=type_filter)
        if category:
            filter_data &= Q(category=category)
        if mode:
            filter_data &= Q(mode=mode)
        if status:
            filter_data &= Q(status=status)
        
        # Date range filter
        if daterange:
            date_parts = daterange.split(" - ")
            start_date_str = date_parts[0].strip()
            end_date_str = date_parts[1].strip()
            start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
            end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
            filter_data &= Q(date__gte=start_date, date__lte=end_date)
        
        # Default: Current month if no filters applied
        if not any([search_query, beneficiary, type_filter, category, mode, status, daterange]):
            search_query = datetime.now().strftime("%B %Y")
            now = datetime.now()
            filter_data &= Q(date__year=now.year, date__month=now.month)
        
        # Fetch transactions with optimization
        transactions = Transaction.objects.filter(
            filter_data
        ).select_related('created_by', 'source').order_by('-date')
        
        # Calculate statistics using database aggregations
        aggregations = transactions.aggregate(
            income=Sum('amount', filter=Q(type='Income'), output_field=DecimalField()),
            expense=Sum('amount', filter=Q(type='Expense') & ~Q(category='Investment'), output_field=DecimalField()),
            investment=Sum('amount', filter=Q(category='Investment'), output_field=DecimalField()),
            emi=Sum('amount', filter=Q(category='EMI'), output_field=DecimalField()),
            paid_amount=Sum('amount', filter=Q(status='Completed', type='Expense'), output_field=DecimalField()),
            pending_amount=Sum('amount', filter=Q(status='Pending', type='Expense'), output_field=DecimalField()),
        )
        
        # Handle None values from aggregation
        income = aggregations['income'] or 0
        expense = aggregations['expense'] or 0
        investment = aggregations['investment'] or 0
        emi = aggregations['emi'] or 0
        paid_amount = aggregations['paid_amount'] or 0
        pending_amount = aggregations['pending_amount'] or 0
        
        # Calculate previous pending amount
        filter_remaining_amount &= Q(date__lt=start_date)
        previous_pending_agg = Transaction.objects.filter(
            filter_remaining_amount
        ).aggregate(
            total=Sum('amount', output_field=DecimalField())
        )
        previous_pending = previous_pending_agg['total'] or 0
        
        # Build calculation summary
        transaction_calculation = {
            "income": income,
            "expense": expense,
            "emi": emi,
            "investment": investment,
            "pending_amount": pending_amount,
            "paid_amount": paid_amount,
            "previous_pending": previous_pending,
            "total": income - expense - investment
        }
        
        context = {
            "user": user,
            "transaction_data": transactions,
            "transaction_calculation": transaction_calculation,
            "data": {
                "type": type_filter,
                "category": category,
                "beneficiary": beneficiary,
                "daterange": daterange,
                "mode": mode,
                "status": status,
                "key": search_query,
            },
            "categories": CATEGORIES
        }
        
        return render(request, "transaction/transactionDetails.html", context)
        
    except Exception as e:
        traceback.print_exc()
        messages.error(request, "An error occurred while loading transactions")
        
        # Return empty data on error
        context = {
            "user": user,
            "transaction_data": [],
            "transaction_calculation": {
                "income": 0,
                "expense": 0,
                "emi": 0,
                "investment": 0,
                "pending_amount": 0,
                "paid_amount": 0,
                "previous_pending": 0,
                "total": 0
            },
            "categories": CATEGORIES,
            "data": {
                "type": type_filter if 'type_filter' in locals() else [],
                "category": category if 'category' in locals() else '',
                "beneficiary": beneficiary if 'beneficiary' in locals() else '',
                "daterange": daterange if 'daterange' in locals() else '',
                "mode": mode if 'mode' in locals() else '',
                "status": status if 'status' in locals() else '',
                "key": search_query if 'search_query' in locals() else ''
            }
        }
        
        return render(request, "transaction/transactionDetails.html", context)


# ============================================================================
# Deletion & Undo
# ============================================================================

@login_required
def fetch_deleted_transaction(request: HttpRequest) -> HttpResponse:
    """
    Display all deleted transactions.
    
    Args:
        request: HTTP GET request
        
    Returns:
        HttpResponse: Rendered deleted transactions page
    """
    user = request.user
    
    try:
        deleted_transactions = Transaction.objects.filter(
            created_by=user,
            is_deleted=True
        ).order_by('-deleted_at')
        
        context = {
            "data": deleted_transactions,
            "user": user
        }
        
        return render(request, 'transaction/deletedTransactions.html', context)
        
    except Exception as e:
        traceback.print_exc()
        messages.error(request, "An error occurred while loading deleted transactions")
        return redirect('utilities')


@login_required
def delete_transaction(request: HttpRequest, id: Optional[int] = None) -> HttpResponse:
    """
    Soft delete transaction(s).
    
    Supports:
        - Single transaction delete (GET with id)
        - Bulk delete (POST with record_ids)
    
    Args:
        request: HTTP request (GET or POST)
        id: Transaction ID for single delete (optional)
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    try:
        # Get list of transactions to delete
        if request.method == "GET":
            delete_list = [id]
        else:
            delete_list = request.POST.getlist('record_ids', [])
        
        deleted_count = 0
        for txn_id in delete_list:
            entry = Transaction.objects.get(id=txn_id, created_by=user)
            entry.is_deleted = True
            entry.deleted_at = datetime.now()
            entry.save()
            deleted_count += 1
        
        messages.success(request, f'{deleted_count} transaction(s) deleted')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, "An error occurred while deleting transactions")
        return redirect('transaction-detail')


@login_required
def undo_transaction(request: HttpRequest, id: Optional[int] = None) -> HttpResponse:
    """
    Restore deleted transaction(s).
    
    Supports:
        - Single transaction restore (GET with id)
        - Bulk restore (POST with record_ids)
    
    Also restores associated financial product if it was deleted.
    
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
            entry = Transaction.objects.get(id=txn_id)
            
            # Restore associated financial product if needed
            if entry.source_id is not None:
                try:
                    product = FinancialProduct.objects.get(
                        id=entry.source_id,
                        created_by=user
                    )
                    if product.is_deleted:
                        product.is_deleted = False
                        product.save()
                except FinancialProduct.DoesNotExist:
                    pass  # Product doesn't exist, continue
            
            # Restore transaction
            entry.is_deleted = False
            entry.deleted_at = None
            entry.save()
            restored_count += 1
        
        messages.success(request, f'{restored_count} transaction(s) restored')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, "An error occurred while restoring transactions")
        return redirect('getDeletedEntries')


# ============================================================================
# Status Management
# ============================================================================

@login_required
def update_transaction_status(request: HttpRequest, id: int) -> HttpResponse:
    """
    Toggle transaction status between Pending and Completed.
    
    Supports:
        - Single transaction update (GET with id)
        - Bulk update (POST with record_ids)
    
    Args:
        request: HTTP request (GET or POST)
        id: Transaction ID for single update
        
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
        for txn_id in transaction_list:
            entry = Transaction.objects.get(id=txn_id, created_by=user)
            entry.status = "Completed" if entry.status == "Pending" else "Pending"
            entry.save()
            updated_count += 1
        
        messages.success(request, f'{updated_count} transaction(s) status updated')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, "An error occurred while updating status")
        return redirect('transaction-detail')
