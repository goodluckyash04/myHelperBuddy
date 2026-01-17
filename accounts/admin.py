from django.contrib import admin
from .models import (
    FinancialProduct,
    Transaction,
    Task,
    TaskCategory,
    TaskTag,
    TaskTemplate,
    RecurringPattern,
    TimeLog,
    TaskAttachment,
    LedgerTransaction,
    PaymentRecord,
    Reminder,
    RefreshToken,
    UploadedFile,
    UtilityModule
)


# ============================================================================
# Utility Module Admin
# ============================================================================

@admin.register(UtilityModule)
class UtilityModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'key', 'access_type', 'is_active', 'show_on_landing', 'display_order', 'get_user_count']
    list_filter = ['is_active', 'access_type', 'show_on_landing']
    search_fields = ['title', 'key', 'description']
    list_editable = ['is_active', 'show_on_landing', 'display_order']
    ordering = ['display_order', 'title']
    filter_horizontal = ('allowed_users_list',)  # Nice multi-select widget
    
    fieldsets = (
        ('Module Identity', {
            'fields': ('key', 'title', 'icon')
        }),
        ('UI Configuration', {
            'fields': ('description', 'url_pattern', 'display_order')
        }),
        ('Access Control', {
            'fields': ('access_type', 'is_active', 'show_on_landing'),
            'description': 'Choose access type, then configure users below'
        }),
        ('Landing Page Content (if show_on_landing is True)', {
            'fields': ('landing_title', 'landing_description'),
            'description': 'Custom title and description for landing page (optional - uses main title/description if blank)'
        }),
        ('User Selection (for CONFIG access type)', {
            'fields': ('allowed_users_list',),
            'description': 'Select specific users from the list below'
        }),
    )
    
    def get_user_count(self, obj):
        """Show number of selected users in list view"""
        if obj.access_type == 'PUBLIC':
            return 'All (Public)'
        elif obj.access_type == 'ADMIN':
            return 'Admin Only'
        else:
            count = obj.allowed_users_list.count()
            return f'{count} user(s)' if count > 0 else 'None'
    get_user_count.short_description = 'Access'


# ============================================================================
# Task Management Admin Interfaces
# ============================================================================

@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'icon', 'created_by', 'display_order', 'get_task_count', 'is_deleted']
    list_filter = ['created_by', 'is_deleted']
    search_fields = ['name', 'description']
    list_editable = ['display_order', 'color']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Visual Settings', {
            'fields': ('color', 'icon', 'display_order'),
            'description': 'Color (hex code), Font Awesome icon class, and display order'
        }),
        ('Status', {
            'fields': ('is_deleted', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_task_count(self, obj):
        """Show number of tasks in this category"""
        if hasattr(obj, 'get_task_count'):
            return obj.get_task_count()
        return 0
    get_task_count.short_description = 'Tasks'


@admin.register(TaskTag)
class TaskTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'created_by', 'get_task_count']
    list_filter = ['created_by']
    search_fields = ['name']
    list_editable = ['color']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'created_by')
        }),
        ('Visual Settings', {
            'fields': ('color',),
            'description': 'Color for tag chip display (hex code)'
        }),
    )
    
    def get_task_count(self, obj):
        """Show number of tasks with this tag"""
        if hasattr(obj, 'get_task_count'):
            return obj.get_task_count()
        return 0
    get_task_count.short_description = 'Tasks'


