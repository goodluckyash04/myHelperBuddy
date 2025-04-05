import traceback
import base64
import datetime
from cryptography.fernet import Fernet

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q

from accounts.services.email_services import EmailService
from accounts.services.google_services import GoogleDriveService
from accounts.models import (
    Reminder,
    Task,
    Transaction,
    LedgerTransaction,
    FinancialProduct,
    User,
)
from accounts.views.view_reminder import calculate_reminder

class Command(BaseCommand):
    """
    Django management command to:
    - Check for task reminders
    - Detect database updates
    - Backup and send encrypted database via email
    """

    help = "Backup and send the encrypted database via email"
    


    def __init__(self):
        super().__init__()
        self.utc_today = datetime.datetime.now(datetime.timezone.utc).astimezone(
            datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        )
        self.email_service = EmailService()
        self.google_service = GoogleDriveService()

    def handle(self, *args, **options):
        """
        Main function executed when the command is run.
        """
        try:
            print("--------------------------------------------------")
            print(f"{self.utc_today.strftime('%Y-%m-%d %H:%M:%S')} : Starting the scheduler...")

            self.send_todays_task_reminder()
            self.backup_database()
            
            print(f"\n{self.utc_today.strftime('%Y-%m-%d %H:%M:%S')} : Scheduler completed.")
            print("--------------------------------------------------")

        except Exception as e:
            traceback.print_exc()
            print(f"\nAn error occurred during scheduler execution: {e}")

    def detect_database_update(self):
        """
        Checks if there have been any updates in the database in the last 24 hours.
        """
        print("\nStarting change detection...")
        changes_detected = False
        query = Q(
            updated_at__date__gte=self.utc_today.date() - datetime.timedelta(days=1)
        ) | Q(
            created_at__date__gte=self.utc_today - datetime.timedelta(days=1)
        )

        models_to_check = [User, Transaction, LedgerTransaction, FinancialProduct, Task, Reminder]

        for model in models_to_check:
            if model.objects.filter(query).exists():
                print(f"\tChanges detected in {model.__name__}")
                changes_detected = True
                break

        print("Change detection completed. Status:", changes_detected)
        return changes_detected

    def encrypt_data(self, data):
        """
        Encrypts data using a symmetric encryption key.
        """
        print("\nData encryption started...")

        encryption_key = base64.b64decode(settings.ENCRYPTION_KEY.encode("utf-8"))
        cipher_suite = Fernet(encryption_key)
        encrypted_data = cipher_suite.encrypt(data)
        print("Data encryption successfully completed.")
        return encrypted_data

    def clean_old_backups(self, existing_files):
        """
        Keeps backups from the last 7 days and the last backup of each month, deleting the rest.
    
        """
        print("\nBackup cleanup started...")
        
        backup_files = []
        for file in existing_files:
            name = file.get("name", "")
            if not name.endswith(".bin"):
                continue
            try:
                backup_date = datetime.datetime.strptime(name.split(".")[0], "%Y%m%d%H%M")
                backup_files.append((backup_date, file))
            except ValueError:
                pass 

        if not backup_files:
            return 

        # Sort backups by date (oldest first)
        backup_files.sort(reverse=True, key=lambda x: x[0])

        keep_files = set()
        last_backup_per_month = set()

        for backup_date, file in backup_files:
            # Keep backups from the last 7 days
            month_key = f"{backup_date.year}_{backup_date.month}"
            if (self.utc_today.date() - backup_date.date()).days <= 7:
                last_backup_per_month.add(month_key)
                keep_files.add(file["name"])
                continue
                
            # Keep the last backup of each month
            if month_key not in last_backup_per_month:
                last_backup_per_month.add(month_key)
                keep_files.add(file["name"])

        for backup_date, file in backup_files:
            if file["name"] not in keep_files or backup_date.date() == self.utc_today.date() :
                print(f"🗑️ Deleting: {file['name']}")
                self.google_service.delete_file(file["id"]) 

        print(f"✅ Cleanup complete! Kept {len(keep_files)} backups, deleted {len(backup_files) - len(keep_files)} backups.")

    def backup_database(self):
        """
        Encrypts and backs up the database, then emails it as an attachment.
        1. Fetch Existing backups and find the latest backup
        2. if no backup found or database has been updated or latest backup is 7 days old
           Cleans old file > Encrypt database > upload to drive or email  
        """
        print("\nDatabase backup started...")
        
        existing_files = []
        last_backup = None

        try:
            existing_files = self.google_service.list_files(folder_id=settings.BACKUP_FOLDER_ID)            
        except:
            pass    
        
        if existing_files:
            last_backup = max([datetime.datetime.strptime(i['name'].split(".")[0], "%Y%m%d%H%M") for i in existing_files if i['name'].endswith(".bin")]) 

        if not self.detect_database_update() and last_backup and (self.utc_today.date() - last_backup.date()).days < 7:
            print("\nBackup is not required for now.")
            return

        self.clean_old_backups(existing_files)

        db_file_path = settings.DATABASES["default"]["NAME"]
        with open(db_file_path, "rb") as f:
            database_data = f.read()

        file_name = f"{self.utc_today.strftime('%Y%m%d%H%M')}.bin"
        encrypted_data = self.encrypt_data(database_data)

        try:
            self.google_service.upload_to_drive(
                    encrypted_data, 
                    file_name, 
                    mime_type="application/octet-stream", 
                    folder_id=settings.BACKUP_FOLDER_ID
                )
        except:
            attachments = [(file_name, encrypted_data, "application/octet-stream")]
            self.email_service.send_email(
                subject="Database Backup Status",
                recipient_list=[settings.ADMIN_EMAIL],
                message=(
                    f"✅ Backup Successful!\n"
                    f"Timestamp: {self.utc_today.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Backup File: {file_name}\n"
                ),
                attachments=attachments,
            )
        print("\nDatabase backup completed successfully.")            
    
    def send_todays_task_reminder(self):
        """
        Fetches pending tasks and reminders for today and notifies users.
        """
        print("\nFetching pending tasks and today's reminders...")

        for user in User.objects.all():
            pending_date = self.utc_today.date() + datetime.timedelta(days=1)
            pending_tasks = Task.objects.filter(
                created_by=user, complete_by_date__lte=pending_date, status="Pending"
            )
            reminders = calculate_reminder(user)

            if not (pending_tasks or reminders):
                continue

            context = {
                "user": user,
                "tasks": pending_tasks,
                "reminders": reminders,
                "site_url": settings.SITE_URL,
            }

            self.email_service.send_email(
                subject="Pending Tasks & Reminders",
                recipient_list=[user.email],
                template_name="email_templates/task_reminders_email.html",
                context=context,
                is_html=True,
            )

        print("Pending tasks and today's reminders fetched successfully.")

# To run the command:
# python manage.py your_custom_command
