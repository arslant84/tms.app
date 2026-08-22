import logging

from celery import shared_task

logger = logging.getLogger("notifications")


@shared_task(
    bind=True,
    max_retries=3,
    queue="emails",
    soft_time_limit=60,
    time_limit=120,
    ignore_result=True,
)
def send_notification_email(self, notification_id):
    """
    Send a single notification email in a Celery worker.

    Retries up to 3 times with exponential backoff on transient failures
    (SMTP timeouts, connection resets, transient DB errors).

    ignore_result=True: nothing in this codebase ever reads this task's
    result (unlike the tasks task_views.py's generic task_status endpoint
    polls) - it's pure fire-and-forget. Without it, apply_async() also
    has to talk to the Redis *result* backend (not just the broker) to
    initialize state tracking, so a transient Redis blip during dispatch
    turns into the caller's request thread retrying that connection (up
    to 20 times, ~65s) and ultimately erroring out the whole request -
    even though the workflow/notification had already been created and
    committed successfully by that point. Seen live: a transport request
    submission logged "Workflow started" and "Notifications sent"
    successfully, then still surfaced as a failed request once Redis
    dropped mid-dispatch.
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
        countdown = 30 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    try:
        NotificationService.send_email_notification(notification)
    except Exception as exc:
        countdown = 60 * (2**self.request.retries)
        logger.warning(
            "Email send failed for notification %s (attempt %d), retrying in %ds: %s",
            notification_id,
            self.request.retries + 1,
            countdown,
            exc,
        )
        raise self.retry(exc=exc, countdown=countdown)
