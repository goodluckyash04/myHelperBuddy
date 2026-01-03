"""
Module Registry Service - Centralized utility module management with caching.

This service manages the registration, retrieval, and access control
for application utility modules with performance optimization via caching.
"""

from typing import Dict, List, Optional

from django.conf import settings
from django.core.cache import cache


class ModuleRegistryService:
    """
    Service for managing and retrieving utility modules.
    
    Features:
        - Caching for performance (1-hour TTL)
        - User-based access control
        - Module registration and updates
        - Default module seeding
    """
    
    CACHE_KEY = "utility_modules_registry"
    CACHE_TIMEOUT = 3600  # 1 hour in seconds
    
    @classmethod
    def get_all_modules(cls, force_refresh: bool = False) -> List:
        """
        Get all active modules with caching for performance.
        
        Args:
            force_refresh: If True, bypass cache and fetch from database
            
        Returns:
            List of UtilityModule instances
            
        Example:
            >>> modules = ModuleRegistryService.get_all_modules()
            >>> for module in modules:
            ...     print(module.title)
        """
        if not force_refresh:
            cached = cache.get(cls.CACHE_KEY)
            if cached is not None:
                return cached
        
        # Import here to avoid circular imports
        from accounts.models import UtilityModule
        
        modules = list(
            UtilityModule.objects
            .filter(is_active=True)
            .order_by('display_order', 'title')
        )
        
        cache.set(cls.CACHE_KEY, modules, cls.CACHE_TIMEOUT)
        return modules
    
    @classmethod
    def get_modules_for_user(cls, user) -> List[Dict[str, str]]:
        """
        Get modules accessible to a specific user.
        
        Filters modules based on access control settings:
        - PUBLIC: Available to all users
        - CONFIG: Available to specific users
        - ADMIN: Available to superusers only
        
        Args:
            user: Django User instance
            
        Returns:
            List of module dictionaries with essential fields
            
        Example:
            >>> modules = ModuleRegistryService.get_modules_for_user(request.user)
            >>> for module in modules:
            ...     print(f"{module['title']}: {module['url']}")
        """
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
    def get_modules_for_landing(cls) -> List[Dict[str, str]]:
        """
        Get modules to display on landing page for non-authenticated users.
        
        Returns:
            List of module dictionaries for landing page display
        """
        all_modules = cls.get_all_modules()
        
        landing_modules = [
            {
                'title': module.landing_title or module.title,
                'description': module.landing_description or module.description,
                'url': module.url_pattern,
                'icon': module.icon,
                'key': module.key,
            }
            for module in all_modules
            if module.show_on_landing
        ]
        
        return landing_modules
    
    @classmethod
    def register_module(cls, **kwargs) -> 'UtilityModule':
        """
        Register or update a utility module.
        
        Args:
            **kwargs: Module fields (key, title, description, etc.)
            
        Returns:
            Created or updated UtilityModule instance
            
        Raises:
            ValueError: If module key is not provided
            
        Example:
            >>> module = ModuleRegistryService.register_module(
            ...     key='MY_MODULE',
            ...     title='My Module',
            ...     description='Module description',
            ...     url_pattern='/my-module/',
            ...     icon='fa-star',
            ...     display_order=1,
            ...     access_type='PUBLIC'
            ... )
        """
        from accounts.models import UtilityModule
        
        key = kwargs.get('key')
        if not key:
            raise ValueError("Module 'key' is required for registration")
        
        module, created = UtilityModule.objects.update_or_create(
            key=key,
            defaults=kwargs
        )
        
        # Clear cache to reflect changes immediately
        cls.clear_cache()
        
        return module
    
    @classmethod
    def deregister_module(cls, key: str) -> bool:
        """
        Deactivate a module by key.
        
        Args:
            key: Module key identifier
            
        Returns:
            bool: True if module was deactivated, False if not found
        """
        from accounts.models import UtilityModule
        
        try:
            module = UtilityModule.objects.get(key=key)
            module.is_active = False
            module.save()
            cls.clear_cache()
            return True
        except UtilityModule.DoesNotExist:
            return False
    
    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear module registry cache.
        
        Call this after any module updates to ensure consistency.
        """
        cache.delete(cls.CACHE_KEY)
    
    @classmethod
    def seed_default_modules(cls) -> None:
        """
        Seed database with default application modules.
        
        Creates standard modules with PUBLIC access by default.
        User assignments should be configured via Django admin.
        
        This method is idempotent - safe to run multiple times.
        """
        default_modules = [
            {
                'key': 'TRANSACTION',
                'title': 'TRANSACTION',
                'description': 'Manage Your Money Moves, One Day at a Time!',
                'url_pattern': '/transaction-detail/',
                'icon': 'fa-credit-card',
                'display_order': 1,
                'access_type': 'PUBLIC',
            },
            {
                'key': 'FINANCE',
                'title': 'FINANCE',
                'description': 'Track Your Loans and SIPs, No Slips!',
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
                'description': "Give Your Brain a Break, We've Got Your To-Dos Covered!",
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
                'access_type': 'ADMIN',  # Admin only
            },
        ]
        
        for module_data in default_modules:
            cls.register_module(**module_data)
        
        print(f"✅ Seeded {len(default_modules)} default modules")


# Singleton instance for convenience
module_registry = ModuleRegistryService()
