# Migration: Move existing Transaction rows into the new Entry model.
#
# For each user:
#   1. Create a "Default (Migrated)" Account (type=bank)
#   2. Create Category objects from the old Transaction.category text field
#   3. Create Entry rows from each non-deleted Transaction row
#
# OLD Transaction.type values: 'Expense', 'Income'
# NEW Entry.entry_type values:  'expense', 'income'

from django.db import migrations


def migrate_transactions_to_entries(apps, schema_editor):
    Transaction = apps.get_model('accounts', 'Transaction')
    Account = apps.get_model('accounts', 'Account')
    Category = apps.get_model('accounts', 'Category')
    Entry = apps.get_model('accounts', 'Entry')
    User = apps.get_model('auth', 'User')

    # Map old Transaction.type -> new Entry.entry_type
    TYPE_MAP = {
        'Expense': 'expense',
        'Income': 'income',
    }

    # Map old category name -> category_type for new Category model
    CATEGORY_TYPE_MAP = {
        'Salary': 'income',
        # All others default to expense
    }

    # Process per user
    users_with_txns = (
        Transaction.objects
        .filter(is_deleted=False)
        .values_list('created_by_id', flat=True)
        .distinct()
    )

    for user_id in users_with_txns:
        # 1. Create a single default account for this user
        default_account, _ = Account.objects.get_or_create(
            name='Default (Migrated)',
            created_by_id=user_id,
            defaults={'account_type': 'bank', 'is_active': True},
        )

        # 2. Create Category objects for unique (category_name, type) combos
        user_txns = Transaction.objects.filter(
            created_by_id=user_id, is_deleted=False
        )

        category_cache = {}  # (name_lower, cat_type) -> Category obj

        unique_cats = (
            user_txns
            .values_list('category', 'type')
            .distinct()
        )
        for cat_name, txn_type in unique_cats:
            if not cat_name:
                continue
            cat_type = CATEGORY_TYPE_MAP.get(cat_name, 'income' if txn_type == 'Income' else 'expense')
            key = (cat_name.lower(), cat_type)
            if key not in category_cache:
                cat_obj, _ = Category.objects.get_or_create(
                    name=cat_name,
                    category_type=cat_type,
                    created_by_id=user_id,
                    defaults={'is_active': True},
                )
                category_cache[key] = cat_obj

        # 3. Create Entry rows
        entries_to_create = []
        for txn in user_txns:
            entry_type = TYPE_MAP.get(txn.type, 'expense')
            cat_type = 'income' if entry_type == 'income' else 'expense'
            cat_name = txn.category or ''
            cat_key = (cat_name.lower(), cat_type)
            category_obj = category_cache.get(cat_key)

            note_parts = []
            if txn.description:
                note_parts.append(txn.description)
            if txn.beneficiary:
                note_parts.append(f"({txn.beneficiary})")
            note = ' '.join(note_parts)[:255]

            entries_to_create.append(Entry(
                account=default_account,
                entry_type=entry_type,
                amount=txn.amount,
                date=txn.date,
                category=category_obj,
                note=note,
                linked_loan=None,
                linked_investment=None,
                linked_split=None,
                created_by_id=user_id,
                created_at=txn.created_at,
            ))

        Entry.objects.bulk_create(entries_to_create, batch_size=500)


def reverse_migrate(apps, schema_editor):
    # Reverse: delete all migrated entries (those tied to 'Default (Migrated)' accounts)
    Account = apps.get_model('accounts', 'Account')
    Entry = apps.get_model('accounts', 'Entry')
    migrated_accounts = Account.objects.filter(name='Default (Migrated)')
    Entry.objects.filter(account__in=migrated_accounts).delete()
    migrated_accounts.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0032_add_account_category_loan_investment_splitplan_entry'),
    ]

    operations = [
        migrations.RunPython(migrate_transactions_to_entries, reverse_migrate),
    ]
