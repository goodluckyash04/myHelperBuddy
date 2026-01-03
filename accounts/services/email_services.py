"""
Email Service - Handle email sending with HTML templates and attachments.

This service provides a centralized way to send emails with support for:
- HTML email templates
- Plain text messages
- File attachments
- Environment-based email service toggle
"""

import traceback
from typing import List, Optional, Tuple

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


class EmailService:
    """
    Service for sending emails with optional HTML templates and attachments.
    
    Features:
        - Plain text and HTML email support
        - Django template rendering
        - File attachments
        - Email obfuscation in logs for privacy
        - Environment-based service toggle
    """
    
    def __init__(self):
        """Initialize email service with environment configuration."""
        self.email_service_enabled = (settings.EMAIL_SERVICE == "1")
    
    def send_email(
        self,
        subject: str,
        recipient_list: List[str],
        message: Optional[str] = None,
        template_name: Optional[str] = None,
        context: Optional[dict] = None,
        attachments: Optional[List[Tuple[str, bytes, str]]] = None,
        is_html: bool = False
    ) -> bool:
        """
        Send an email with optional HTML content and attachments.
        
        Args:
            subject: Email subject line
            recipient_list: List of recipient email addresses
            message: Plain text message body (optional if template_name provided)
            template_name: Path to Django template file (optional)
            context: Template context dict (required if template_name provided)
            attachments: List of (filename, content, mime_type) tuples
            is_html: Whether to send as HTML email
            
        Returns:
            bool: True if email sent successfully, False otherwise
            
        Example:
            >>> service = EmailService()
            >>> service.send_email(
            ...     subject="Welcome",
            ...     recipient_list=["user@example.com"],
            ...     template_name="email/welcome.html",
            ...     context={"name": "John"},
            ...     is_html=True
            ... )
        """
        if not self.email_service_enabled:
            print(f"[Email Service Offline] {subject} - Email not sent")
            return False
        
        print(f"\n{subject} - Sending email...")
        
        try:
            # Render template if provided
            if template_name and context:
                message = render_to_string(template_name, context)
            
            # Create email message
            email = EmailMessage(
                subject=subject,
                body=message or "This is an automated notification.",
                from_email=settings.EMAIL_HOST_USER,
                to=recipient_list,
            )
            
            # Set HTML content type if requested
            if is_html:
                email.content_subtype = "html"
            
            # Add attachments if provided
            if attachments:
                for filename, content, mime_type in attachments:
                    email.attach(filename, content, mime_type)
            
            # Send email
            email_sent = email.send()
            
            if email_sent:
                # Log success with obfuscated email addresses
                obfuscated_emails = self._obfuscate_emails(recipient_list)
                print(f"{subject}: Email sent successfully to {', '.join(obfuscated_emails)}")
                return True
            else:
                print(f"{subject}: Email sending failed (no exception raised)")
                return False
                
        except Exception as e:
            print(f"{subject}: Email sending failed with exception")
            traceback.print_exc()
            return False
    
    @staticmethod
    def _obfuscate_emails(email_list: List[str]) -> List[str]:
        """
        Obfuscate email addresses for privacy in logs.
        
        Args:
            email_list: List of email addresses
            
        Returns:
            List of obfuscated email addresses
            
        Example:
            >>> _obfuscate_emails(["john@example.com"])
            ["jo******hn@example.com"]
        """
        obfuscated = []
        
        for email in email_list:
            try:
                local, domain = email.split("@")
                if len(local) <= 4:
                    # Short local part: show first 2 and last 2 chars
                    obfuscated_local = f"{local[:2]}****{local[-2:]}"
                else:
                    # Longer local part: show more context
                    obfuscated_local = f"{local[:2]}******{local[-2:]}"
                obfuscated.append(f"{obfuscated_local}@{domain}")
            except ValueError:
                # Invalid email format, return as-is
                obfuscated.append(email)
        
        return obfuscated
