import traceback
import base64
import json
import datetime
from cryptography.fernet import Fernet

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q

from accounts.services.email_services import EmailService
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

    def handle(self, *args, **options):
        """
        Main function executed when the command is run.
        """
        try:
            print("--------------------------------------------------")
            print(f"{self.utc_today.strftime('%Y-%m-%d %H:%M:%S')} : Starting the scheduler...")

            self.send_todays_task_reminder()

            with open(settings.JSON_DB) as file:
                file_data = file.read()
                last_backup = json.loads(file_data).get("last_backup") if file_data else None

            last_backup = (
                datetime.datetime.strptime(last_backup, "%Y-%m-%d %H:%M:%S")
                if last_backup
                else None
            )

            if not last_backup or self.detect_database_update() or (
                (self.utc_today.date() - last_backup.date()).days >= 7
            ):
                self.backup_database()
                with open(settings.JSON_DB, "w") as file:
                    json.dump({"last_backup": self.utc_today.strftime("%Y-%m-%d %H:%M:%S")}, file, indent=4)

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

    def backup_database(self):
        """
        Encrypts and backs up the database, then emails it as an attachment.
        """
        print("\nDatabase backup started...")

        db_file_path = settings.DATABASES["default"]["NAME"]
        with open(db_file_path, "rb") as f:
            database_data = f.read()

        file_name = f"{self.utc_today.strftime('%Y%m%d%H%M')}.bin"
        encrypted_data = self.encrypt_data(database_data)

        if encrypted_data:
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
        else:
            print("\nDatabase backup failed due to encryption error.")

    def encrypt_data(self, data):
        """
        Encrypts data using a symmetric encryption key.
        """
        print("\nData encryption started...")
        try:
            encryption_key = base64.b64decode(settings.ENCRYPTION_KEY.encode("utf-8"))
            cipher_suite = Fernet(encryption_key)
            encrypted_data = cipher_suite.encrypt(data)
            print("Data encryption successfully completed.")
            return encrypted_data
        except Exception:
            print("Error during encryption.")
            traceback.print_exc()
            return None

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

            if pending_tasks or reminders:
                context = {
                    "user": user,
                    "tasks": pending_tasks,
                    "reminders": reminders,
                    "site_url": settings.SITE_URL,
                }

                self.email_service.send_email(
                    subject="Pending Tasks & Reminders",
                    recipient_list=[user.email],
                    template_name="email_templates\\task_reminders_email.html",
                    context=context,
                    is_html=True,
                )

        print("Pending tasks and today's reminders fetched successfully.")


# To run the command:
# python manage.py your_custom_command
