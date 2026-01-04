"""
Enhanced Task Management Models

This module contains all task-related models with improved features for
real-world, day-to-day to-do list management.

Features:
- Task categorization with categories/projects
- Flexible tagging system
- Recurring task patterns
- Task templates for quick creation
- Subtask support with hierarchical structure
- Time tracking and estimates
- Priority scoring
- Task attachments and notes
"""

from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TaskCategory(models.Model):
    """
    Categories for organizing tasks (e.g., Work, Personal, Health, Finance).
    
    A category represents a major area of life or work, helping users organize
    tasks into meaningful groups.
    """
    
    name = models.CharField(
        max_length=100,
        help_text=_("Category name (e.g., 'Work', 'Personal', 'Health')")
    )
    color = models.CharField(
        max_length=7,
        default='#6c757d',
        help_text=_("Hex color code for visual identification (e.g., '#3B82F6')")
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Font Awesome icon class (e.g., 'fa-briefcase')")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Optional description of this category")
    )
    
    # User association
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='task_categories'
    )
    
    # Order for display
    display_order = models.IntegerField(
        default=0,
        help_text=_("Order in which categories appear (lower first)")
    )
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Task Category")
        verbose_name_plural = _("Task Categories")
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['created_by', 'is_deleted']),
            models.Index(fields=['display_order']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['created_by', 'name'],
                condition=models.Q(is_deleted=False),
                name='unique_category_per_user'
            )
        ]
    
    def __str__(self):
        return self.name
    
    def get_task_count(self):
        """Return count of active tasks in this category."""
        return self.tasks.filter(is_deleted=False).count()


class TaskTag(models.Model):
    """
    Flexible tags for cross-cutting task organization.
    
    Tags allow users to label tasks with keywords for flexible filtering
    (e.g., 'urgent', 'waiting-on-others', 'quick-win').
    """
    
    name = models.CharField(
        max_length=50,
        help_text=_("Tag name (e.g., 'urgent', 'waiting', 'quick-win')")
    )
    color = models.CharField(
        max_length=7,
        default='#6c757d',
        help_text=_("Hex color code for tag chip display")
    )
    
    # User association
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='task_tags'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Task Tag")
        verbose_name_plural = _("Task Tags")
        ordering = ['name']
        indexes = [
            models.Index(fields=['created_by']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['created_by', 'name'],
                name='unique_tag_per_user'
            )
        ]
    
    def __str__(self):
        return self.name
    
    def get_task_count(self):
        """Return count of active tasks with this tag."""
        return self.tasks.filter(is_deleted=False).count()


class RecurringPattern(models.Model):
    """
    Defines how a task should recur over time.
    
    Supports various recurrence patterns for automating routine tasks.
    """
    
    FREQUENCY_CHOICES = [
        ('DAILY', _('Daily')),
        ('WEEKLY', _('Weekly')),
        ('MONTHLY', _('Monthly')),
        ('YEARLY', _('Yearly')),
        ('CUSTOM', _('Custom (days)')),
    ]
    
    WEEKDAY_CHOICES = [
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday')),
    ]
    
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        help_text=_("How often the task repeats")
    )
    interval = models.IntegerField(
        default=1,
        help_text=_("Repeat every X days/weeks/months/years (e.g., every 2 weeks)")
    )
    
    # For weekly recurrence
    weekdays = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of weekday numbers for weekly recurrence (0=Monday, 6=Sunday)")
    )
    
    # For monthly recurrence
    day_of_month = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Day of month (1-31) for monthly recurrence")
    )
    
    # For custom frequency (in days)
    custom_days = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Number of days for custom recurrence pattern")
    )
    
    # End date for recurrence (optional)
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("When to stop creating recurring tasks (optional)")
    )
    
    # Maximum occurrences (alternative to end_date)
    max_occurrences = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum number of task instances to create (optional)")
    )
    
    class Meta:
        verbose_name = _("Recurring Pattern")
        verbose_name_plural = _("Recurring Patterns")
    
    def __str__(self):
        if self.frequency == 'CUSTOM' and self.custom_days:
            return f"Every {self.custom_days} days"
        return f"{self.get_frequency_display()} (every {self.interval})"
    
    def clean(self):
        """Validate recurring pattern configuration."""
        if self.frequency == 'WEEKLY' and not self.weekdays:
            raise ValidationError(_("Weekly recurrence requires at least one weekday"))
        if self.frequency == 'MONTHLY' and not self.day_of_month:
            raise ValidationError(_("Monthly recurrence requires a day of month"))
        if self.frequency == 'CUSTOM' and not self.custom_days:
            raise ValidationError(_("Custom recurrence requires number of days"))


