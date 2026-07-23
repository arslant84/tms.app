"""
Notification service for creating and sending notifications
"""

import logging
import re
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.utils import timezone

from .models import (
    NotificationEventType,
    NotificationTemplate,
    UserNotification,
    UserNotificationPreference,
    UserNotificationSubscription,
)

logger = logging.getLogger(__name__)

# Bounded, in-process email-sending pool. Replaces one raw threading.Thread
# per email (unbounded thread creation, no backpressure — a real risk for
# loops like NotificationService.notify_role/notify_users, which can create
# dozens of notifications in one request). Per Gunicorn worker process:
# at most EMAIL_EXECUTOR_MAX_WORKERS threads running at once, at most
# EMAIL_QUEUE_MAX_SIZE tasks in flight or queued — beyond that, submission
# is rejected immediately (never blocks the calling HTTP request) and the
# notification is marked with an email_error instead of being sent.
EMAIL_EXECUTOR_MAX_WORKERS = 8
EMAIL_QUEUE_MAX_SIZE = 200

_email_executor = ThreadPoolExecutor(
    max_workers=EMAIL_EXECUTOR_MAX_WORKERS,
    thread_name_prefix="email-notify",
)
_email_queue_semaphore = threading.BoundedSemaphore(EMAIL_QUEUE_MAX_SIZE)


def _submit_bounded_email_task(fn, *args, **kwargs):
    """
    Submit a task to the bounded email executor. Returns the Future on
    success, or None if the queue is saturated (task is dropped, not
    blocked — a saturated queue must never stall the calling request).
    """
    if not _email_queue_semaphore.acquire(blocking=False):
        logger.error(
            "Email queue saturated (%d in flight) - dropping email send",
            EMAIL_QUEUE_MAX_SIZE,
        )
        return None

    def _wrapped():
        try:
            fn(*args, **kwargs)
        finally:
            _email_queue_semaphore.release()

    return _email_executor.submit(_wrapped)