@admin.register(RecurringPattern)
class RecurringPatternAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'frequency', 'interval', 'end_date', 'max_occurrences']
    list_filter = ['frequency']
    
    fieldsets = (
        ('Basic Recurrence', {
            'fields': ('frequency', 'interval')
        }),
        ('Weekly Settings', {
            'fields': ('weekdays',),
            'description': 'For weekly recurrence, specify weekdays (0=Monday, 6=Sunday)'
        }),
        ('Monthly Settings', {
            'fields': ('day_of_month',),
            'description': 'For monthly recurrence, specify day of month (1-31)'
        }),
        ('Custom Settings', {
            'fields': ('custom_days',),
            'description': 'For custom recurrence, specify number of days'
        }),
        ('Limits', {
            'fields': ('end_date', 'max_occurrences'),
            'description': 'Optional: set end date or max number of occurrences'
        }),
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'priority', 'status', 'complete_by_date', 
                   'priority_score', 'is_recurring', 'created_by', 'is_deleted']
    list_filter = ['status', 'priority', 'category', 'is_recurring', 'is_deleted', 'created_by']
    search_fields = ['name', 'description', 'notes']
    list_editable = ['status', 'priority']
    filter_horizontal = ['tags']
    date_hierarchy = 'complete_by_date'
    ordering = ['-priority_score', 'complete_by_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Organization', {
            'fields': ('category', 'tags'),
            'description': 'Categorize and tag your task'
        }),
        ('Priority & Status', {
            'fields': ('priority', 'status', 'priority_score'),
            'description': 'Priority score is auto-calculated'
        }),
        ('Dates & Deadlines', {
            'fields': ('start_date', 'complete_by_date', 'completed_on')
        }),
        ('Hierarchical Structure', {
            'fields': ('parent_task',),
            'classes': ('collapse',),
            'description': 'Set parent task to make this a subtask'
        }),
        ('Recurring Task', {
            'fields': ('is_recurring', 'recurring_pattern', 'recurring_parent', 
                      'next_occurrence_date', 'occurrence_count'),
            'classes': ('collapse',),
        }),
        ('Time Tracking', {
            'fields': ('estimated_hours', 'actual_hours'),
            'classes': ('collapse',),
        }),
        ('Reminders', {
            'fields': ('reminder_datetime', 'reminder_sent'),
            'classes': ('collapse',),
        }),
        ('Additional Info', {
            'fields': ('notes', 'position'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('is_deleted', 'deleted_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['priority_score', 'actual_hours', 'occurrence_count']


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'default_priority', 'default_category', 'use_count', 'created_by']
    list_filter = ['default_priority', 'default_category', 'created_by']
    search_fields = ['name', 'description', 'task_title_template']
    filter_horizontal = ['default_tags']
    ordering = ['-use_count', 'name']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Default Task Properties', {
            'fields': ('task_title_template', 'task_description_template', 
                      'default_priority', 'default_category', 'default_tags')
        }),
        ('Time & Scheduling', {
            'fields': ('days_until_due', 'default_estimated_hours')
        }),
        ('Subtasks', {
            'fields': ('subtask_templates',),
            'description': 'JSON list of subtask names, e.g., ["Step 1", "Step 2"]'
        }),
        ('Usage', {
            'fields': ('use_count',),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['use_count']


@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'start_time', 'end_time', 'duration_hours', 'logged_by']
    list_filter = ['logged_by', 'start_time']
    search_fields = ['task__name', 'notes']
    date_hierarchy = 'start_time'
    ordering = ['-start_time']
    
    fieldsets = (
        ('Time Entry', {
            'fields': ('task', 'logged_by')
        }),
        ('Time Tracking', {
            'fields': ('start_time', 'end_time', 'duration_hours'),
            'description': 'Duration is auto-calculated from start and end times'
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    readonly_fields = ['duration_hours']


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'task', 'uploaded_file', 'external_url', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'task__name', 'notes']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('task', 'name')
        }),
        ('File Reference', {
            'fields': ('uploaded_file', 'external_url'),
            'description': 'Either link to uploaded file or provide external URL'
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )


# ============================================================================
# Other Models - Simple Registration
# ============================================================================

admin.site.register(FinancialProduct)
admin.site.register(Transaction)
admin.site.register(LedgerTransaction)
admin.site.register(PaymentRecord)
admin.site.register(Reminder)
admin.site.register(RefreshToken)
admin.site.register(UploadedFile)
