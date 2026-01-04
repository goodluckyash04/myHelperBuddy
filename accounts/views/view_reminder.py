"""
Reminder Management Views

Handles reminder creation, listing, and cancellation with support for
various frequency patterns (daily, monthly, yearly, custom).

Features:
- Create reminders with multiple frequency options
- Calculate today's active reminders based on frequency
- List all reminders
- Cancel (soft delete) reminders
- Duplicate detection
"""

import datetime
from datetime import date
from typing import List

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import Reminder


# ============================================================================
# Reminder Creation
# ============================================================================

@login_required
def add_reminder(request: HttpRequest) -> HttpResponse:
    """
    Create a new reminder with specified frequency pattern.
    
    Frequency Options:
        - Daily: Repeats every day
        - Monthly: Repeats on same day each month
        - Yearly: Repeats on same date each year
        - Custom: Repeats every N days (custom_repeat_days)
    
    Features:
        - Duplicate detection (same title + date)
        - Custom repeat interval support
        - Auto-validation
    
    Args:
        request: HTTP POST request with reminder details
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    # Extract form data
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    reminder_date_str = request.POST.get('reminder_date')
    frequency = request.POST.get('frequency', Reminder.DAILY)
    custom_repeat_days = request.POST.get('custom_repeat_days')
    
    # Validate required fields
    if not title or not reminder_date_str:
        messages.error(request, "Title and reminder date are required")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    try:
        # Parse reminder date
        reminder_date = timezone.datetime.strptime(reminder_date_str, "%Y-%m-%d").date()
        
        # Check for duplicate reminder
        existing_reminder = Reminder.objects.filter(
            title=title,
            reminder_date=reminder_date,
            created_by=user
        ).first()
        
        if existing_reminder:
            messages.error(
                request,
                f"Reminder '{title}' for {reminder_date} already exists"
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
        # Create reminder
        reminder = Reminder.objects.create(
            title=title,
            description=description,
            reminder_date=reminder_date,
            frequency=frequency,
            created_by=user,
            custom_repeat_days=int(custom_repeat_days) if frequency == 'custom' and custom_repeat_days else None
        )
        
        messages.success(request, f"Reminder '{title}' added successfully")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except ValueError as e:
        messages.error(request, f"Invalid date format: {str(e)}")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# ============================================================================
# Reminder Listing
# ============================================================================

@login_required
def todays_reminder(request: HttpRequest) -> HttpResponse:
    """
    Display reminders due today.
    
    Calculates which reminders are active today based on their
    frequency patterns (daily, monthly, yearly, custom).
    
    Args:
        request: HTTP GET request
        
    Returns:
        HttpResponse: Rendered reminder view with today's reminders
    """
    user = request.user
    
    context = {
        "user": user,
        'reminders': calculate_reminder(user),
        'key': "today"
    }
    
    return render(request, 'reminder/viewReminder.html', context)


@login_required
def reminder_list(request: HttpRequest) -> HttpResponse:
    """
    Display all active reminders.
    
    Shows all non-deleted reminders ordered by date (newest first).
    
    Args:
        request: HTTP GET request
        
    Returns:
        HttpResponse: Rendered reminder view with all reminders
    """
    user = request.user
    
    # Get all active reminders
    reminders = Reminder.objects.filter(
        created_by=user,
        is_deleted=False
    ).select_related('created_by').order_by('-reminder_date')
    
    context = {
        "user": user,
        'reminders': reminders,
        'key': "all"
    }
    
    return render(request, 'reminder/viewReminder.html', context)


# ============================================================================
# Reminder Cancellation
# ============================================================================

@login_required
def cancel_reminder(request: HttpRequest, id: int) -> HttpResponse:
    """
    Cancel (soft delete) a reminder.
    
    Args:
        request: HTTP request
        id: Reminder ID
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    
    try:
        reminder = Reminder.objects.filter(
            created_by=user,
            id=id,
            is_deleted=False
        ).first()
        
        if not reminder:
            messages.error(request, "Reminder not found")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
        # Soft delete
        reminder.is_deleted = True
        reminder.save()
        
        messages.success(request, f"Reminder '{reminder.title}' cancelled")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, "An unexpected error occurred")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_reminder(user) -> List[Reminder]:
    """
    Calculate which reminders are due today based on frequency patterns.
    
    Frequency Logic:
        - Daily: Always included if reminder_date <= today
        - Monthly: Included if day of month matches
        - Yearly: Included if month and day match
        - Custom: Included if (today - reminder_date) is divisible by custom_repeat_days
    
    Args:
        user: Django user object
        
    Returns:
        List[Reminder]: Reminders due today
        
    Example:
        Daily reminder from Jan 1 → shows every day
        Monthly reminder from Jan 15 → shows on 15th of each month
        Yearly reminder from Jan 15 → shows on Jan 15 each year
        Custom (7 days) from Jan 1 → shows on Jan 1, 8, 15, 22, 29, etc.
    """
    today = date.today()
    current_month = today.month
    current_day = today.day
    
    # Get all active reminders on or before today
    all_reminders_query = Reminder.objects.filter(
        created_by=user,
        reminder_date__lte=today,
        is_deleted=False
    ).select_related('created_by')
    
    active_today = []
    
    for reminder in all_reminders_query:
        # Skip future reminders (shouldn't happen due to filter, but safety check)
        if reminder.reminder_date > today:
            continue
        
        # Daily reminders: always active
        if reminder.frequency == Reminder.DAILY:
            active_today.append(reminder)
        
        # Monthly reminders: active if day matches
        elif reminder.frequency == Reminder.MONTHLY:
            if reminder.reminder_date.day == current_day:
                active_today.append(reminder)
        
        # Yearly reminders: active if month and day match
        elif reminder.frequency == Reminder.YEARLY:
            if (reminder.reminder_date.day == current_day and
                reminder.reminder_date.month == current_month):
                active_today.append(reminder)
        
        # Custom reminders: active if days elapsed is divisible by custom interval
        elif reminder.frequency == Reminder.CUSTOM:
            if reminder.custom_repeat_days:
                days_elapsed = (today - reminder.reminder_date).days
                
                # Check if today is a repeat day
                if days_elapsed >= 0 and days_elapsed % reminder.custom_repeat_days == 0:
                    active_today.append(reminder)
    
    return active_today