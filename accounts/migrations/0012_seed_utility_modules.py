# Generated data migration

from django.db import migrations


def seed_modules(apps, schema_editor):
    """Seed the database with existing utility modules from settings"""
    UtilityModule = apps.get_model('accounts', 'UtilityModule')
    
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
            'access_type': 'ADMIN',
        },
    ]

    for module_data in default_modules:
        key = module_data.get('key')
        UtilityModule.objects.update_or_create(
            key=key,
            defaults=module_data
        )


def reverse_seed(apps, schema_editor):
    """Remove all seeded modules on rollback"""
    UtilityModule = apps.get_model('accounts', 'UtilityModule')
    UtilityModule.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_utilitymodule'),
    ]

    operations = [
        migrations.RunPython(seed_modules, reverse_seed),
    ]
