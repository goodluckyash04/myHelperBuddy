from django.contrib import admin
from .models import (
    FinancialProduct,
    Transaction,
    Task,
    LedgerTransaction,
    Reminder,
    RefreshToken,
    UploadedFile,
    UtilityModule
)


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



# Register the rest of the models with simpler admin interface
admin.site.register(FinancialProduct)
admin.site.register(Transaction)
admin.site.register(Task)
admin.site.register(LedgerTransaction)
admin.site.register(Reminder)
admin.site.register(RefreshToken)
admin.site.register(UploadedFile)