class NotificationService:
    """Service for creating and sending notifications"""

    @staticmethod
    def create_notification(
        user,
        title,
        message,
        event_type=None,
        priority="normal",
        action_url=None,
        action_text="View",
        content_object=None,
        additional_data=None,
        send_email=False,
        bypass_subscription_check=False,
    ):
        """
        Create a notification for a user

        Args:
            user: User instance
            title: Notification title
            message: Notification message
            event_type: NotificationEventType instance (optional)
            priority: Priority level ('low', 'normal', 'high', 'urgent')
            action_url: URL for the notification action
            action_text: Text for the action button
            content_object: Related model instance
            additional_data: Additional JSON data
            send_email: Whether to send email notification
            bypass_subscription_check: Skip subscription check (for critical notifications)

        Returns:
            UserNotification instance
        """
        # Get or create user preferences
        try:
            preferences = user.notification_preferences
        except UserNotificationPreference.DoesNotExist:
            preferences = UserNotificationPreference.objects.create(user=user)

        # Check global in-app notifications setting
        if not preferences.in_app_notifications_enabled:
            logger.info(
                f"In-app notifications disabled for user {user.email} - skipping"
            )
            return None

        # Check event type subscription (if event_type provided and not bypassed)
        if event_type and not bypass_subscription_check:
            subscription = UserNotificationSubscription.objects.filter(
                user=user, event_type=event_type, is_active=True
            ).first()

            if subscription and not subscription.receive_in_app:
                logger.info(
                    f"User {user.email} unsubscribed from in-app for event {event_type.name} - skipping in-app"
                )
                # Still might send email if subscribed to email
                if (
                    send_email
                    and subscription.receive_email
                    and preferences.email_notifications_enabled
                ):
                    # Create notification just for email tracking, mark as read immediately
                    pass
                else:
                    return None

        # Create content type reference if content_object provided
        content_type = None
        object_id = None
        if content_object:
            content_type = ContentType.objects.get_for_model(content_object)
            object_id = content_object.pk

        # Create notification
        notification = UserNotification.objects.create(
            user=user,
            event_type=event_type,
            title=title,
            message=message,
            content_type=content_type,
            object_id=object_id,
            action_url=action_url,
            action_text=action_text,
            priority=priority,
            additional_data=additional_data,
        )

        # Send email if requested and user has email notifications enabled
        if send_email:
            try:
                # Check global email preference
                if not preferences.email_notifications_enabled:
                    logger.info(
                        f"Email notifications disabled for user {user.email} - skipping email"
                    )
                else:
                    # Check event-specific email subscription
                    should_send_email = True
                    if event_type and not bypass_subscription_check:
                        subscription = UserNotificationSubscription.objects.filter(
                            user=user, event_type=event_type, is_active=True
                        ).first()
                        if subscription and not subscription.receive_email:
                            should_send_email = False
                            logger.info(
                                f"User {user.email} unsubscribed from email for event {event_type.name}"
                            )

                    if should_send_email:
                        # Send email asynchronously in background thread
                        NotificationService.send_email_async(notification)
            except Exception as e:
                notification.email_error = str(e)
                notification.save()

        return notification

    @staticmethod
    def send_email_async(notification):
        """
        Send email asynchronously via the bounded email executor.
        This prevents blocking the HTTP request while waiting for SMTP,
        without spawning an unbounded number of threads (see the
        EMAIL_EXECUTOR_MAX_WORKERS/EMAIL_QUEUE_MAX_SIZE pool defined at
        module scope).

        Args:
            notification: UserNotification instance
        """

        def _send_in_background():
            try:
                NotificationService.send_email_notification(notification)
            except Exception as e:
                # Error is already logged in send_email_notification
                logger.error(
                    f"Background email send failed for notification {notification.id}: {str(e)}"
                )
            finally:
                # This runs on a pool thread outside Django's request_finished
                # signal, which is what normally closes DB connections -
                # without this, each send leaks a Postgres connection that
                # never gets reclaimed.
                from django.db import connection

                connection.close()

        future = _submit_bounded_email_task(_send_in_background)
        if future is None:
            notification.email_error = "Email queue saturated - send dropped"
            notification.save(update_fields=["email_error"])
            return

        logger.info(f"Email queued for background sending to {notification.user.email}")

    @staticmethod
    def send_email_notification(notification):
        """
        Send email for a notification with enhanced error logging

        Args:
            notification: UserNotification instance
        """
        logger.info(
            f"Starting email notification send to {notification.user.email} (Notification ID: {notification.id})"
        )

        try:
            # Check if email notifications are globally enabled
            from accounts.models import ApplicationSetting

            email_notifications_enabled = ApplicationSetting.get_setting(
                "enable_email_notifications", True
            )

            if not email_notifications_enabled:
                # Email notifications are disabled globally
                logger.warning(
                    f"Email notifications disabled globally - skipping notification {notification.id}"
                )
                notification.email_error = "Email notifications are disabled globally"
                notification.save(update_fields=["email_error"])
                return

            # Validate recipient email
            if not notification.user.email:
                error_msg = f"User {notification.user.id} has no email address"
                logger.error(error_msg)
                notification.email_error = error_msg
                notification.save(update_fields=["email_error"])
                return

            # Get email template if event type has one
            subject = notification.title
            message_body = notification.message
            html_message_body = None

            if notification.event_type:
                logger.debug(
                    f"Using event type template: {notification.event_type.name}"
                )
                template = notification.event_type.templates.filter(
                    is_active=True
                ).first()
                if template and template.subject:
                    # Render subject with variables
                    subject = NotificationService._render_template(
                        template.subject, notification
                    )
                    if template.body:
                        # Step 1: Render template with variables
                        rendered_body = NotificationService._render_template(
                            template.body, notification
                        )

                        # Step 2: Convert markdown to HTML
                        try:
                            from notifications.utils.markdown_to_html import (
                                markdown_to_html,
                            )

                            html_content = markdown_to_html(rendered_body)
                            logger.debug(
                                f"Converted markdown to HTML for notification {notification.id}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Markdown conversion failed, using plain text: {str(e)}"
                            )
                            html_content = rendered_body

                        # Step 3: Wrap in base HTML email template
                        try:
                            from notifications.email_renderer import (
                                EmailTemplateRenderer,
                            )

                            html_message_body = EmailTemplateRenderer.render_email(
                                subject=subject,
                                content=html_content,
                                user_name=notification.user.get_full_name(),
                                action_url=notification.action_url,
                                action_text=notification.action_text or "View Details",
                            )
                            logger.debug(
                                f"Wrapped content in HTML email template for notification {notification.id}"
                            )

                            # Create plain text version by stripping HTML tags
                            message_body = re.sub("<[^<]+?>", "", html_message_body)
                            message_body = re.sub(
                                r"\n\s*\n\s*\n", "\n\n", message_body
                            )  # Clean up extra newlines
                            message_body = message_body.strip()

                        except Exception as e:
                            logger.warning(
                                f"HTML template wrapping failed, using converted markdown: {str(e)}"
                            )
                            html_message_body = html_content
                            message_body = re.sub("<[^<]+?>", "", html_content)

                        logger.debug(
                            f"Rendered HTML email template for notification {notification.id}"
                        )

            # Log SMTP configuration being used
            logger.debug(
                f"SMTP Config - Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}, TLS: {settings.EMAIL_USE_TLS}"
            )

            # Send email with HTML support
            logger.info(
                f"Sending email to {notification.user.email} - Subject: '{subject}'"
            )
            send_mail(
                subject=subject,
                message=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.user.email],
                fail_silently=False,
                html_message=html_message_body,  # HTML version for email clients that support it
            )

            # Update notification
            notification.sent_via_email = True
            notification.email_sent_at = timezone.now()
            notification.save(update_fields=["sent_via_email", "email_sent_at"])

            logger.info(
                f"[OK] Email sent successfully to {notification.user.email} (Notification ID: {notification.id})"
            )

        except Exception as e:
            # Enhanced error logging with full traceback
            error_msg = str(e)
            error_type = type(e).__name__

            logger.error(
                f"[ERROR] Email sending failed for notification {notification.id}\n"
                f"   Error Type: {error_type}\n"
                f"   Error Message: {error_msg}\n"
                f"   Recipient: {notification.user.email}\n"
                f"   Subject: {notification.title}\n"
                f"   SMTP Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}\n"
                f"   From: {settings.DEFAULT_FROM_EMAIL}\n"
                f"   Full Traceback:\n{traceback.format_exc()}"
            )

            # Store detailed error in database
            notification.email_error = f"[{error_type}] {error_msg}"
            notification.save(update_fields=["email_error"])

            # Re-raise to allow higher-level error handling
            raise

    @staticmethod
    def _render_template(template_string, notification):
        """
        Render template string with notification data

        Args:
            template_string: Template with {{variable}} placeholders
            notification: UserNotification instance

        Returns:
            Rendered string
        """
        context = {
            "user_name": notification.user.get_full_name(),
            "user_email": notification.user.email,
            "title": notification.title,
            "message": notification.message,
            "action_url": notification.action_url or "",
            "action_text": notification.action_text,
        }

        # Add additional data to context
        if notification.additional_data:
            context.update(notification.additional_data)

        # Simple template rendering
        result = template_string
        for key, value in context.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))

        return result

    @staticmethod
    def notify_users(
        user_ids,
        title,
        message,
        event_type_name=None,
        priority="normal",
        action_url=None,
        action_text="View",
        content_object=None,
        additional_data=None,
        send_email=False,
    ):
        """
        Send notifications to multiple users

        Args:
            user_ids: List of user IDs
            title: Notification title
            message: Notification message
            event_type_name: Event type name (optional)
            priority: Priority level
            action_url: URL for action
            action_text: Action button text
            content_object: Related object
            additional_data: Additional data
            send_email: Send via email

        Returns:
            List of created notifications
        """
        from accounts.models import User

        # Get event type if specified
        event_type = None
        if event_type_name:
            try:
                event_type = NotificationEventType.objects.get(
                    name=event_type_name, is_active=True
                )
            except NotificationEventType.DoesNotExist:
                pass

        # Get users
        users = User.objects.filter(id__in=user_ids)

        notifications = []
        for user in users:
            notification = NotificationService.create_notification(
                user=user,
                title=title,
                message=message,
                event_type=event_type,
                priority=priority,
                action_url=action_url,
                action_text=action_text,
                content_object=content_object,
                additional_data=additional_data,
                send_email=send_email,
            )
            if notification:
                notifications.append(notification)

        return notifications

    @staticmethod
    def notify_role(
        role_name,
        title,
        message,
        event_type_name=None,
        priority="normal",
        action_url=None,
        action_text="View",
        content_object=None,
        additional_data=None,
        send_email=False,
    ):
        """
        Send notifications to all users with a specific role

        Args:
            role_name: Role name to notify
            (other args same as notify_users)

        Returns:
            List of created notifications
        """
        from accounts.models import User

        # Get users with this role
        users = User.objects.filter(role__name=role_name)
        user_ids = list(users.values_list("id", flat=True))

        return NotificationService.notify_users(
            user_ids=user_ids,
            title=title,
            message=message,
            event_type_name=event_type_name,
            priority=priority,
            action_url=action_url,
            action_text=action_text,
            content_object=content_object,
            additional_data=additional_data,
            send_email=send_email,
        )

    @staticmethod
    def mark_all_as_read(user):
        """
        Mark all notifications as read for a user

        Args:
            user: User instance

        Returns:
            Number of notifications marked as read
        """
        count = UserNotification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )

        return count

    @staticmethod
    def delete_old_notifications(days=30):
        """
        Delete old read notifications

        Args:
            days: Number of days to keep notifications

        Returns:
            Number of notifications deleted
        """
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days)

        count, _ = UserNotification.objects.filter(
            is_read=True, read_at__lt=cutoff_date
        ).delete()

        return count
