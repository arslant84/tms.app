"""
Regression tests for the bounded email-sending executor (2026-07-23).

NotificationService.send_email_async used to spawn one raw daemon
threading.Thread per email with no cap and no backpressure - a loop like
notify_role() with many recipients could fire dozens of concurrent SMTP
connections from a single request. Replaced with a bounded ThreadPoolExecutor
gated by a BoundedSemaphore: at most EMAIL_QUEUE_MAX_SIZE tasks in flight or
queued at once; submission never blocks the caller, it's rejected instantly
and the notification is marked with an email_error instead.
"""

from unittest.mock import patch

import pytest
from notifications import services as notification_services
from notifications.services import NotificationService


class TestEmailBackpressure:
    def test_email_send_uses_bounded_executor_not_raw_thread(self):
        """A submitted task must actually run on the pool (not just get
        silently dropped) and the caller must be able to wait on it.

        Uses a plain callable rather than a DB-touching one, since the pool
        thread runs on its own DB connection - see
        test_saturated_queue_is_rejected_not_blocked for the DB-touching
        (synchronous, same-connection) case instead.
        """
        calls = []
        future = notification_services._submit_bounded_email_task(calls.append, "sent")
        assert future is not None
        future.result(timeout=5)  # block test until the pool thread finishes

        assert calls == ["sent"]

    @pytest.mark.django_db
    def test_saturated_queue_is_rejected_not_blocked(self, regular_user):
        """When the bounded semaphore has no permits left, submission must
        return None immediately (not block the caller) and the caller
        (send_email_async) must record an email_error."""
        from notifications.models import UserNotification

        notification = UserNotification.objects.create(
            user=regular_user,
            title="Test",
            message="Test message",
        )

        # Exhaust every permit without releasing, simulating a saturated
        # queue, then restore them in `finally` so this doesn't leak state
        # into other tests sharing this module-level semaphore.
        acquired = []
        try:
            while notification_services._email_queue_semaphore.acquire(blocking=False):
                acquired.append(1)

            with patch.object(notification_services, "send_mail") as mock_send_mail:
                NotificationService.send_email_async(notification)
                mock_send_mail.assert_not_called()
        finally:
            for _ in acquired:
                notification_services._email_queue_semaphore.release()

        notification.refresh_from_db()
        assert notification.email_error == "Email queue saturated - send dropped"

    def test_pool_is_bounded_to_configured_worker_count(self):
        assert (
            notification_services._email_executor._max_workers
            == notification_services.EMAIL_EXECUTOR_MAX_WORKERS
        )
