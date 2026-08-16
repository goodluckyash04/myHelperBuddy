"""
Ledger views — Phase 6 of the finance-first rebuild.

Features:
- Ledger Contact list: Shows contacts and their net balance (sum of taken - sum of given).
- Ledger Contact create/edit.
- Ledger Detail: Per-contact view showing history of given/taken entries.
- Ledger Entry create: Log a given or taken amount.
- Settle Up action: Mark entries as settled.
"""

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, F
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import LedgerContact, LedgerEntry


@login_required
def ledger_contact_list(request: HttpRequest) -> HttpResponse:
    """List ledger contacts and calculate net balance for each."""
    user = request.user
    contacts = LedgerContact.objects.filter(created_by=user).order_by('name')

    # Calculate net balances: (Total Taken from them) - (Total Given to them)
    # So if net > 0, you owe them. If net < 0, they owe you.
    contact_data = []
    
    # We only look at 'open' entries to compute current net balance
    for contact in contacts:
        totals = LedgerEntry.objects.filter(
            contact=contact,
            status='open'
        ).aggregate(
            total_given=Sum('amount', filter=Q(entry_type='given')),
            total_taken=Sum('amount', filter=Q(entry_type='taken'))
        )
        
        given = totals['total_given'] or 0
        taken = totals['total_taken'] or 0
        net_balance = taken - given
        
        contact_data.append({
            'contact': contact,
            'given': given,
            'taken': taken,
            'net_balance': net_balance,
        })
        
    return render(request, 'finance/ledger_list.html', {'contact_data': contact_data})


@login_required
def ledger_contact_create(request: HttpRequest) -> HttpResponse:
    """Create a new ledger contact."""
    if request.method == 'GET':
        return render(request, 'finance/ledger_contact_form.html', {
            'mode': 'create',
            'form_data': {},
        })
        
    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()
    
    if not name:
        messages.error(request, 'Contact name is required.')
        return render(request, 'finance/ledger_contact_form.html', {
            'mode': 'create', 
            'form_data': {'name': name, 'phone': phone}
        })
        
    contact = LedgerContact.objects.create(
        name=name,
        phone=phone,
        created_by=request.user
    )
    
    messages.success(request, f'Contact "{name}" added.')
    return redirect('finance:ledger_detail', pk=contact.pk)


@login_required
def ledger_contact_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit an existing ledger contact."""
    contact = get_object_or_404(LedgerContact, pk=pk, created_by=request.user)
    
    if request.method == 'GET':
        return render(request, 'finance/ledger_contact_form.html', {
            'mode': 'edit', 
            'contact': contact
        })
        
    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()
    
    if not name:
        messages.error(request, 'Contact name is required.')
        return render(request, 'finance/ledger_contact_form.html', {
            'mode': 'edit', 
            'contact': contact
        })
        
    contact.name = name
    contact.phone = phone
    contact.save()
    
    messages.success(request, f'Contact "{name}" updated.')
    return redirect('finance:ledger_detail', pk=contact.pk)


@login_required
def ledger_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Show details for a specific contact, including history of given/taken entries."""
    user = request.user
    contact = get_object_or_404(LedgerContact, pk=pk, created_by=user)
    
    entries = LedgerEntry.objects.filter(contact=contact).order_by('-date', '-created_at')
    
    # Calculate net balance from open entries
    totals = entries.filter(status='open').aggregate(
        total_given=Sum('amount', filter=Q(entry_type='given')),
        total_taken=Sum('amount', filter=Q(entry_type='taken'))
    )
    given = totals['total_given'] or 0
    taken = totals['total_taken'] or 0
    net_balance = taken - given
    
    return render(request, 'finance/ledger_detail.html', {
        'contact': contact,
        'entries': entries,
        'given': given,
        'taken': taken,
        'net_balance': net_balance,
        'today': date.today().isoformat(),
    })


@login_required
@require_POST
def ledger_entry_add(request: HttpRequest, pk: int) -> HttpResponse:
    """Add a new given or taken entry for a contact."""
    user = request.user
    contact = get_object_or_404(LedgerContact, pk=pk, created_by=user)
    
    entry_type = request.POST.get('entry_type', '')
    amount_str = request.POST.get('amount', '')
    date_str = request.POST.get('date', '')
    note = request.POST.get('note', '').strip()
    
    if entry_type not in ('given', 'taken'):
        messages.error(request, 'Invalid entry type.')
        return redirect('finance:ledger_detail', pk=pk)
        
    try:
        amount = float(amount_str)
        if amount <= 0:
            messages.error(request, 'Amount must be positive.')
            return redirect('finance:ledger_detail', pk=pk)
    except (ValueError, TypeError):
        messages.error(request, 'Invalid amount.')
        return redirect('finance:ledger_detail', pk=pk)
        
    if not date_str:
        date_str = date.today().isoformat()
        
    LedgerEntry.objects.create(
        contact=contact,
        entry_type=entry_type,
        amount=amount,
        date=date_str,
        note=note,
        status='open',
        created_by=user,
    )
    
    verb = "lent" if entry_type == 'given' else "borrowed"
    messages.success(request, f'Logged ₹{amount} {verb}.')
    return redirect('finance:ledger_detail', pk=pk)


@login_required
@require_POST
def ledger_settle_up(request: HttpRequest, pk: int) -> HttpResponse:
    """Mark all open entries for this contact as settled."""
    user = request.user
    contact = get_object_or_404(LedgerContact, pk=pk, created_by=user)
    
    updated = LedgerEntry.objects.filter(
        contact=contact, 
        status='open'
    ).update(
        status='settled',
        settled_at=timezone.now()
    )
    
    messages.success(request, f'Settled {updated} open entries with {contact.name}.')
    return redirect('finance:ledger_detail', pk=pk)
