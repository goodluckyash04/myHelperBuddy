"""
Module Registry Service - Centralized module management with caching
"""
from typing import List, Dict, Optional
from django.core.cache import cache
from django.conf import settings


class ModuleRegistryService:
    """Service for managing and retrieving utility modules"""
    
    CACHE_KEY = "utility_modules_registry"
    CACHE_TIMEOUT = 3600  # 1 hour
    
    @classmethod
    def get_all_modules(cls, force_refresh=False):
        """Get all active modules (cached for performance)"""
        if not force_refresh:
            cached = cache.get(cls.CACHE_KEY)
            if cached is not None:
                return cached
        
        # Import here to avoid circular imports
        from accounts.models import UtilityModule
        
        modules = list(UtilityModule.objects.filter(is_active=True).order_by('display_order', 'title'))
        cache.set(cls.CACHE_KEY, modules, cls.CACHE_TIMEOUT)
        return modules
    
    @classmethod
    def get_modules_for_user(cls, user) -> List[Dict]:
        """Get modules accessible to a specific user"""
        all_modules = cls.get_all_modules()
        
        accessible_modules = [
            {
                'title': module.title,
                'description': module.description,
                'url': module.url_pattern,
                'icon': module.icon,
                'key': module.key,
            }
            for module in all_modules
            if module.has_access(user)
        ]
        
        return accessible_modules
    
    @classmethod
    def register_module(cls, **kwargs):
        """Register or update a module"""
        from accounts.models import UtilityModule
        
        key = kwargs.get('key')
        if not key:
            raise ValueError("Module key is required")
        
        module, created = UtilityModule.objects.update_or_create(
            key=key,
            defaults=kwargs
        )
        cls.clear_cache()
        return module
    
    @classmethod
    def clear_cache(cls):
        """Clear module cache"""
        cache.delete(cls.CACHE_KEY)
    
    @classmethod
    def seed_default_modules(cls):
        """Seed database with current modules from settings"""
        
        # Note: User assignments should be done via Django admin or management commands
        # This just creates the modules with basic configuration
        default_modules = [
            {
                'key': 'TRANSACTION',
                'title': 'TRANSACTION',
                'description': 'Manage Your Money Moves, One Day at a Time!',
                'url_pattern': '/transaction-detail/',
                'icon': 'fa-credit-card',
                'display_order': 1,
                'access_type': 'PUBLIC',  # Default to PUBLIC, configure users in admin
            },
            {
                'key': 'FINANCE',
                'title': 'FINANCE',
                'description': 'Track Your Loans and Sips, No Slips!',
                'url_pattern': '/finance-details/',
                'icon': 'fa-wallet',
                'display_order': 2,
                'access_type': 'PUBLIC',
            },
            {
                'key': 'LEDGER',
                'title': 'LEDGER',
                'description': 'Balance Your Payables and Receivables with Ease!',
                'url_pattern': '/ledger-transaction-details/',
                'icon': 'fa-book',
                'display_order': 3,
                'access_type': 'PUBLIC',
            },
            {
                'key': 'TASK',
                'title': 'TASK',
                'description': 'Give Your Brain a Break, We\'ve Got Your To-Dos Covered!',
                'url_pattern': '/currentMonthTaskReport/',
                'icon': 'fa-check-circle',
                'display_order': 4,
                'access_type': 'PUBLIC',
            },
            {
                'key': 'REMINDER',
                'title': 'REMINDER',
                'description': 'Never Miss a Moment, Let the Reminders Handle it All!',
                'url_pattern': '/view-today-reminder/',
                'icon': 'fa-bell',
                'display_order': 5,
                'access_type': 'PUBLIC',
            },
            {
                'key': 'DOCUMENT_MANAGER',
                'title': 'DOCUMENT MANAGER',
                'description': 'The Right File, Right Now. Never Search Again.',
                'url_pattern': '/fetch-documents/',
                'icon': 'fa-file',
                'display_order': 6,
                'access_type': 'PUBLIC',
            },
            {
                'key': 'OTHER_UTILITIES',
                'title': 'ADVANCE UTILITIES',
                'description': 'Access and manage advanced utility tools integrated with your account.',
                'url_pattern': '/advance-utils/',
                'icon': 'fa-tools',
                'display_order': 7,
                'access_type': 'ADMIN',  # Admin only by default
            },
        ]
        
        for module_data in default_modules:
            cls.register_module(**module_data)


# Create a singleton instance for convenience
module_registry = ModuleRegistryService()
