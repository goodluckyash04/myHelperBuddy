"""
Task Management Views

Handles task creation, listing, editing, and status management.

Features:
- Task creation with priority and due dates
- Task listing with status-based sorting
- Update task details
- Status management (pending/completed)
- Soft delete with restore functionality
- Hard delete support
"""

from typing import Optional

from django.contrib.auth.decorators import login_required
from django.db.models import F, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from accounts.models import Task, TaskCategory, TaskTag


# ============================================================================
# Helper Functions
# ============================================================================

def get_task_data_by_user(user) -> QuerySet:
    """
    Get all tasks for a user, ordered by status and due date.
    
    Ordering:
        - Pending tasks first (status='Pending')
        - Then by completion date (earliest first)
    
    Args:
        user: Django user object
        
    Returns:
        QuerySet: User's tasks ordered appropriately
    """
    return Task.objects.filter(
        created_by=user
    ).select_related('created_by').order_by(
        F('status').desc(),  # Pending before Completed
        'complete_by_date'
    )


def get_task_by_id(task_id: int) -> Task:
    """
    Get task by ID or raise 404.
    
    Args:
        task_id: Task primary key
        
    Returns:
        Task: Task object
        
    Raises:
        Http404: If task not found
    """
    return get_object_or_404(Task, id=task_id)


# ============================================================================
# Task Creation
# ============================================================================

@login_required
def addTask(request: HttpRequest) -> HttpResponse:
    """
    Create a new task.
    
    Required POST fields:
        - priority: Task priority level
        - name: Task name/title
        - complete_by_date: Due date (YYYY-MM-DD)
        - description: Task description
    
    Args:
        request: HTTP POST request with task details
        
    Returns:
        HttpResponse: Redirect to previous page
    """
    user = request.user
    
    if request.method != "POST":
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    task_data = request.POST
    
    # Import datetime for date parsing
    from datetime import datetime
    
    # Get and parse dates - convert string to date object
    complete_by_date = task_data.get("complete_by_date")
    if complete_by_date:
        try:
            complete_by_date = datetime.strptime(complete_by_date, "%Y-%m-%d").date()
        except ValueError:
            complete_by_date = None
    else:
        complete_by_date = None
    
    start_date = task_data.get("start_date")
    if start_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            start_date = None
    else:
        start_date = None
    
    estimated_hours = task_data.get("estimated_hours") or None
    category_id = task_data.get("category") or None
    
    # Get category object if provided
    category = None
    if category_id:
        try:
            category = TaskCategory.objects.get(id=category_id, created_by=user)
        except TaskCategory.DoesNotExist:
            category = None
    
    # Create task (priority_score will be auto-calculated on save)
    task = Task.objects.create(
        priority=task_data.get("priority", "Medium"),
        name=task_data.get("name", ""),
        complete_by_date=complete_by_date,
        start_date=start_date,
        description=task_data.get("description", ""),
        estimated_hours=estimated_hours,
        status=task_data.get("status", "Pending"),
        category=category,
        created_by=user
    )
    
    # Handle tags (many-to-many relationship)
    tag_ids = request.POST.getlist("tags")
    if tag_ids:
        tags = TaskTag.objects.filter(id__in=tag_ids, created_by=user)
        task.tags.set(tags)
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# ============================================================================
# Task Listing
# ============================================================================

@login_required
def currentMonthTaskReport(request: HttpRequest) -> HttpResponse:
    """
    Display pending tasks due this month or earlier.
    
    Filters:
        - User's tasks only
        - Due date <= current month
        - Status = Pending
        - Not deleted
    
    Args:
        request: HTTP GET request
        
    Returns:
        HttpResponse: Rendered tasks page
    """
    user = request.user
    current_month = timezone.now().month
    
    tasks = Task.objects.filter(
        created_by=user,
        complete_by_date__month__lte=current_month,
        status="Pending",
        is_deleted=False
    ).select_related('created_by').order_by('complete_by_date')
    
    # Get user's categories and tags for modal
    categories = TaskCategory.objects.filter(created_by=user, is_deleted=False).order_by('display_order', 'name')
    tags = TaskTag.objects.filter(created_by=user).order_by('name')
    
    context = {
        "user": user,
        "taskData": tasks,
        "categories": categories,
        "tags": tags
    }
    
    return render(request, "task/tasks.html", context)


