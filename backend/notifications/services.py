"""
Notification service for creating and sending notifications
"""
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import (
    NotificationEventType, NotificationTemplate, UserNotification,
    UserNotificationPreference, UserNotificationSubscription
)
import re


class NotificationService:
    """Service for creating and sending notifications"""

    @staticmethod
    def create_notification(
        user,
        title,
        message,
        event_type=None,
        priority='normal',
        action_url=None,
        action_text='View',
        content_object=None,
        additional_data=None,
        send_email=False
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

        Returns:
            UserNotification instance
        """
        # Check user preferences
        try:
            preferences = user.notification_preferences
            if not preferences.in_app_notifications_enabled:
                return None
        except UserNotificationPreference.DoesNotExist:
            # Create default preferences
            UserNotificationPreference.objects.create(user=user)

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
            additional_data=additional_data
        )

        # Send email if requested and user has email notifications enabled
        if send_email:
            try:
                preferences = user.notification_preferences
                if preferences.email_notifications_enabled:
                    NotificationService.send_email_notification(notification)
            except Exception as e:
                notification.email_error = str(e)
                notification.save()

        return notification

    @staticmethod
    def send_email_notification(notification):
        """
        Send email for a notification

        Args:
            notification: UserNotification instance
        """
        try:
            # Get email template if event type has one
            subject = notification.title
            message_body = notification.message

            if notification.event_type:
                template = notification.event_type.templates.filter(is_active=True).first()
                if template and template.email_subject:
                    subject = NotificationService._render_template(
                        template.email_subject,
                        notification
                    )
                    if template.email_body:
                        message_body = NotificationService._render_template(
                            template.email_body,
                            notification
                        )

            # Send email
            send_mail(
                subject=subject,
                message=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.user.email],
                fail_silently=False,
            )

            # Update notification
            notification.sent_via_email = True
            notification.email_sent_at = timezone.now()
            notification.save(update_fields=['sent_via_email', 'email_sent_at'])

        except Exception as e:
            notification.email_error = str(e)
            notification.save(update_fields=['email_error'])
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
            'user_name': notification.user.get_full_name(),
            'user_email': notification.user.email,
            'title': notification.title,
            'message': notification.message,
            'action_url': notification.action_url or '',
            'action_text': notification.action_text,
        }

        # Add additional data to context
        if notification.additional_data:
            context.update(notification.additional_data)

        # Simple template rendering
        result = template_string
        for key, value in context.items():
            result = result.replace(f'{{{{{key}}}}}', str(value))

        return result

    @staticmethod
    def notify_users(
        user_ids,
        title,
        message,
        event_type_name=None,
        priority='normal',
        action_url=None,
        action_text='View',
        content_object=None,
        additional_data=None,
        send_email=False
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
                    name=event_type_name,
                    is_active=True
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
                send_email=send_email
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
        priority='normal',
        action_url=None,
        action_text='View',
        content_object=None,
        additional_data=None,
        send_email=False
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
        user_ids = list(users.values_list('id', flat=True))

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
            send_email=send_email
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
        count = UserNotification.objects.filter(
            user=user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

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
            is_read=True,
            read_at__lt=cutoff_date
        ).delete()

        return count
