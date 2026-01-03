from django.contrib import admin
from .models import (
    User,
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
    list_display = ['title', 'key', 'access_type', 'is_active', 'display_order']
    list_filter = ['is_active', 'access_type']
    search_fields = ['title', 'key', 'description']
    list_editable = ['is_active', 'display_order']
    ordering = ['display_order', 'title']

    fieldsets = (
        ('Module Identity', {
            'fields': ('key', 'title', 'icon')
        }),
        ('UI Configuration', {
            'fields': ('description', 'url_pattern', 'display_order')
        }),
        ('Access Control', {
            'fields': ('access_type', 'allowed_users', 'is_active')
        }),
    )


# Register the rest of the models with simpler admin interface
admin.site.register(User)
admin.site.register(FinancialProduct)
admin.site.register(Transaction)
admin.site.register(Task)
admin.site.register(LedgerTransaction)
admin.site.register(Reminder)
admin.site.register(RefreshToken)
admin.site.register(UploadedFile)
