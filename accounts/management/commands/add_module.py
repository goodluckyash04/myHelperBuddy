from django.core.management.base import BaseCommand, CommandError
from accounts.services.module_registry import module_registry


class Command(BaseCommand):
    help = 'Add or update a utility module in the registry'

    def add_arguments(self, parser):
        parser.add_argument(
            '--key', 
            type=str, 
            required=True, 
            help='Module key (unique identifier, e.g., "INVENTORY")'
        )
        parser.add_argument(
            '--title', 
            type=str, 
            required=True, 
            help='Module title (e.g., "Inventory Manager")'
        )
        parser.add_argument(
            '--description', 
            type=str, 
            required=True, 
            help='Module description shown to users'
        )
        parser.add_argument(
            '--url', 
            type=str, 
            required=True, 
            help='URL pattern (e.g., "/inventory/")'
        )
        parser.add_argument(
            '--icon', 
            type=str, 
            default='fa-puzzle-piece', 
            help='Font Awesome icon class (default: fa-puzzle-piece)'
        )
        parser.add_argument(
            '--order', 
            type=int, 
            default=99, 
            help='Display order (default: 99)'
        )
        parser.add_argument(
            '--access', 
            type=str, 
            default='CONFIG', 
            choices=['PUBLIC', 'CONFIG', 'ADMIN'], 
            help='Access type: PUBLIC (all users), CONFIG (specific users), ADMIN (admin only)'
        )
        parser.add_argument(
            '--users', 
            type=str, 
            default='*', 
            help='Allowed users if access=CONFIG (comma-separated usernames or "*" for all)'
        )
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Create module as inactive (disabled)'
        )

    def handle(self, *args, **options):
        try:
            module = module_registry.register_module(
                key=options['key'],
                title=options['title'],
                description=options['description'],
                url_pattern=options['url'],
                icon=options['icon'],
                display_order=options['order'],
                access_type=options['access'],
                allowed_users=options['users'],
                is_active=not options['inactive']
            )
            
            action = "Updated" if module else "Created"
            self.stdout.write(
                self.style.SUCCESS(
                    f'{action} module: {options["title"]} ({options["key"]})'
                )
            )
            self.stdout.write(f'  URL: {options["url"]}')
            self.stdout.write(f'  Access: {options["access"]}')
            self.stdout.write(f'  Active: {not options["inactive"]}')
            
        except Exception as e:
            raise CommandError(f'Error creating module: {str(e)}')