class Task(models.Model):
    """
    Enhanced Task model with comprehensive features for day-to-day task management.
    
    Core entity for managing to-do items with support for categorization,
    tagging, subtasks, recurring patterns, time tracking, and more.
    """
    
    PRIORITY_CHOICES = [
        ('Low', _('Low')),
        ('Medium', _('Medium')),
        ('High', _('High')),
    ]
    
    STATUS_CHOICES = [
        ('Pending', _('Pending')),
        ('In Progress', _('In Progress')),
        ('Completed', _('Completed')),
        ('Cancelled', _('Cancelled')),
    ]
    
    # Basic Information
    name = models.CharField(
        max_length=200,
        help_text=_("Task title/name")
    )
    description = models.TextField(
        max_length=1000,
        blank=True,
        help_text=_("Detailed task description")
    )
    
    # Categorization & Organization
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text=_("Category/project this task belongs to")
    )
    tags = models.ManyToManyField(
        TaskTag,
        blank=True,
        related_name='tasks',
        help_text=_("Tags for flexible categorization")
    )
    
    # Priority & Status
    priority = models.CharField(
        max_length=50,
        choices=PRIORITY_CHOICES,
        default='Medium',
        help_text=_("Task priority level")
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Pending',
        help_text=_("Current task status")
    )
    
    # Calculated priority score based on urgency and importance
    priority_score = models.IntegerField(
        default=0,
        help_text=_("Auto-calculated priority score for smart sorting")
    )
    
    # Dates & Deadlines
    complete_by_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Due date for task completion")
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("When to start working on this task")
    )
    completed_on = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("When the task was completed")
    )
    
    # Hierarchical Structure (Subtasks)
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks',
        help_text=_("Parent task if this is a subtask")
    )
    
    # Recurring Task Support
    is_recurring = models.BooleanField(
        default=False,
        help_text=_("Whether this task repeats on a schedule")
    )
    recurring_pattern = models.ForeignKey(
        RecurringPattern,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text=_("Recurrence pattern for this task")
    )
    recurring_parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='recurring_instances',
        help_text=_("Original task if this is a recurring instance")
    )
    next_occurrence_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Next date when a recurring instance will be created")
    )
    occurrence_count = models.IntegerField(
        default=0,
        help_text=_("Number of times this recurring task has been generated")
    )
    
    # Time Tracking
    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Estimated time to complete (in hours)")
    )
    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text=_("Actual time spent on task (in hours)")
    )
    
    # Reminders
    reminder_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When to send a reminder notification")
    )
    reminder_sent = models.BooleanField(
        default=False,
        help_text=_("Whether reminder has been sent")
    )
    
    # Notes & Additional Context
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes, updates, or context")
    )
    
    # Display Order (for manual sorting)
    position = models.IntegerField(
        default=0,
        help_text=_("Manual sort order within a category or list")
    )
    
    # Soft Delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    # User Association
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        ordering = ['-priority_score', 'complete_by_date', 'position']
        indexes = [
            models.Index(fields=['created_by', 'is_deleted']),
            models.Index(fields=['status']),
            models.Index(fields=['complete_by_date']),
            models.Index(fields=['priority_score']),
            models.Index(fields=['is_recurring']),
            models.Index(fields=['parent_task']),
            # Composite indexes for common queries
            models.Index(fields=['created_by', 'is_deleted', 'status']),
            models.Index(fields=['created_by', 'is_deleted', 'complete_by_date']),
            models.Index(fields=['category', 'is_deleted']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate priority score."""
        self.calculate_priority_score()
        super().save(*args, **kwargs)
    
    def calculate_priority_score(self):
        """
        Calculate priority score based on priority level and due date urgency.
        
        Score calculation:
        - Priority: High=30, Medium=20, Low=10
        - Due date urgency: adds 0-40 points based on how soon it's due
        - Overdue tasks get maximum urgency bonus
        """
        # Base score from priority
        priority_scores = {'High': 30, 'Medium': 20, 'Low': 10}
        score = priority_scores.get(self.priority, 20)
        
        # Add urgency based on due date
        if self.complete_by_date:
            today = timezone.now().date()
            days_until_due = (self.complete_by_date - today).days
            
            if days_until_due < 0:
                # Overdue - maximum urgency
                score += 40
            elif days_until_due == 0:
                # Due today
                score += 35
            elif days_until_due == 1:
                # Due tomorrow
                score += 30
            elif days_until_due <= 3:
                # Due within 3 days
                score += 25
            elif days_until_due <= 7:
                # Due within a week
                score += 15
            elif days_until_due <= 14:
                # Due within 2 weeks
                score += 10
            # else: far in future, no urgency bonus
        
        self.priority_score = score
    
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.complete_by_date:
            return False
        return self.complete_by_date < timezone.now().date() and self.status != 'Completed'
    
    def get_progress_percentage(self) -> float:
        """
        Calculate completion percentage based on subtasks.
        
        Returns:
            float: Percentage of subtasks completed (0-100)
        """
        subtasks = self.subtasks.filter(is_deleted=False)
        if not subtasks.exists():
            return 100.0 if self.status == 'Completed' else 0.0
        
        completed = subtasks.filter(status='Completed').count()
        total = subtasks.count()
        return (completed / total) * 100 if total > 0 else 0.0
    
    def mark_complete(self):
        """Mark task as completed with timestamp."""
        self.status = 'Completed'
        self.completed_on = timezone.now()
        self.save()
        
        # If this is a recurring task, create next instance
        if self.is_recurring and self.recurring_pattern:
            self.create_next_occurrence()
    
    def create_next_occurrence(self):
        """Create the next instance of a recurring task."""
        if not self.recurring_pattern:
            return
        
        pattern = self.recurring_pattern
        
        # Check if we've reached max occurrences
        if pattern.max_occurrences and self.occurrence_count >= pattern.max_occurrences:
            return
        
        # Calculate next due date based on pattern
        next_date = self._calculate_next_date(pattern)
        
        if not next_date:
            return
        
        # Check if we've passed end date
        if pattern.end_date and next_date > pattern.end_date:
            return
        
        # Create new task instance
        new_task = Task.objects.create(
            name=self.name,
            description=self.description,
            category=self.category,
            priority=self.priority,
            complete_by_date=next_date,
            start_date=next_date - timedelta(days=1) if self.start_date else None,
            is_recurring=True,
            recurring_pattern=pattern,
            recurring_parent=self.recurring_parent or self,
            estimated_hours=self.estimated_hours,
            created_by=self.created_by,
            occurrence_count=self.occurrence_count + 1,
        )
        
        # Copy tags
        new_task.tags.set(self.tags.all())
        
        return new_task
    
    def _calculate_next_date(self, pattern: RecurringPattern) -> Optional[timezone.datetime]:
        """Calculate the next occurrence date based on recurring pattern."""
        if not self.complete_by_date:
            return None
        
        current_date = self.complete_by_date
        
        if pattern.frequency == 'DAILY':
            return current_date + timedelta(days=pattern.interval)
        
        elif pattern.frequency == 'WEEKLY':
            # Move to next occurrence of specified weekday(s)
            next_date = current_date + timedelta(days=1)
            days_checked = 0
            while days_checked < 7 * pattern.interval:
                if next_date.weekday() in pattern.weekdays:
                    return next_date
                next_date += timedelta(days=1)
                days_checked += 1
        
        elif pattern.frequency == 'MONTHLY':
            # Add months
            month = current_date.month + pattern.interval
            year = current_date.year
            while month > 12:
                month -= 12
                year += 1
            
            # Use specified day of month or last day
            day = pattern.day_of_month or current_date.day
            try:
                return current_date.replace(year=year, month=month, day=day)
            except ValueError:
                # Handle invalid dates (e.g., Feb 30)
                return current_date.replace(year=year, month=month, day=28)
        
        elif pattern.frequency == 'YEARLY':
            return current_date.replace(year=current_date.year + pattern.interval)
        
        elif pattern.frequency == 'CUSTOM' and pattern.custom_days:
            return current_date + timedelta(days=pattern.custom_days)
        
        return None


class TaskTemplate(models.Model):
    """
    Templates for quickly creating commonly-used tasks.
    
    Allows users to save task configurations (with subtasks and tags) for
    easy reuse, speeding up task creation for routine workflows.
    """
    
    name = models.CharField(
        max_length=200,
        help_text=_("Template name for identification")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Template description")
    )
    
    # Default task properties
    task_title_template = models.CharField(
        max_length=200,
        help_text=_("Default task title (can include placeholders like {date})")
    )
    task_description_template = models.TextField(
        blank=True,
        help_text=_("Default task description")
    )
    default_priority = models.CharField(
        max_length=50,
        choices=Task.PRIORITY_CHOICES,
        default='Medium'
    )
    default_category = models.ForeignKey(
        TaskCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates'
    )
    default_tags = models.ManyToManyField(
        TaskTag,
        blank=True,
        related_name='templates'
    )
    default_estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Days offset for due date
    days_until_due = models.IntegerField(
        default=7,
        help_text=_("Number of days from creation until due date")
    )
    
    # Template for subtasks (stored as JSON)
    subtask_templates = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of subtask names to create with this template")
    )
    
    # User association
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='task_templates'
    )
    
    # Usage tracking
    use_count = models.IntegerField(
        default=0,
        help_text=_("Number of times this template has been used")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Task Template")
        verbose_name_plural = _("Task Templates")
        ordering = ['-use_count', 'name']
        indexes = [
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return self.name
    
    def create_task_from_template(self, custom_title: str = None) -> Task:
        """
        Create a new task from this template.
        
        Args:
            custom_title: Optional custom title to override template title
        
        Returns:
            Created Task instance
        """
        # Calculate due date
        due_date = timezone.now().date() + timedelta(days=self.days_until_due)
        
        # Create main task
        task = Task.objects.create(
            name=custom_title or self.task_title_template.format(
                date=timezone.now().strftime('%Y-%m-%d')
            ),
            description=self.task_description_template,
            priority=self.default_priority,
            category=self.default_category,
            complete_by_date=due_date,
            estimated_hours=self.default_estimated_hours,
            created_by=self.created_by,
        )
        
        # Add tags
        task.tags.set(self.default_tags.all())
        
        # Create subtasks
        for subtask_name in self.subtask_templates:
            Task.objects.create(
                name=subtask_name,
                parent_task=task,
                priority=self.default_priority,
                category=self.default_category,
                complete_by_date=due_date,
                created_by=self.created_by,
            )
        
        # Increment use count
        self.use_count += 1
        self.save()
        
        return task


class TimeLog(models.Model):
    """
    Track time spent on tasks in detailed increments.
    
    Allows users to log work sessions for accurate time tracking and
    productivity analysis.
    """
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='time_logs',
        help_text=_("Task this time entry is for")
    )
    
    start_time = models.DateTimeField(
        help_text=_("When work started")
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When work ended (null if timer is running)")
    )
    
    duration_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text=_("Calculated duration in hours")
    )
    
    notes = models.TextField(
        blank=True,
        help_text=_("Notes about what was accomplished")
    )
    
    # User who logged the time
    logged_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='time_logs'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Time Log")
        verbose_name_plural = _("Time Logs")
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['task']),
            models.Index(fields=['logged_by']),
            models.Index(fields=['start_time']),
        ]
    
    def __str__(self):
        return f"{self.task.name} - {self.duration_hours}h"
    
    def save(self, *args, **kwargs):
        """Calculate duration before saving."""
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            self.duration_hours = round(duration.total_seconds() / 3600, 2)
        super().save(*args, **kwargs)
        
        # Update task's actual hours
        self.update_task_hours()
    
    def update_task_hours(self):
        """Update the parent task's actual hours."""
        total_hours = self.task.time_logs.aggregate(
            total=models.Sum('duration_hours')
        )['total'] or 0
        
        self.task.actual_hours = total_hours
        self.task.save()
    
    def stop_timer(self):
        """Stop the running timer and calculate duration."""
        if not self.end_time:
            self.end_time = timezone.now()
            self.save()


class TaskAttachment(models.Model):
    """
    File attachments for tasks.
    
    Links tasks to documents from the document management system or
    stores references to external files.
    """
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='attachments',
        help_text=_("Task this attachment belongs to")
    )
    
    # Reference to UploadedFile model (if using document manager)
    uploaded_file = models.ForeignKey(
        'UploadedFile',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=_("Reference to file in document manager")
    )
    
    # Alternative: external URL
    external_url = models.URLField(
        blank=True,
        help_text=_("External link (e.g., Google Drive, Dropbox)")
    )
    
    # Display name
    name = models.CharField(
        max_length=255,
        help_text=_("Attachment name for display")
    )
    
    notes = models.TextField(
        blank=True,
        help_text=_("Notes about this attachment")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Task Attachment")
        verbose_name_plural = _("Task Attachments")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task']),
        ]
    
    def __str__(self):
        return f"{self.task.name} - {self.name}"
