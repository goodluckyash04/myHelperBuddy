# Generated data migration

from django.db import migrations


def seed_modules(apps, schema_editor):
    """Seed the database with existing utility modules from settings"""
    from accounts.services.module_registry import ModuleRegistryService
    ModuleRegistryService.seed_default_modules()


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
