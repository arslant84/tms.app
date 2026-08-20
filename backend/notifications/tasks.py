import logging

from celery import shared_task

logger = logging.getLogger("notifications")


@shared_task(
    bind=True,
    max_retries=3,
    queue="emails",
    soft_time_limit=60,
    time_limit=120,
)
def send_notification_email(self, notification_id):
    """
    Send a single notification email in a Celery worker.

    Retries up to 3 times with exponential backoff on transient failures
    (SMTP timeouts, connection resets, transient DB errors).
    """
    from django.db import OperationalError

    from .models import UserNotification
    from .services import NotificationService

    try:
        notification = UserNotification.objects.get(pk=notification_id)
    except UserNotification.DoesNotExist:
        logger.error("Notification %s not found — skipping email send", notification_id)
        return
    except OperationalError as exc:
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    try:
        NotificationService.send_email_notification(notification)
    except Exception as exc:
        countdown = 60 * (2 ** self.request.retries)
        logger.warning(
            "Email send failed for notification %s (attempt %d), retrying in %ds: %s",
            notification_id,
            self.request.retries + 1,
            countdown,
            exc,
        )
        raise self.retry(exc=exc, countdown=countdown)
