"""
Database Backup Management Command

Django management command that provides automated database backup and maintenance:
- Detects database changes in the last 24 hours
- Creates encrypted database backups
- Uploads backups to Google Drive
- Sends backup email notifications as fallback
- Maintains backup retention policy (7 days + monthly)
- Sends daily task and reminder notifications to users

Usage:
    python manage.py backup_db
"""

import base64
import datetime
import traceback
from typing import List, Optional, Set, Tuple

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q

from accounts.models import (
    FinancialProduct,
    LedgerTransaction,
    Reminder,
    Task,
    Transaction,
    UserProfile,
)
from accounts.services.email_services import EmailService
from accounts.services.google_services import GoogleDriveService
from accounts.views.view_reminder import calculate_reminder

User = get_user_model()


class Command(BaseCommand):
    """
    Automated database backup and task reminder management command.
    
    Features:
        - Change detection for database models
        - Encrypted database backups with Fernet
        - Google Drive upload with fallback to email
        - Smart backup retention (7 days + last of each month)
        - Daily task and reminder email notifications
        - IST timezone support (UTC+5:30)
    """
    
    help = "Backup encrypted database and send task/reminder notifications"
    
    # Backup retention settings
    RETENTION_DAYS = 7
    
    def add_arguments(self, parser):
        """Add custom command arguments."""
        parser.add_argument(
            '--skip-reminders',
            action='store_true',
            help='Skip sending task reminder emails (only backup database)',
        )
    
    def __init__(self):
        """Initialize command with services and timezone."""
        super().__init__()
        
        # Set IST timezone (UTC+5:30)
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        ist_tz = datetime.timezone(ist_offset)
        self.now = datetime.datetime.now(datetime.timezone.utc).astimezone(ist_tz)
        
        # Initialize services
        self.email_service = EmailService()
        self.google_service = GoogleDriveService()
    
    def handle(self, *args, **options):
        """
        Main entry point for the management command.
        
        Executes:
            1. Task and reminder notifications (unless --skip-reminders)
            2. Database backup (if needed)
        
        Args:
            options: Command options including skip_reminders flag
        """
        skip_reminders = options.get('skip_reminders', False)
        
        try:
            self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
            self.stdout.write(
                self.style.SUCCESS(
                    f"🚀 Backup Scheduler Started - {self.now.strftime('%Y-%m-%d %H:%M:%S IST')}"
                )
            )
            self.stdout.write(self.style.SUCCESS("=" * 60))
            
            # Send task reminders to users (unless skipped)
            if not skip_reminders:
                self.send_todays_task_reminder()
            else:
                self.stdout.write(
                    self.style.WARNING("\n⏭️  Skipping task reminder emails")
                )
            
            # Backup database if needed
            self.backup_database()
            
            self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Backup Scheduler Completed - {self.now.strftime('%Y-%m-%d %H:%M:%S IST')}"
                )
            )
            self.stdout.write(self.style.SUCCESS("=" * 60 + "\n"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Scheduler failed: {e}"))
            traceback.print_exc()
    
    # ========================================================================
    # Change Detection
    # ========================================================================
    
    def detect_database_update(self) -> bool:
        """
        Check if database has been updated in the last 24 hours.
        
        Checks all primary models for recent created_at or updated_at timestamps.
        
        Returns:
            bool: True if changes detected, False otherwise
        """
        self.stdout.write("\n🔍 Detecting database changes...")
        
        yesterday = self.now - datetime.timedelta(days=1)
        query = Q(updated_at__gte=yesterday) | Q(created_at__gte=yesterday)
        
        models_to_check = [
            UserProfile,
            Transaction,
            LedgerTransaction,
            FinancialProduct,
            Task,
            Reminder,
        ]
        
        for model in models_to_check:
            if model.objects.filter(query).exists():
                self.stdout.write(
                    self.style.WARNING(f"   📝 Changes detected in {model.__name__}")
                )
                return True
        
        self.stdout.write(self.style.SUCCESS("   ✅ No recent changes detected"))
        return False
    
    # ========================================================================
    # Encryption
    # ========================================================================
    
    def encrypt_data(self, data: bytes) -> bytes:
        """
        Encrypt data using Fernet symmetric encryption.
        
        Args:
            data: Raw bytes to encrypt
            
        Returns:
            bytes: Encrypted data
            
        Raises:
            Exception: If encryption key is invalid
        """
        self.stdout.write("🔐 Encrypting database...")
        
        try:
            encryption_key = base64.b64decode(settings.ENCRYPTION_KEY.encode("utf-8"))
            cipher_suite = Fernet(encryption_key)
            encrypted_data = cipher_suite.encrypt(data)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✅ Encrypted {len(data):,} bytes → {len(encrypted_data):,} bytes"
                )
            )
            return encrypted_data
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Encryption failed: {e}"))
            raise
    
    # ========================================================================
    # Backup Management
    # ========================================================================
    
    def clean_old_backups(self, existing_files: List[dict]) -> None:
        """
        Maintain backup retention policy.
        
        Retention rules:
            - Keep all backups from last 7 days
            - Keep last backup of each month
            - Delete everything else
        
        Args:
            existing_files: List of file dicts from Google Drive
        """
        self.stdout.write("\n🧹 Cleaning old backups...")
        
        # Parse backup files
        backup_files: List[Tuple[datetime.datetime, dict]] = []
        for file in existing_files:
            name = file.get("name", "")
            if not name.endswith(".bin"):
                continue
            
            try:
                # Parse timestamp from filename (format: YYYYMMDDHHMM.bin)
                backup_date = datetime.datetime.strptime(
                    name.split(".")[0],
                    "%Y%m%d%H%M"
                )
                backup_files.append((backup_date, file))
            except ValueError:
                self.stdout.write(
                    self.style.WARNING(f"   ⚠️  Invalid backup filename: {name}")
                )
        
        if not backup_files:
            self.stdout.write("   ℹ️  No backup files to clean")
            return
        
        # Sort by date (newest first)
        backup_files.sort(reverse=True, key=lambda x: x[0])
        
        # Determine which files to keep
        keep_files: Set[str] = set()
        monthly_backups: Set[str] = set()
        
        for backup_date, file in backup_files:
            month_key = f"{backup_date.year}_{backup_date.month:02d}"
            age_days = (self.now.date() - backup_date.date()).days
            
            # Keep backups from last N days
            if age_days <= self.RETENTION_DAYS:
                keep_files.add(file["name"])
                monthly_backups.add(month_key)
                continue
            
            # Keep last backup of each month
            if month_key not in monthly_backups:
                keep_files.add(file["name"])
                monthly_backups.add(month_key)
        
        # Delete old backups
        deleted_count = 0
        for backup_date, file in backup_files:
            # Skip if it's today's backup or marked to keep
            if (file["name"] in keep_files or 
                backup_date.date() == self.now.date()):
                continue
            
            try:
                self.stdout.write(f"   🗑️  Deleting: {file['name']}")
                self.google_service.delete_file(file["id"])
                deleted_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"   ❌ Failed to delete {file['name']}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"   ✅ Cleanup complete! Kept {len(keep_files)}, deleted {deleted_count}"
            )
        )
    
    def get_latest_backup(self, files: List[dict]) -> Optional[datetime.datetime]:
        """
        Find the most recent backup from file list.
        
        Args:
            files: List of file dicts from Google Drive
            
        Returns:
            datetime: Timestamp of latest backup, or None if no backups found
        """
        backup_dates = []
        
        for file in files:
            name = file.get("name", "")
            if not name.endswith(".bin"):
                continue
            
            try:
                backup_date = datetime.datetime.strptime(
                    name.split(".")[0],
                    "%Y%m%d%H%M"
                )
                backup_dates.append(backup_date)
            except ValueError:
                pass
        
        return max(backup_dates) if backup_dates else None
    
    def backup_database(self) -> None:
        """
        Create and upload encrypted database backup.
        
        Backup is created if:
            - No previous backup exists, OR
            - Database has been updated, OR
            - Last backup is older than 7 days
        
        Backup flow:
            1. Check if backup is needed
            2. Clean old backups
            3. Read and encrypt database
            4. Upload to Google Drive (fallback to email)
        """
        self.stdout.write("\n💾 Starting database backup process...")
        
        # Fetch existing backups
        existing_files = []
        try:
            if self.google_service.is_service_active:
                existing_files = self.google_service.list_files(
                    folder_id=settings.BACKUP_FOLDER_ID
                )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"   ⚠️  Could not fetch existing backups: {e}")
            )
        
        # Find latest backup
        last_backup = self.get_latest_backup(existing_files)
        
        # Determine if backup is needed
        if last_backup:
            days_since_backup = (self.now.date() - last_backup.date()).days
            self.stdout.write(
                f"   📅 Last backup: {last_backup.strftime('%Y-%m-%d %H:%M')} "
                f"({days_since_backup} days ago)"
            )
            
            if not self.detect_database_update() and days_since_backup < self.RETENTION_DAYS:
                self.stdout.write(
                    self.style.SUCCESS("   ✅ Backup not needed (no changes, recent backup exists)")
                )
                return
        else:
            self.stdout.write("   ℹ️  No previous backup found")
        
        # Clean old backups before creating new one
        if existing_files:
            self.clean_old_backups(existing_files)
        
        # Read database file
        db_file_path = settings.DATABASES["default"]["NAME"]
        self.stdout.write(f"   📂 Reading database: {db_file_path}")
        
        try:
            with open(db_file_path, "rb") as f:
                database_data = f.read()
            
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ Read {len(database_data):,} bytes")
            )
        except IOError as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Failed to read database: {e}"))
            return
        
        # Encrypt database
        encrypted_data = self.encrypt_data(database_data)
        
        # Generate backup filename
        file_name = f"{self.now.strftime('%Y%m%d%H%M')}.bin"
        
        # Try Google Drive upload first
        if self.google_service.is_service_active:
            try:
                self.stdout.write(f"   ☁️  Uploading to Google Drive: {file_name}")
                self.google_service.upload_to_drive(
                    encrypted_data,
                    file_name,
                    mime_type="application/octet-stream",
                    folder_id=settings.BACKUP_FOLDER_ID
                )
                self.stdout.write(
                    self.style.SUCCESS("   ✅ Database backup uploaded to Google Drive")
                )
                return
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"   ⚠️  Google Drive upload failed: {e}\n   📧 Falling back to email..."
                    )
                )
        
        # Fallback to email
        attachments = [(file_name, encrypted_data, "application/octet-stream")]
        
        try:
            self.email_service.send_email(
                subject="Database Backup - Email Delivery",
                recipient_list=[settings.ADMIN_EMAIL],
                message=(
                    f"✅ Database Backup Successful\n\n"
                    f"Timestamp: {self.now.strftime('%Y-%m-%d %H:%M:%S IST')}\n"
                    f"Backup File: {file_name}\n"
                    f"Size: {len(encrypted_data):,} bytes\n\n"
                    f"Note: Google Drive upload failed. Backup sent via email."
                ),
                attachments=attachments,
            )
            self.stdout.write(
                self.style.SUCCESS("   ✅ Database backup sent via email")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"   ❌ Backup failed (email fallback): {e}")
            )
    
    # ========================================================================
    # Task & Reminder Notifications
    # ========================================================================
    
    def send_todays_task_reminder(self) -> None:
        """
        Send daily email notifications for pending tasks and reminders.
        
        Notifies users about:
            - Tasks due today or tomorrow
            - Reminders scheduled for today
        
        Only sends emails to users who have pending items.
        """
        self.stdout.write("\n📬 Sending task and reminder notifications...")
        
        users_notified = 0
        pending_tomorrow = self.now.date() + datetime.timedelta(days=1)
        
        for user in User.objects.all():
            # Get pending tasks
            pending_tasks = Task.objects.filter(
                created_by=user,
                complete_by_date__lte=pending_tomorrow,
                status="Pending"
            )
            
            # Get today's reminders
            reminders = calculate_reminder(user)
            
            # Skip if no tasks or reminders
            if not (pending_tasks or reminders):
                continue
            
            # Prepare email context
            context = {
                "user": user,
                "tasks": pending_tasks,
                "reminders": reminders,
                "site_url": getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            }
            
            # Send notification email
            try:
                self.email_service.send_email(
                    subject="📋 Pending Tasks & Reminders",
                    recipient_list=[user.email],
                    template_name="email_templates/task_reminders_email.html",
                    context=context,
                    is_html=True,
                )
                users_notified += 1
                self.stdout.write(
                    f"   ✅ Notification sent to {user.username} ({user.email})"
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"   ❌ Failed to notify {user.username}: {e}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"   📧 Task reminders sent to {users_notified} user(s)"
            )
        )
