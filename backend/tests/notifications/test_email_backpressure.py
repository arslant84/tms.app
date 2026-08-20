"""
Tests for async email dispatch via Celery (notifications/tasks.py).

Replaces the old thread-pool backpressure tests now that email sending
uses Celery + transaction.on_commit instead of a bounded ThreadPoolExecutor.
"""

from unittest.mock import MagicMock, call, patch

import pytest
from notifications.services import NotificationService
from notifications.tasks import send_notification_email


class TestSendEmailAsync:
    """send_email_async should schedule a Celery task, not block the caller."""

    @pytest.mark.django_db
    def test_enqueues_celery_task_on_commit(self, regular_user):
        """send_email_async must call apply_async inside a transaction.on_commit
        callback, not inline — so it never blocks the HTTP request."""
        from notifications.models import UserNotification

        notification = UserNotification.objects.create(
            user=regular_user,
            title="Test",
            message="Test message",
        )

        with patch("notifications.services.transaction") as mock_tx:
            # Capture the on_commit callback without actually running it
            captured = []
            mock_tx.on_commit.side_effect = lambda fn: captured.append(fn)

            NotificationService.send_email_async(notification)

            # on_commit must have been called exactly once
            assert mock_tx.on_commit.call_count == 1
            # The task must NOT have been dispatched yet (it's deferred to commit)
            assert len(captured) == 1

    @pytest.mark.django_db
    def test_task_dispatched_with_correct_notification_id(self, regular_user):
        """The on_commit callback must dispatch send_notification_email with
        the notification's PK."""
        from notifications.models import UserNotification

        notification = UserNotification.objects.create(
            user=regular_user,
            title="Test",
            message="Test message",
        )

        with patch("notifications.services.transaction") as mock_tx:
            captured = []
            mock_tx.on_commit.side_effect = lambda fn: captured.append(fn)

            NotificationService.send_email_async(notification)

        with patch("notifications.tasks.send_notification_email.apply_async") as mock_apply:
            # Simulate the transaction committing
            captured[0]()
            mock_apply.assert_called_once_with(
                args=[notification.id], queue="emails"
            )


class TestSendNotificationEmailTask:
    """Celery task: send_notification_email."""

    @pytest.mark.django_db
    def test_calls_send_email_notification(self, regular_user):
        """Task must call NotificationService.send_email_notification with the
        correct notification instance when the notification exists."""
        from notifications.models import UserNotification

        notification = UserNotification.objects.create(
            user=regular_user,
            title="Task test",
            message="Body",
        )

        # NotificationService is imported from notifications.services inside the
        # task, so patch it at its definition site.
        with patch(
            "notifications.services.NotificationService.send_email_notification"
        ) as mock_send:
            send_notification_email(notification.id)
            mock_send.assert_called_once()
            called_notification = mock_send.call_args[0][0]
            assert called_notification.id == notification.id

    @pytest.mark.django_db
    def test_missing_notification_is_a_noop(self, regular_user):
        """A deleted/missing notification must not raise — just log and return."""
        with patch(
            "notifications.services.NotificationService.send_email_notification"
        ) as mock_send:
            send_notification_email(999999)  # non-existent
            mock_send.assert_not_called()

    @pytest.mark.django_db
    def test_smtp_failure_triggers_retry(self, regular_user):
        """On SMTP failure the task must raise Retry so Celery reschedules it."""
        from celery.exceptions import Retry

        from notifications.models import UserNotification

        notification = UserNotification.objects.create(
            user=regular_user,
            title="Retry test",
            message="Body",
        )

        with patch(
            "notifications.services.NotificationService.send_email_notification",
            side_effect=Exception("SMTP timeout"),
        ):
            with pytest.raises(Retry):
                # CELERY_TASK_ALWAYS_EAGER + CELERY_TASK_EAGER_PROPAGATES means
                # self.retry() raises Retry immediately in tests
                send_notification_email.apply(args=[notification.id])
