"""
Django management command to migrate existing ledger transaction data
to the new enhanced structure with payment tracking and installments.

Usage:
    python manage.py migrate_ledger_data
    python manage.py migrate_ledger_data --dry-run  # Test without making changes
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import LedgerTransaction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Migrate existing ledger transactions to new enhanced structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making actual changes (preview mode)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be saved'))
        
        # Get all transactions that need migration
        transactions = LedgerTransaction.objects.all()
        total_count = transactions.count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('No transactions found to migrate'))
            return
        
        self.stdout.write(f'Found {total_count} transactions to migrate')
        
        updated_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            for txn in transactions:
                updated = False
                changes = []
                
                # 1. Set status based on transaction_type if not set
                if not txn.status or txn.status == '':
                    if txn.transaction_type in ['RECEIVED', 'PAID']:
                        txn.status = 'COMPLETED'
                        changes.append('status -> COMPLETED')
                    elif txn.transaction_type in ['RECEIVABLE', 'PAYABLE']:
                        txn.status = 'PENDING'
                        changes.append('status -> PENDING')
                    updated = True
                
                # 2. Set paid_amount and remaining_amount
                if txn.paid_amount is None:
                    if txn.transaction_type in ['RECEIVED', 'PAID']:
                        # Completed transactions
                        txn.paid_amount = txn.amount
                        txn.remaining_amount = Decimal('0.00')
                        changes.append(f'paid_amount -> {txn.amount}')
                        changes.append('remaining_amount -> 0.00')
                    else:
                        # Pending transactions
                        txn.paid_amount = Decimal('0.00')
                        txn.remaining_amount = txn.amount
                        changes.append('paid_amount -> 0.00')
                        changes.append(f'remaining_amount -> {txn.amount}')
                    updated = True
                
                # 3. Set completion_date for completed transactions
                if txn.status == 'COMPLETED' and txn.completion_date is None:
                    txn.completion_date = txn.transaction_date
                    changes.append(f'completion_date -> {txn.transaction_date}')
                    updated = True
                
                # 4. Convert existing transaction_type if needed
                type_mapping = {
                    'Receivable': 'RECEIVABLE',
                    'Payable': 'PAYABLE',
                    'Received': 'RECEIVED',
                    'Paid': 'PAID'
                }
                if txn.transaction_type in type_mapping:
                    old_type = txn.transaction_type
                    txn.transaction_type = type_mapping[old_type]
                    changes.append(f'transaction_type: {old_type} -> {txn.transaction_type}')
                    updated = True
                
                # 5. Initialize empty tags list if None
                if txn.tags is None:
                    txn.tags = []
                    changes.append('tags -> []')
                    updated = True
                
                # Save changes
                if updated:
                    if not dry_run:
                        txn.save()
                    
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Updated Transaction #{txn.id} ({txn.counterparty}): {", ".join(changes)}'
                        )
                    )
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'○ Skipped Transaction #{txn.id} (already migrated)'
                        )
                    )
            
            # Rollback if dry run
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('\nDRY RUN - No changes were saved'))
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Migration Summary:'))
        self.stdout.write(f'  Total transactions: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'  Updated: {updated_count}'))
        self.stdout.write(self.style.WARNING(f'  Skipped: {skipped_count}'))
        
        if not dry_run:
            self.stdout.write('\n' + self.style.SUCCESS('✓ Migration completed successfully!'))
        else:
            self.stdout.write('\n' + self.style.WARNING('Run without --dry-run to apply changes'))
