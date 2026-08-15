"""
CSV Import views — Phase 8 of the finance-first rebuild.

Features:
- Upload CSV for PhonePe or GPay.
- Parse CSV to StagingEntry model.
- Review pending StagingEntry rows (assign category & account).
- Commit to Entry table.
"""

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Account, Category, Entry, StagingEntry


@login_required
def import_upload(request: HttpRequest) -> HttpResponse:
    """Show CSV upload form and parse uploaded file."""
    if request.method == 'GET':
        return render(request, 'finance/import_upload.html')

    source = request.POST.get('source')
    csv_file = request.FILES.get('csv_file')

    if not source or not csv_file:
        messages.error(request, 'Please select a source and provide a CSV file.')
        return redirect('finance:import_upload')

    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a valid CSV file.')
        return redirect('finance:import_upload')

    try:
        # Read the file
        file_data = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(file_data))
        
        # Generic fallback headers in case standard ones aren't found
        rows_processed = 0
        duplicates_skipped = 0
        
        with transaction.atomic():
            for row in reader:
                # Normalize keys (lowercase, strip whitespace)
                normalized_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                
                # Extract data based on source heuristics
                txn_id = ""
                date_str = ""
                amount_str = "0"
                entry_type = "expense"
                desc = ""
                
                if source == 'phonepe':
                    # Example assumed columns: date, transaction id, amount, type, description
                    txn_id = normalized_row.get('transaction id', '') or normalized_row.get('utr', '')
                    date_str = normalized_row.get('date', '')
                    amount_str = normalized_row.get('amount', '0')
                    desc = normalized_row.get('description', '') or normalized_row.get('narration', '')
                    
                    raw_type = normalized_row.get('type', '').upper()
                    entry_type = 'income' if 'CREDIT' in raw_type or 'RECEIVED' in raw_type else 'expense'
                    
                elif source == 'gpay':
                    # Example assumed columns: time, transaction id, amount, direction, description
                    txn_id = normalized_row.get('transaction id', '')
                    date_str = normalized_row.get('time', '') or normalized_row.get('date', '')
                    amount_str = normalized_row.get('amount', '0')
                    desc = normalized_row.get('description', '')
                    
                    raw_dir = normalized_row.get('direction', '').upper()
                    entry_type = 'income' if 'RECEIVED' in raw_dir else 'expense'
                
                # Cleanup amount (remove commas, currency symbols)
                amount_clean = ''.join(c for c in amount_str if c.isdigit() or c == '.')
                if not amount_clean:
                    continue
                    
                try:
                    amount = Decimal(amount_clean)
                except InvalidOperation:
                    continue
                    
                if amount <= 0:
                    continue
                
                # Parse date - try multiple common formats
                txn_date = None
                date_formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d %b %Y']
                for fmt in date_formats:
                    try:
                        txn_date = datetime.strptime(date_str.split()[0] if ' ' in date_str and fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y') else date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                        
                if not txn_date:
                    # Fallback to today if date parsing fails entirely
                    txn_date = datetime.today().date()
                
                # Duplicate Check
                # If txn_id is provided, check if it exists in StagingEntry or Entry (by original_txn_id if we added it to Entry, but we didn't).
                # So we check StagingEntry. We can also do a fuzzy check: same amount, date, type.
                is_duplicate = False
                if txn_id:
                    if StagingEntry.objects.filter(original_txn_id=txn_id).exists():
                        is_duplicate = True
                else:
                    # Fuzzy duplicate detection
                    if StagingEntry.objects.filter(date=txn_date, amount=amount, entry_type=entry_type).exists():
                        is_duplicate = True
                        
                if is_duplicate:
                    duplicates_skipped += 1
                    continue
                    
                # Create staging entry
                StagingEntry.objects.create(
                    source=source,
                    original_txn_id=txn_id,
                    date=txn_date,
                    amount=amount,
                    entry_type=entry_type,
                    raw_description=desc[:500],
                    status='pending',
                    created_by=request.user
                )
                rows_processed += 1
                
        messages.success(request, f'Successfully parsed {rows_processed} new entries. Skipped {duplicates_skipped} duplicates.')
        return redirect('finance:import_review')
        
    except Exception as e:
        messages.error(request, f'Error parsing CSV: {str(e)}')
        return redirect('finance:import_upload')


@login_required
def import_review(request: HttpRequest) -> HttpResponse:
    """List all pending StagingEntry rows for categorization."""
    user = request.user
    pending_entries = StagingEntry.objects.filter(created_by=user, status='pending')
    
    accounts = Account.objects.filter(created_by=user, is_active=True).order_by('name')
    expense_categories = Category.objects.filter(created_by=user, is_active=True, category_type='expense').order_by('name')
    income_categories = Category.objects.filter(created_by=user, is_active=True, category_type='income').order_by('name')
    
    # Simple default account
    default_account = accounts.first()
    
    return render(request, 'finance/import_review.html', {
        'entries': pending_entries,
        'accounts': accounts,
        'expense_categories': expense_categories,
        'income_categories': income_categories,
        'default_account': default_account,
    })


@login_required
@require_POST
def import_commit(request: HttpRequest) -> HttpResponse:
    """Commit selected StagingEntry rows to the main Entry table."""
    user = request.user
    
    # The form will send arrays of data. Since HTML forms send multiple inputs with the same name,
    # we use getlist() to retrieve them.
    staging_ids = request.POST.getlist('staging_id')
    account_ids = request.POST.getlist('account_id')
    category_ids = request.POST.getlist('category_id')
    notes = request.POST.getlist('note')
    
    if not staging_ids:
        messages.info(request, 'No entries selected to commit.')
        return redirect('finance:import_review')
        
    committed_count = 0
    with transaction.atomic():
        for i, staging_id in enumerate(staging_ids):
            # Skip if user selected "Skip" for category (we'll assume empty category means skip for now, 
            # or maybe we have a specific checkbox. Let's say if account is empty, skip).
            acc_id = account_ids[i] if i < len(account_ids) else None
            if not acc_id:
                continue
                
            staging = StagingEntry.objects.filter(id=staging_id, created_by=user, status='pending').first()
            if not staging:
                continue
                
            cat_id = category_ids[i] if i < len(category_ids) else None
            note = notes[i] if i < len(notes) else staging.raw_description
            
            # Create real entry
            Entry.objects.create(
                account_id=acc_id,
                entry_type=staging.entry_type,
                amount=staging.amount,
                date=staging.date,
                category_id=cat_id if cat_id else None,
                note=note[:255],
                created_by=user
            )
            
            # Mark as committed
            staging.status = 'committed'
            staging.save()
            committed_count += 1
            
    messages.success(request, f'Successfully committed {committed_count} entries.')
    return redirect('finance:entry_list')
