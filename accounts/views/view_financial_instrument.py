"""
Financial Instrument Management Views

Handles creation, listing, updating, and management of financial instruments
including Loans, SIPs (Systematic Investment Plans), and Split payments.

Features:
- Financial product creation with EMI/installment generation
- Product listing with search and status filtering
- Update product details with automatic transaction recalculation
- Transaction tracking and status management
- Soft delete functionality
"""

import datetime
import decimal
import traceback
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import F, Q, Sum
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import FinancialProduct, Transaction


# ============================================================================
# Helper Functions
# ============================================================================

def desired_date(start_date: str, months_offset: int) -> str:
    """
    Calculate a date N months from the start date.
    
    Handles month/year rollovers properly. Used for calculating
    EMI/installment due dates.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        months_offset: Number of months to add
        
    Returns:
        str: Calculated date in YYYY-MM-DD format
        
    Example:
        >>> desired_date("2024-01-31", 1)
        "2024-02-29"  # Handles month boundaries
    """
    payment_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    current_month = payment_date.month
    current_year = payment_date.year
    current_day = payment_date.day
    
    desired_month = current_month + months_offset
    desired_year = current_year + (desired_month - 1) // 12
    desired_month = (desired_month - 1) % 12 + 1
    
    desired_date_obj = datetime.datetime(desired_year, desired_month, current_day)
    return desired_date_obj.strftime('%Y-%m-%d')


# ============================================================================
# Financial Product Creation
# ============================================================================

