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
    Create a new reminder with smart types and priority.
    
    Supports:
        - 7 reminder types (one-time, daily, weekly, monthly, custom, linked)
        - 4 priority levels (critical, high, medium, low)
        - Weekly patterns with weekday selection
        - Monthly patterns with day selection
        - Linked to tasks or finance products
    
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
    reminder_time_str = request.POST.get('reminder_time', '')
    
    # New fields
    reminder_type = request.POST.get('reminder_type', Reminder.ONE_TIME)
    priority = request.POST.get('priority', Reminder.MEDIUM)
    
    # Recurring pattern fields
    weekdays_list = request.POST.getlist('weekdays')  # For weekly
    month_days_list = request.POST.getlist('month_days')  # For monthly
    custom_repeat_days = request.POST.get('custom_repeat_days')
    
    # Linked items
    linked_task_id = request.POST.get('linked_task')
    linked_finance_id = request.POST.get('linked_finance')
    
    # Legacy support
    frequency = request.POST.get('frequency', Reminder.DAILY)
    
    # Validate required fields
    if not title or not reminder_date_str:
        messages.error(request, "Title and reminder date are required")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    try:
        # Parse dates
        reminder_date = timezone.datetime.strptime(reminder_date_str, "%Y-%m-%d").date()
        reminder_time = None
        if reminder_time_str:
            reminder_time = timezone.datetime.strptime(reminder_time_str, "%H:%M").time()
        
        # Process weekdays for weekly reminders
        weekdays = None
        if reminder_type == Reminder.WEEKLY and weekdays_list:
            weekdays = [int(day) for day in weekdays_list]
        
        # Process month days for monthly reminders
        month_days = None
        if reminder_type == Reminder.MONTHLY_TYPE and month_days_list:
            month_days = [int(day) for day in month_days_list]
        
        # Check for duplicate reminder
        existing_reminder = Reminder.objects.filter(
            title=title,
            reminder_date=reminder_date,
            created_by=user,
            is_deleted=False
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
            reminder_time=reminder_time,
            reminder_type=reminder_type,
            priority=priority,
            weekdays=weekdays,
            month_days=month_days,
            frequency=frequency,  # For backward compatibility
            custom_repeat_days=int(custom_repeat_days) if custom_repeat_days else None,
            linked_task_id=linked_task_id if linked_task_id else None,
            linked_finance_id=linked_finance_id if linked_finance_id else None,
            created_by=user
        )
        
        priority_icon = reminder.get_priority_icon()
        messages.success(request, f"{priority_icon} Reminder '{title}' added successfully")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except ValueError as e:
        messages.error(request, f"Invalid date format: {str(e)}")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def update_reminder(request: HttpRequest, id: int) -> HttpResponse:
    """Update an existing reminder."""
    user = request.user
    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    try:
        reminder = Reminder.objects.filter(created_by=user, id=id, is_deleted=False).first()
        if not reminder:
            messages.error(request, "Reminder not found")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        reminder_date_str = request.POST.get('reminder_date')
        reminder_time_str = request.POST.get('reminder_time', '')
        reminder_type = request.POST.get('reminder_type', Reminder.ONE_TIME)
        priority = request.POST.get('priority', Reminder.MEDIUM)
        weekdays_list = request.POST.getlist('weekdays')
        month_days_list = request.POST.getlist('month_days')
        custom_repeat_days = request.POST.get('custom_repeat_days')
        
        if not title or not reminder_date_str:
            messages.error(request, "Title and date are required")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
        reminder.title = title
        reminder.description = description
        reminder.reminder_date = timezone.datetime.strptime(reminder_date_str, "%Y-%m-%d").date()
        reminder.reminder_time = timezone.datetime.strptime(reminder_time_str, "%H:%M").time() if reminder_time_str else None
        reminder.reminder_type = reminder_type
        reminder.priority = priority
        reminder.weekdays = [int(day) for day in weekdays_list] if weekdays_list else None
        reminder.month_days = [int(day) for day in month_days_list] if month_days_list else None
        reminder.custom_repeat_days = int(custom_repeat_days) if custom_repeat_days else None
        reminder.is_snoozed = False
        reminder.snoozed_until = None
        reminder.is_dismissed = False
        reminder.dismissed_at = None
        reminder.save()
        
        messages.success(request, f"{reminder.get_priority_icon()} Reminder '{title}' updated successfully")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
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


@login_required
def snooze_reminder(request: HttpRequest, id: int, hours: int) -> HttpResponse:
    """
    Snooze a reminder for specified hours.
    
    Args:
        request: HTTP request
        id: Reminder ID
        hours: Number of hours to snooze
        
    Returns:
        HttpResponse: JSON response or redirect
    """
    user = request.user
    
    try:
        reminder = Reminder.objects.filter(
            created_by=user,
            id=id,
            is_deleted=False
        ).first()
        
        if not reminder or not reminder.can_snooze():
            messages.error(request, "Cannot snooze this reminder")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
        from django.utils import timezone
        from datetime import timedelta
        
        reminder.is_snoozed = True
        reminder.snoozed_until = timezone.now() + timedelta(hours=hours)
        reminder.save()
        
        messages.success(request, f"Reminder snoozed for {hours} hour(s)")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        messages.error(request, "An error occurred")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def dismiss_reminder(request: HttpRequest, id: int) -> HttpResponse:
    """
    Dismiss a reminder (mark as seen).
    
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
        
        from django.utils import timezone
        reminder.is_dismissed = True
        reminder.dismissed_at = timezone.now()
        reminder.save()
        
        messages.success(request, f"Reminder '{reminder.title}' dismissed")
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