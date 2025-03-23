import traceback

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

class EmailService:
    """
    Handles sending emails with optional attachments.
    """

    def __init__(self):
        self.email_service = (settings.EMAIL_SERVICE == "1") 

    def send_email(self, subject, recipient_list, message=None, template_name=None, context=None, attachments=None, is_html=False):
        """
        Sends an email with optional HTML content and attachments.
        """
        if not self.email_service:
            print("Email service is offline.")
            return

        print(f"\n{subject} - Sending Email...")

        try:
            if template_name and context:
                message = render_to_string(template_name, context)

            email = EmailMessage(
                subject=subject,
                body=message if message else "This is an automated notification.",
                from_email=settings.EMAIL_HOST_USER,
                to=recipient_list,
            )

            if is_html:
                email.content_subtype = "html"

            if attachments:
                for filename, content, mime_type in attachments:
                    email.attach(filename, content, mime_type)
             
            email_sent = email.send()

            if email_sent:
                # Obfuscating recipient emails in logs
                obfuscated_emails = [
                    f"{email[:2]}******{email[-2:]}@{domain}" for email, domain in [rec.split("@") for rec in recipient_list]
                ]
                print(f"{subject}: Email sent successfully to {', '.join(obfuscated_emails)}")
            else:
                print(f"{subject}: Email sending failed.")

            return email_sent
        except Exception:
            traceback.print_exc()