@login_required
def create_finance(request: HttpRequest) -> HttpResponse:
    """
    Create a new financial product (Loan, SIP, or Split payment).
    
    Automatically generates associated transactions (EMIs/installments)
    based on the product parameters.
    
    Product Types:
        - Loan: Creates EMI transactions
        - SIP: Creates investment transactions
        - Split: Creates split payment transactions
    
    Args:
        request: HTTP POST request with product details
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    try:
        # Extract form data
        name = request.POST.get("name", "")
        product_type = request.POST.get("type", "")
        category = request.POST.get("category", "")
        amount = int(request.POST.get("amount", 0))
        no_of_installments = int(request.POST.get("no_of_installments", 1))
        started_on = request.POST.get("started_on", "")
        
        # Validate installments
        if no_of_installments < 1:
            raise ValueError('Number of installments cannot be zero')
        
        # Check for duplicate product
        try:
            existing = FinancialProduct.objects.get(
                name=name,
                type=product_type,
                amount=amount,
                no_of_installments=no_of_installments,
                started_on=started_on,
                created_by=user
            )
            if existing:
                raise ValueError(f"{product_type} already exists")
        except ObjectDoesNotExist:
            pass  # Product doesn't exist, proceed with creation
        
        # Create financial product
        new_product = FinancialProduct.objects.create(
            name=name,
            type=product_type,
            amount=amount,
            no_of_installments=no_of_installments,
            started_on=started_on,
            created_by=user
        )
        
        # Calculate installment amount
        emi_amount = round((amount / no_of_installments), 2)
        
        # Determine category and description based on type
        if product_type == 'Loan':
            category = "EMI"
            sub_label = "EMI"
        elif product_type == "Split":
            sub_label = product_type
            # category remains as provided
        else:  # SIP or other
            category = "Investment"
            sub_label = product_type
        
        # Generate installment transactions
        for i in range(no_of_installments):
            Transaction.objects.create(
                type="Expense",
                category=category,
                date=desired_date(started_on, i),
                amount=emi_amount,
                beneficiary='Self',
                description=f'{name} {sub_label} {i + 1}',
                status="Pending",
                mode="Online",
                mode_detail=product_type,
                created_by=user,
                source=new_product
            )
        
        messages.success(request, f'{product_type} "{name}" added successfully')
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
# Financial Product Listing
# ============================================================================

@login_required
def finance_details(request: HttpRequest) -> HttpResponse:
    """
    List all financial products with search functionality.
    
    Features:
        - Search by name or type
        - Display remaining amount and installments
        - Sort by status (Open first) then name
        - Show only non-deleted products
    
    Args:
        request: HTTP GET request with optional 'search' parameter
        
    Returns:
        HttpResponse: Rendered finance home page
    """
    user = request.user
    
    try:
        search_query = request.GET.get('search', '').strip()
        query = Q(created_by=user, is_deleted=False)
        
        if search_query:
            query &= Q(name__icontains=search_query) | Q(type=search_query)
        
        # Get products with optimized query
        products = FinancialProduct.objects.filter(query).select_related(
            'created_by'
        ).order_by(
            F('status').desc(),  # Open status first
            'name'
        )
        
        # Calculate remaining amounts for each product
        for product in products:
            installments = Transaction.objects.filter(
                source=product.id,
                is_deleted=False
            )
            remaining_transactions = [
                trn for trn in installments if trn.status != "Completed"
            ]
            product.remaining_amount = sum(trn.amount for trn in remaining_transactions)
            product.remaining_installments = len(remaining_transactions)
        
        context = {
            'details': products,
            'search_query': search_query,
            'user': user
        }
        
        return render(request, 'financial_instrument/financeHome.html', context)
        
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        traceback.print_exc()
        return HttpResponseServerError()


# ============================================================================
# Financial Product Update
# ============================================================================

@login_required
def update_finance_detail(request: HttpRequest, id: int) -> HttpResponse:
    """
    Update financial product details and recalculate transactions.
    
    GET: Returns product details as JSON
    POST: Updates product and associated transactions
    
    Handles complex scenarios:
        - Name changes: Updates all transaction descriptions
        - Type changes: Updates categories and labels
        - Date changes: Recalculates installment dates (validated against paid dates)
        - Amount/installment changes: Recalculates EMI amounts, adds/removes transactions
    
    Args:
        request: HTTP request (GET or POST)
        id: Financial product ID
        
    Returns:
        HttpResponse: JSON response (GET) or redirect (POST)
    """
    user = request.user
    
    try:
        details = get_object_or_404(FinancialProduct, created_by=user, id=id)
        
        # GET: Return product details
        if request.method == "GET":
            return JsonResponse({
                "type": details.type,
                "name": details.name,
                "started_on": details.started_on,
                "amount": details.amount,
                "no_of_installments": details.no_of_installments
            })
        
        # POST: Update product
        name = request.POST.get("name", "")
        i_type = request.POST.get("type", "")
        started_on = request.POST.get("started_on", "")
        amount = decimal.Decimal(request.POST.get("amount", 0))
        no_of_installments = int(request.POST.get("no_of_installments", 1))
        category = request.POST.get("category", "")
        
        if no_of_installments < 1:
            raise ValueError('Number of installments cannot be zero')
        
        sub_label = 'EMI' if i_type == 'Loan' else i_type
        transactions = Transaction.objects.filter(
            created_by=user,
            source_id=id,
            is_deleted=False
        )
        
        # ====================================================================
        # Update Name
        # ====================================================================
        
        details.name = name
        for index, trn in enumerate(transactions, 1):
            trn.description = f'{name} {sub_label} {index}'
            trn.save()
        
        # ====================================================================
        # Update Type
        # ====================================================================
        
        if i_type != details.type:
            details.type = i_type
            
            # Determine category based on new type
            if i_type == 'Loan':
                category = "EMI"
            elif i_type == "Split":
                # Keep provided category
                pass
            else:
                category = "Investment"
            
            for index, trn in enumerate(transactions, 1):
                trn.category = category
                trn.mode_detail = i_type
                trn.description = f'{name} {sub_label} {index}'
                trn.save()
        
        # ====================================================================
        # Update Start Date
        # ====================================================================
        
        new_start_date = datetime.datetime.strptime(started_on, "%Y-%m-%d").date()
        if new_start_date != details.started_on:
            no_of_paid_installments = sum(
                1 if trn.status == "Completed" else 0 for trn in transactions
            )
            paid_dates = [trn.date for trn in transactions if trn.status == "Completed"]
            
            # Validate: new start date can't be after any paid installment date
            if paid_dates:
                for date in paid_dates:
                    if date >= new_start_date:
                        raise ValueError(f'Start date cannot be before paid installment date: {date}')
            
            # Update start date if all pending
            if not no_of_paid_installments:
                details.started_on = started_on
            
            # Recalculate dates for pending transactions
            for i, trn in enumerate(transactions):
                if i >= no_of_paid_installments:
                    offset = i - no_of_paid_installments
                    trn.date = desired_date(started_on, offset)
                    trn.save()
        
        # ====================================================================
        # Update Amount or Installments
        # ====================================================================
        
        if amount != details.amount or no_of_installments != details.no_of_installments:
            previous_installments = details.no_of_installments
            completed_count = sum(1 if x.status == 'Completed' else 0 for x in transactions)
            
            # If there are completed transactions
            if completed_count:
                paid_amount = sum(
                    x.amount if x.status == 'Completed' else 0 for x in transactions
                )
                
                # Validate changes
                if amount < paid_amount:
                    raise ValueError(
                        f'Amount cannot be less than total paid amount: {paid_amount}'
                    )
                
                if no_of_installments < completed_count:
                    raise ValueError(
                        f'Installments cannot be less than completed count: {completed_count}'
                    )
                
                if amount > paid_amount and no_of_installments == completed_count:
                    raise ValueError(
                        f'Installments cannot be less than {completed_count + 1}'
                    )
                
                # Recalculate remaining installment amount
                remaining_amount = amount - paid_amount
                remaining_installments = no_of_installments - completed_count
                emi_amount = round(
                    (remaining_amount / remaining_installments), 2
                ) if remaining_installments else 0
                
                details.amount = amount
                details.no_of_installments = no_of_installments
                
                # Add new installments
                if no_of_installments > previous_installments:
                    new_trn_count = no_of_installments - previous_installments
                    
                    # Update existing pending transactions
                    for trn in transactions:
                        if trn.status != 'Completed':
                            trn.amount = emi_amount
                            trn.save()
                    
                    # Create new transactions
                    last_trn = transactions.last()
                    for i in range(previous_installments, previous_installments + new_trn_count):
                        Transaction.objects.create(
                            type=last_trn.type,
                            category=last_trn.category,
                            date=desired_date(last_trn.date.strftime("%Y-%m-%d"), 1),
                            amount=emi_amount,
                            beneficiary='Self',
                            description=f'{name} {sub_label} {i + 1}',
                            status="Pending",
                            mode="Online",
                            mode_detail=details.type,
                            created_by=user,
                            source=details
                        )
                
                # Remove extra installments
                elif no_of_installments < previous_installments:
                    for index, trn in enumerate(transactions, 1):
                        if index <= no_of_installments:
                            if trn.status != 'Completed':
                                trn.amount = emi_amount
                                trn.save()
                        else:
                            trn.delete()
                
                # Same number of installments, update amounts
                else:
                    for trn in transactions:
                        if trn.status != 'Completed':
                            trn.amount = emi_amount
                            trn.save()
            
            # All transactions are pending
            else:
                details.amount = amount
                details.no_of_installments = no_of_installments
                emi_amount = round((amount / no_of_installments), 2)
                
                # Add new installments
                if no_of_installments > previous_installments:
                    new_trn_count = no_of_installments - previous_installments
                    
                    for trn in transactions:
                        trn.amount = emi_amount
                        trn.save()
                    
                    last_trn = transactions.last()
                    for i in range(previous_installments, previous_installments + new_trn_count):
                        Transaction.objects.create(
                            type=last_trn.type,
                            category=last_trn.category,
                            date=desired_date(last_trn.date.strftime("%Y-%m-%d"), 1),
                            amount=emi_amount,
                            beneficiary='Self',
                            description=f'{name} {sub_label} {i + 1}',
                            status="Pending",
                            mode="Online",
                            mode_detail=details.type,
                            created_by=user,
                            source=details
                        )
                
                # Remove extra installments
                elif no_of_installments < previous_installments:
                    for index, trn in enumerate(transactions, 1):
                        if index <= no_of_installments:
                            trn.amount = emi_amount
                            trn.save()
                        else:
                            trn.delete()
                
                # Update all amounts
                else:
                    for trn in transactions:
                        trn.amount = emi_amount
                        trn.save()
        
        details.save()
        messages.success(request, f'"{name}" updated successfully')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except ValueError as e:
        traceback.print_exc()
        messages.error(request, str(e))
        return redirect('finance-details')
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        traceback.print_exc()
        return HttpResponseServerError()


# ============================================================================
# Transaction Listing
# ============================================================================

@login_required
def fetch_financial_transaction(request: HttpRequest, id: int) -> HttpResponse:
    """
    Display all transactions for a specific financial product.
    
    Shows detailed information including:
        - All related transactions
        - Paid vs pending amounts
        - Remaining installments
    
    Args:
        request: HTTP GET request
        id: Financial product ID
        
    Returns:
        HttpResponse: Rendered installment details page
    """
    user = request.user
    
    try:
        product_details = FinancialProduct.objects.get(created_by=user, id=id)
        
        if not product_details:
            raise ValueError('Product not found')
        
        all_transactions = Transaction.objects.filter(
            created_by=user,
            source=id,
            is_deleted=False
        ).order_by('-date')
        
        # Calculate summary statistics
        paid_transactions = [trn for trn in all_transactions if trn.status == "Completed"]
        product_details.paid_amount = sum(trn.amount for trn in paid_transactions)
        product_details.paid_installment = len(paid_transactions)
        product_details.remaining_amount = product_details.amount - product_details.paid_amount
        
        context = {
            'all_transaction': all_transactions,
            'product_details': product_details,
            'user': user
        }
        
        return render(request, 'financial_instrument/installmentDetails.html', context)
        
    except ValueError as e:
        traceback.print_exc()
        messages.error(request, str(e))
        return redirect('finance-details')
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        traceback.print_exc()
        return HttpResponseServerError()


# ============================================================================
# Status Management
# ============================================================================

@login_required
def update_instrument_status(request: HttpRequest, id: int) -> HttpResponse:
    """
    Toggle financial product status between Open and Closed.
    
    Validation: Cannot close if there are pending installments.
    
    Args:
        request: HTTP request
        id: Financial product ID
        
    Returns:
        HttpResponse: Redirect to finance details
    """
    user = request.user
    
    try:
        product_details = FinancialProduct.objects.get(created_by=user, id=id)
        
        if not product_details:
            raise ValueError('Product not found')
        
        # Check for pending installments
        all_transactions = Transaction.objects.filter(
            created_by=user,
            source=id,
            is_deleted=False
        )
        pending_transactions = [trn for trn in all_transactions if trn.status == "Pending"]
        
        if pending_transactions:
            raise ValueError(
                f'Cannot close "{product_details.name.title()}" due to '
                f'{len(pending_transactions)} pending installment(s)'
            )
        
        # Toggle status
        if product_details.status == "Open":
            product_details.status = 'Closed'
        else:
            product_details.status = 'Open'
        
        product_details.save()
        
        messages.info(request, f'"{product_details.name.title()}" status updated')
        return redirect('finance-details')
        
    except ValueError as e:
        traceback.print_exc()
        messages.error(request, str(e))
        return redirect('finance-details')
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        traceback.print_exc()
        return HttpResponseServerError()


# ============================================================================
# Deletion
# ============================================================================

@login_required
def remove_instrument(request: HttpRequest, id: int) -> HttpResponse:
    """
    Soft delete a financial product.
    
    Validation: Cannot delete if product has associated transactions.
    
    Args:
        request: HTTP request
        id: Financial product ID
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    try:
        # Check for associated transactions
        if Transaction.objects.filter(created_by=user, source=id, is_deleted=False).exists():
            messages.error(request, "Cannot delete product with existing installments")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
        # Soft delete
        current_product = FinancialProduct.objects.get(
            created_by=user,
            id=id,
            is_deleted=False
        )
        current_product.is_deleted = True
        current_product.deleted_at = datetime.datetime.today()
        current_product.save()
        
        messages.success(request, f'"{current_product.name}" deleted successfully')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        traceback.print_exc()
        return HttpResponseServerError()
