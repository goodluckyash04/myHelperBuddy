"""
FCM (Firebase Cloud Messaging) Service

Provides push notification delivery to registered user devices.
Uses fcm-django for token management and firebase-admin for delivery.

Usage:
    from accounts.services.fcm_service import fcm_service
    fcm_service.send_reminder(user, reminder)
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class FCMService:
    """
    Service for sending Firebase Cloud Messaging push notifications.

    Features:
        - Per-user device targeting (all registered devices)
        - Structured notification payloads (title, body, data)
        - Domain-specific helpers for reminders, tasks, and ledger alerts
        - Graceful failure — never raises; always logs errors
    """

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _send(self, user, title: str, body: str, data: Optional[Dict[str, str]] = None) -> bool:
        """
        Internal: send a notification to ALL devices registered by *user*.

        Args:
            user:  Django User instance
            title: Notification title string
            body:  Notification body string
            data:  Optional extra key-value dict (values must be strings)

        Returns:
            bool: True if at least one device was notified successfully
        """
        try:
            from fcm_django.models import FCMDevice  # lazy import — avoids circular deps
            from firebase_admin import messaging

            devices = FCMDevice.objects.filter(user=user, active=True)
            if not devices.exists():
                logger.debug("No active FCM devices for user %s — skipping push", user.username)
                return False

            tokens = [device.registration_id for device in devices]
            notification = messaging.Notification(title=title, body=body)
            data_payload = {k: str(v) for k, v in (data or {}).items()}

            message = messaging.MulticastMessage(
                notification=notification,
                data=data_payload,
                tokens=tokens,
                android=messaging.AndroidConfig(priority="high"),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", badge=1)
                    )
                ),
            )
            
            response = messaging.send_each_for_multicast(message)
            logger.debug("Multicast push sent for user %s. Success count: %d, Failure count: %d", 
                         user.username, response.success_count, response.failure_count)
            
            if response.failure_count > 0:
                # Deactivate stale tokens automatically
                for i, res in enumerate(response.responses):
                    if not res.success:
                        error_code = getattr(res.exception, 'code', '')
                        if error_code in ('NOT_FOUND', 'UNREGISTERED'):
                            stale_device = devices[i]
                            logger.warning("Deactivating stale token for user %s (device %s)", user.username, stale_device.pk)
                            stale_device.active = False
                            stale_device.save(update_fields=["active"])

            if response.success_count > 0:
                logger.info("Push notification '%s' delivered to %d device(s) for user %s",
                            title, response.success_count, user.username)
            return response.success_count > 0

        except ImportError as e:
            logger.error("FCM dependencies not installed: %s", e)
            return False
        except Exception as e:
            logger.error("FCM send error for user %s: %s", getattr(user, 'username', '?'), e)
            return False

    # =========================================================================
    # Public API
    # =========================================================================

    def send_to_user(
        self,
        user,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Send an arbitrary push notification to a user's devices.

        Args:
            user:  Django User instance
            title: Notification title
            body:  Notification body
            data:  Optional extra data dict (string values only)

        Returns:
            bool: True if at least one device received the notification

        Example:
            >>> fcm_service.send_to_user(user, "Hello!", "You have a new message")
        """
        return self._send(user, title, body, data)

    def send_reminder(self, user, reminder) -> bool:
        """
        Send a reminder push notification.

        Args:
            user:     Django User instance
            reminder: Reminder model instance (must have title, description, id)

        Returns:
            bool: True if delivered to at least one device

        Example:
            >>> fcm_service.send_reminder(user, reminder_obj)
        """
        title = f"⏰ Reminder: {reminder.title}"
        body = reminder.description or "You have a reminder due today."
        data = {
            "type": "reminder",
            "id": str(reminder.id),
            "url": f"/view-reminder/",
        }
        return self._send(user, title, body, data)

    def send_task_due(self, user, task) -> bool:
        """
        Send a task-due push notification.

        Args:
            user: Django User instance
            task: Task model instance (must have name, priority, id)

        Returns:
            bool: True if delivered to at least one device

        Example:
            >>> fcm_service.send_task_due(user, task_obj)
        """
        priority_label = getattr(task, 'priority', 'Normal')
        title = f"📋 Task Due: {task.name}"
        body = f"Priority: {priority_label} — due today or tomorrow."
        data = {
            "type": "task",
            "id": str(task.id),
            "url": f"/taskReports/",
        }
        return self._send(user, title, body, data)

    def send_overdue_ledger(self, user, entry) -> bool:
        """
        Send an overdue ledger entry push notification.

        Args:
            user:  Django User instance
            entry: LedgerTransaction model instance (must have counterparty_name,
                   remaining_amount, id)

        Returns:
            bool: True if delivered to at least one device

        Example:
            >>> fcm_service.send_overdue_ledger(user, ledger_entry)
        """
        name = getattr(entry, 'counterparty_name', 'Unknown')
        amount = getattr(entry, 'remaining_amount', 0)
        title = f"⚠️ Overdue: {name}"
        body = f"₹{amount} remaining — payment is overdue."
        data = {
            "type": "ledger",
            "id": str(entry.id),
            "url": f"/ledger-transaction-details/",
        }
        return self._send(user, title, body, data)


# Singleton — import this everywhere
fcm_service = FCMService()