@login_required
def taskReports(request: HttpRequest) -> HttpResponse:
    """
    Display all tasks with status-based filtering.
    
    Shows all tasks ordered by:
        - Status (Pending first, then Completed)
        - Due date (earliest first)
    
    Args:
        request: HTTP GET request
        
    Returns:
        HttpResponse: Rendered task report page
    """
    user = request.user
    
    tasks = Task.objects.filter(
        created_by=user
    ).select_related('created_by').order_by(
        F('status').desc(),
        'complete_by_date'
    )
    
    # Get user's categories and tags for modal
    categories = TaskCategory.objects.filter(created_by=user, is_deleted=False).order_by('display_order', 'name')
    tags = TaskTag.objects.filter(created_by=user).order_by('name')
    
    context = {
        'user': user,
        'taskData': tasks,
        'categories': categories,
        'tags': tags
    }
    
    return render(request, 'task/taskReport.html', context)


# ============================================================================
# Task Update
# ============================================================================

@login_required
def editTask(request: HttpRequest, id: int) -> HttpResponse:
    """
    Update task details.
    
    GET: Returns task details as JSON
    POST: Updates task fields
    
    Args:
        request: HTTP request (GET or POST)
        id: Task ID
        
    Returns:
        HttpResponse: JSON response (GET) or redirect (POST)
    """
    task = get_object_or_404(Task, id=id)
    
    # GET: Return task details
    if request.method == "GET":
        task_dict = {
            'id': task.id,
            'priority': task.priority,
            'name': task.name,
            'complete_by_date': str(task.complete_by_date) if task.complete_by_date else "",
            'start_date': str(task.start_date) if task.start_date else "",
            'description': task.description,
            'estimated_hours': float(task.estimated_hours) if task.estimated_hours else None,
            'status': task.status,
            'category': task.category.id if task.category else None,
            'tags': list(task.tags.values_list('id', flat=True))
        }
        return JsonResponse(task_dict)
    
    # POST: Update task
    user = request.user
    task_data = request.POST
    
    # Update basic fields
    task.priority = task_data.get("priority", task.priority)
    task.name = task_data.get("name", task.name)
    task.description = task_data.get("description", task.description)
    task.status = task_data.get("status", task.status)
    
    # Update dates - convert string to date object
    from datetime import datetime
    
    complete_by_date = task_data.get("complete_by_date")
    if complete_by_date:
        try:
            # Parse the date string to a date object
            task.complete_by_date = datetime.strptime(complete_by_date, "%Y-%m-%d").date()
        except ValueError:
            pass  # Keep existing date if parsing fails
    
    start_date = task_data.get("start_date")
    if start_date:
        try:
            task.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    
    # Update estimated hours
    estimated_hours = task_data.get("estimated_hours")
    if estimated_hours:
        task.estimated_hours = estimated_hours
    
    # Update category
    category_id = task_data.get("category")
    if category_id:
        try:
            task.category = TaskCategory.objects.get(id=category_id, created_by=user)
        except TaskCategory.DoesNotExist:
            pass
    else:
        task.category = None
    
    task.save()
    
    # Handle tags (many-to-many relationship)
    tag_ids = request.POST.getlist("tags")
    if tag_ids:
        tags = TaskTag.objects.filter(id__in=tag_ids, created_by=user)
        task.tags.set(tags)
    else:
        task.tags.clear()
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# ============================================================================
# Task Actions
# ============================================================================

@login_required
def taskAction(request: HttpRequest, id: int, action: str) -> HttpResponse:
    """
    Perform action on a task (complete, incomplete, delete, permanent delete).
    
    Actions:
        - 'complete': Mark task as completed
        - 'incomplete': Mark task as pending (restore from completed)
        - 'delete': Soft delete task
        - 'permdeletetask': Permanently delete task (hard delete)
    
    Args:
        request: HTTP request
        id: Task ID
        action: Action to perform
        
    Returns:
        HttpResponse: Redirect to previous page
    """
    task = get_task_by_id(id)
    
    # Perform action
    if action == 'complete':
        task.completed_on = timezone.now()
        task.status = "Completed"
    
    elif action == 'incomplete':
        task.completed_on = None
        task.status = "Pending"
        task.is_deleted = False
        task.deleted_at = None
    
    elif action == 'delete':
        task.is_deleted = True
        task.deleted_at = timezone.now()
    
    # Save changes (for all actions except permanent delete)
    task.save()
    
    # Permanent delete (hard delete from database)
    if action == "permdeletetask":
        task.delete()
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
