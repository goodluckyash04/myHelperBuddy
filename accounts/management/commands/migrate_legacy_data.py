"""
Management command: migrate_legacy_data
=======================================
Phase E - One-time migration of legacy FinancialProduct rows into the new
Loan / Investment / SplitPlan models, and LedgerTransaction rows into
LedgerContact / LedgerEntry models.

SAFETY RULES
------------
- Idempotent: running twice will NOT duplicate records (uses get_or_create / skip-if-exists).
- Logs every row mapped, skipped, or failed.
- Prints a reconciliation table at the end: old count vs new count per model.
- Does NOT delete any legacy data.

USAGE
-----
    python manage.py migrate_legacy_data               # dry-run (no writes)
    python manage.py migrate_legacy_data --commit      # write to database
    python manage.py migrate_legacy_data --commit --verbosity 2   # verbose
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "One-time migration: FinancialProduct -> Loan/Investment/SplitPlan; "
        "LedgerTransaction -> LedgerContact/LedgerEntry"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--commit',
            action='store_true',
            default=False,
            help=(
                "Actually write records to the database. "
                "Without this flag the command runs in dry-run mode."
            ),
        )

    def handle(self, *args, **options):
        commit = options['commit']
        verbosity = options.get('verbosity', 1)

        if not commit:
            self.stdout.write(self.style.WARNING(
                "\n[DRY RUN] No changes will be written. Add --commit to persist.\n"
            ))

        stats = {
            'financial_products_total': 0,
            'loans_created': 0,
            'investments_created': 0,
            'split_plans_created': 0,
            'financial_products_skipped': 0,
            'financial_products_unmapped': 0,

            'ledger_transactions_total': 0,
            'ledger_contacts_created': 0,
            'ledger_entries_created': 0,
            'ledger_transactions_skipped': 0,
        }

        # Import models inline to avoid circular imports
        from accounts.models import (
            FinancialProduct, LedgerTransaction,
            Account, Loan, Investment, SplitPlan,
            LedgerContact, LedgerEntry,
        )

        with db_transaction.atomic():
            # ================================================================
            # PART 1: FinancialProduct -> Loan / Investment / SplitPlan
            # ================================================================
            self.stdout.write("\n-- Part 1: FinancialProduct -> Loan / Investment / SplitPlan --")

            products = FinancialProduct.objects.filter(is_deleted=False).select_related('created_by')
            stats['financial_products_total'] = products.count()

            for fp in products:
                fp_type = fp.type.strip().lower() if fp.type else ''
                user = fp.created_by

                # Get or create a migration account for this user
                migration_account, _ = Account.objects.get_or_create(
                    name='Default (Migrated)',
                    created_by=user,
                    defaults={'account_type': 'bank', 'is_active': True},
                )

                if fp_type == 'loan':
                    exists = Loan.objects.filter(
                        name=fp.name,
                        created_by=user,
                        start_date=fp.started_on,
                    ).exists()
                    if exists:
                        stats['financial_products_skipped'] += 1
                        if verbosity >= 2:
                            self.stdout.write(f"  SKIP Loan already exists: {fp.name}")
                        continue

                    monthly_emi = (fp.amount / fp.no_of_installments) if fp.no_of_installments else fp.amount

                    if commit:
                        Loan.objects.create(
                            name=fp.name,
                            principal=fp.amount,
                            monthly_emi=monthly_emi,
                            account=migration_account,
                            start_date=fp.started_on,
                            is_active=(fp.status == 'Open'),
                            created_by=user,
                        )
                    stats['loans_created'] += 1
                    if verbosity >= 2:
                        mode = 'CREATE' if commit else 'DRY'
                        self.stdout.write(f"  [{mode}] Loan: {fp.name}  EMI=Rs.{monthly_emi:.2f}")

                elif fp_type in ('sip', 'investment', 'mutual fund', 'mf'):
                    exists = Investment.objects.filter(
                        name=fp.name,
                        created_by=user,
                        start_date=fp.started_on,
                    ).exists()
                    if exists:
                        stats['financial_products_skipped'] += 1
                        if verbosity >= 2:
                            self.stdout.write(f"  SKIP Investment already exists: {fp.name}")
                        continue

                    monthly_amount = (fp.amount / fp.no_of_installments) if fp.no_of_installments else fp.amount

                    if commit:
                        Investment.objects.create(
                            name=fp.name,
                            monthly_amount=monthly_amount,
                            account=migration_account,
                            start_date=fp.started_on,
                            is_active=(fp.status == 'Open'),
                            created_by=user,
                        )
                    stats['investments_created'] += 1
                    if verbosity >= 2:
                        mode = 'CREATE' if commit else 'DRY'
                        self.stdout.write(f"  [{mode}] Investment: {fp.name}  Monthly=Rs.{monthly_amount:.2f}")

                elif fp_type in ('split', 'no cost emi', 'no-cost emi', 'emi'):
                    exists = SplitPlan.objects.filter(
                        title=fp.name,
                        created_by=user,
                        start_month=fp.started_on,
                    ).exists()
                    if exists:
                        stats['financial_products_skipped'] += 1
                        if verbosity >= 2:
                            self.stdout.write(f"  SKIP SplitPlan already exists: {fp.name}")
                        continue

                    if commit:
                        SplitPlan.objects.create(
                            title=fp.name,
                            total_amount=fp.amount,
                            num_months=fp.no_of_installments or 1,
                            start_month=fp.started_on,
                            account=migration_account,
                            created_by=user,
                        )
                    stats['split_plans_created'] += 1
                    if verbosity >= 2:
                        mode = 'CREATE' if commit else 'DRY'
                        self.stdout.write(
                            f"  [{mode}] SplitPlan: {fp.name}  "
                            f"Rs.{fp.amount}/{fp.no_of_installments} months"
                        )

                else:
                    stats['financial_products_unmapped'] += 1
                    self.stdout.write(self.style.WARNING(
                        f"  [UNMAPPED] FinancialProduct id={fp.pk} name='{fp.name}' "
                        f"type='{fp.type}' -- cannot map to Loan/Investment/SplitPlan. Skipped."
                    ))

            # ================================================================
            # PART 2: LedgerTransaction -> LedgerContact / LedgerEntry
            # ================================================================
            self.stdout.write("\n-- Part 2: LedgerTransaction -> LedgerContact / LedgerEntry --")

            ledger_txns = LedgerTransaction.objects.filter(is_deleted=False).select_related('created_by')
            stats['ledger_transactions_total'] = ledger_txns.count()

            for lt in ledger_txns:
                user = lt.created_by
                counterparty_name = (lt.counterparty or '').strip()
                if not counterparty_name:
                    counterparty_name = 'Unknown'

                # Get or create LedgerContact
                contact, contact_created = LedgerContact.objects.get_or_create(
                    name=counterparty_name,
                    created_by=user,
                    defaults={'phone': ''},
                )
                if contact_created:
                    stats['ledger_contacts_created'] += 1

                # Map transaction_type to entry_type (given/taken)
                LEDGER_TYPE_MAP = {
                    'PAYABLE':    'given',    # you are paying
                    'PAID':       'given',
                    'RECEIVABLE': 'taken',    # counterparty owes you
                    'RECEIVED':   'taken',
                }
                entry_type = LEDGER_TYPE_MAP.get(lt.transaction_type)
                if not entry_type:
                    stats['ledger_transactions_skipped'] += 1
                    self.stdout.write(self.style.WARNING(
                        f"  [SKIP] LedgerTransaction id={lt.pk} unknown type='{lt.transaction_type}'"
                    ))
                    continue

                # Check if already migrated (match date+amount+type+contact+user)
                exists = LedgerEntry.objects.filter(
                    contact=contact,
                    created_by=user,
                    amount=lt.amount,
                    date=lt.transaction_date,
                    entry_type=entry_type,
                ).exists()
                if exists:
                    stats['ledger_transactions_skipped'] += 1
                    if verbosity >= 2:
                        self.stdout.write(f"  SKIP LedgerEntry already exists for txn id={lt.pk}")
                    continue

                # Map status
                status = 'settled' if lt.status in ('COMPLETED', 'CANCELLED') else 'open'
                note = (lt.description or lt.notes or '')[:255]

                if commit:
                    le = LedgerEntry.objects.create(
                        contact=contact,
                        entry_type=entry_type,
                        amount=lt.amount,
                        date=lt.transaction_date,
                        status=status,
                        note=note,
                        created_by=user,
                    )
                    if status == 'settled' and lt.completion_date:
                        from django.utils import timezone
                        import datetime
                        le.settled_at = timezone.make_aware(
                            datetime.datetime.combine(lt.completion_date, datetime.time())
                        )
                        le.save(update_fields=['settled_at'])

                stats['ledger_entries_created'] += 1
                if verbosity >= 2:
                    mode = 'CREATE' if commit else 'DRY'
                    self.stdout.write(
                        f"  [{mode}] LedgerEntry {entry_type} Rs.{lt.amount} with {counterparty_name}"
                    )

            if not commit:
                # Rollback in dry-run mode
                db_transaction.set_rollback(True)

        # ────────────────────────────────────────────────────────────────────
        # Reconciliation Report
        # ────────────────────────────────────────────────────────────────────
        action = 'created' if commit else '(would create)'
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  RECONCILIATION REPORT")
        self.stdout.write("=" * 60)
        self.stdout.write(f"\n  FinancialProduct (legacy)        : {stats['financial_products_total']} rows")
        self.stdout.write(f"  -> Loans {action:<20}  : {stats['loans_created']}")
        self.stdout.write(f"  -> Investments {action:<16}  : {stats['investments_created']}")
        self.stdout.write(f"  -> SplitPlans {action:<17}  : {stats['split_plans_created']}")
        self.stdout.write(f"  -> Already existed (skipped)     : {stats['financial_products_skipped']}")
        self.stdout.write(f"  -> Unmapped (investigate these)  : {stats['financial_products_unmapped']}")

        self.stdout.write(f"\n  LedgerTransaction (legacy)       : {stats['ledger_transactions_total']} rows")
        self.stdout.write(f"  -> LedgerContacts {action:<15}  : {stats['ledger_contacts_created']}")
        self.stdout.write(f"  -> LedgerEntries {action:<16}  : {stats['ledger_entries_created']}")
        self.stdout.write(f"  -> Already existed (skipped)     : {stats['ledger_transactions_skipped']}")
        self.stdout.write("=" * 60)

        if stats['financial_products_unmapped'] > 0:
            self.stdout.write(self.style.WARNING(
                f"\n  [WARN] {stats['financial_products_unmapped']} FinancialProduct rows could not be mapped. "
                "Check --verbosity 2 output or inspect FinancialProduct.type values."
            ))

        if commit:
            self.stdout.write(self.style.SUCCESS("\n  [OK] Migration committed successfully."))
        else:
            self.stdout.write(self.style.WARNING(
                "\n  [DRY RUN] No changes written. Re-run with --commit to apply.\n"
            ))
