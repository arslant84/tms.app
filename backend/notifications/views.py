import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework.response import Response


class CanManageNotifications(BasePermission):
    """Allows access to superusers, or users with manage_notifications or view_system_settings permission."""

    def has_permission(self, request, view):
        return (
            request.user.is_superuser
            or has_permission(request.user, "manage_notifications")
            or has_permission(request.user, "view_system_settings")
        )


from datetime import datetime, timedelta

from accounts.utils import can_manage, has_permission
from django.db.models import Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)
from utils.api_response import (
    created_response,
    error_response,
    forbidden_response,
    success_response,
    validation_error_response,
)

from .models import (
    NotificationBatch,
    NotificationEventType,
    NotificationTemplate,
    UserNotification,
    UserNotificationPreference,
    UserNotificationSubscription,
)
from .serializers import (
    NotificationBatchSerializer,
    NotificationEventTypeSerializer,
    NotificationStatsSerializer,
    NotificationTemplateListSerializer,
    NotificationTemplateSerializer,
    UserNotificationCreateSerializer,
    UserNotificationPreferenceSerializer,
    UserNotificationSerializer,
    UserNotificationSubscriptionSerializer,
)
from .services import NotificationService


class NotificationEventTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification event types (admin only)
    """

    queryset = NotificationEventType.objects.all()
    serializer_class = NotificationEventTypeSerializer
    permission_classes = [IsAuthenticated, CanManageNotifications]
    pagination_class = None  # Disable pagination

    def get_queryset(self):
        """Filter event types by module and status"""
        queryset = super().get_queryset()

        module = self.request.query_params.get("module", None)
        if module:
            queryset = queryset.filter(module=module)

        is_active = self.request.query_params.get("is_active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("module", "category", "name")


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification templates (admin only)
    """

    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated, CanManageNotifications]
    pagination_class = None  # Disable pagination

    def get_serializer_class(self):
        """Use list serializer for list action (without body field)"""
        if self.action == "list":
            return NotificationTemplateListSerializer
        return NotificationTemplateSerializer

    def get_queryset(self):
        """Filter templates by event type, module, and status"""
        queryset = super().get_queryset()

        event_type_id = self.request.query_params.get("event_type", None)
        if event_type_id:
            queryset = queryset.filter(event_type_id=event_type_id)

        module = self.request.query_params.get("module", None)
        if module:
            queryset = queryset.filter(event_type__module=module)

        notification_type = self.request.query_params.get("notification_type", None)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        recipient_type = self.request.query_params.get("recipient_type", None)
        if recipient_type:
            queryset = queryset.filter(recipient_type=recipient_type)

        is_active = self.request.query_params.get("is_active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.select_related("event_type").order_by("name")


class UserNotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notification preferences
    """

    serializer_class = UserNotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only see their own preferences"""
        user = self.request.user
        # All users only see their own preferences
        return UserNotificationPreference.objects.filter(user=user)

    def perform_create(self, serializer):
        """Set user to current user"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def my_preferences(self, request):
        """Get current user's preferences"""
        try:
            preferences = request.user.notification_preferences
        except UserNotificationPreference.DoesNotExist:
            # Create default preferences
            preferences = UserNotificationPreference.objects.create(user=request.user)

        serializer = self.get_serializer(preferences)
        return Response(serializer.data)

    @action(detail=False, methods=["put", "patch"])
    def update_my_preferences(self, request):
        """Update current user's preferences"""
        try:
            preferences = request.user.notification_preferences
        except UserNotificationPreference.DoesNotExist:
            preferences = UserNotificationPreference.objects.create(user=request.user)

        serializer = self.get_serializer(preferences, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class UserNotificationSubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notification subscriptions
    """

    serializer_class = UserNotificationSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only see their own subscriptions"""
        user = self.request.user

        # All users only see their own subscriptions
        queryset = UserNotificationSubscription.objects.filter(user=user)

        # Filter by event type
        event_type_id = self.request.query_params.get("event_type", None)
        if event_type_id:
            queryset = queryset.filter(event_type_id=event_type_id)

        return queryset.select_related("user", "event_type")

    def perform_create(self, serializer):
        """Set user to current user"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def my_subscriptions(self, request):
        """Get current user's subscriptions"""
        subscriptions = request.user.notification_subscriptions.filter(is_active=True)
        serializer = self.get_serializer(subscriptions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post", "put", "patch"])
    def update_subscription(self, request, pk=None):
        """
        Create or update subscription for an event type.
        The pk here is the event_type_id.
        """
        try:
            event_type = NotificationEventType.objects.get(pk=pk, is_active=True)
        except NotificationEventType.DoesNotExist:
            return error_response(
                message="Event type not found or inactive",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Get or create subscription for this user and event type
        subscription, created = UserNotificationSubscription.objects.get_or_create(
            user=request.user,
            event_type=event_type,
            defaults={
                "receive_email": request.data.get("receive_email", True),
                "receive_in_app": request.data.get("receive_in_app", True),
                "receive_push": request.data.get("receive_push", False),
                "is_active": True,
            },
        )

        if not created:
            # Update existing subscription
            subscription.receive_email = request.data.get(
                "receive_email", subscription.receive_email
            )
            subscription.receive_in_app = request.data.get(
                "receive_in_app", subscription.receive_in_app
            )
            subscription.receive_push = request.data.get(
                "receive_push", subscription.receive_push
            )
            subscription.is_active = request.data.get(
                "is_active", subscription.is_active
            )
            subscription.save()

        serializer = self.get_serializer(subscription)
        return success_response(
            data=serializer.data,
            message="Subscription updated successfully",
            status_code=status.HTTP_200_OK,
        )


class UserNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notifications
    """

    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]

    # Search across notification content
    search_fields = ["title", "message"]

    # Allow ordering
    ordering_fields = ["created_at", "priority", "is_read"]
    ordering = ["-created_at"]  # Default: newest first

    def get_queryset(self):
        """Users can only see their own notifications"""
        user = self.request.user

        # All users (including admins) only see notifications sent to them
        # Notifications are created for the appropriate users by the notification service
        queryset = UserNotification.objects.filter(user=user)
        logger.info(
            f"User {user.email or user.username} - showing only notifications sent to them"
        )

        # Filter by read status
        is_read = self.request.query_params.get("is_read", None)
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == "true")

        # Filter by priority
        priority = self.request.query_params.get("priority", None)
        if priority:
            queryset = queryset.filter(priority=priority)

        # Filter by event type
        event_type_id = self.request.query_params.get("event_type", None)
        if event_type_id:
            queryset = queryset.filter(event_type_id=event_type_id)

        # Filter by date range
        from_date = self.request.query_params.get("from_date", None)
        to_date = self.request.query_params.get("to_date", None)
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)

        return queryset.select_related("user", "event_type", "content_type")

    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action == "create":
            return UserNotificationCreateSerializer
        return UserNotificationSerializer

    def create(self, request, *args, **kwargs):
        """Create notifications for multiple users (requires notification permission)"""
        if not request.user.is_superuser and not can_manage(
            request.user, "notification"
        ):
            return forbidden_response(message="Only admin can create notifications")

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid notification data"
            )

        # Create notifications using service
        notifications = NotificationService.notify_users(
            user_ids=serializer.validated_data["recipient_ids"],
            title=serializer.validated_data["title"],
            message=serializer.validated_data["message"],
            priority=serializer.validated_data.get("priority", "normal"),
            action_url=serializer.validated_data.get("action_url"),
            action_text=serializer.validated_data.get("action_text", "View"),
            send_email=serializer.validated_data.get("send_email", False),
            additional_data=serializer.validated_data.get("additional_data"),
        )

        response_serializer = UserNotificationSerializer(notifications, many=True)
        return created_response(
            data=response_serializer.data,
            message=f"Created {len(notifications)} notification(s)",
        )

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()

        is_admin = request.user.is_superuser or can_manage(request.user, "notification")
        if notification.user != request.user and not is_admin:
            return forbidden_response(
                message="You can only mark your own notifications as read"
            )

        notification.mark_as_read()

        serializer = self.get_serializer(notification)
        return success_response(
            data=serializer.data,
            message="Notification marked as read",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def mark_as_unread(self, request, pk=None):
        """Mark a notification as unread"""
        notification = self.get_object()

        is_admin = request.user.is_superuser or can_manage(request.user, "notification")
        if notification.user != request.user and not is_admin:
            return forbidden_response(
                message="You can only mark your own notifications as unread"
            )

        notification.is_read = False
        notification.read_at = None
        notification.save(update_fields=["is_read", "read_at"])

        serializer = self.get_serializer(notification)
        return success_response(
            data=serializer.data,
            message="Notification marked as unread",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def mark_all_as_read(self, request):
        """Mark all notifications as read for current user"""
        count = NotificationService.mark_all_as_read(request.user)
        return success_response(
            data={"count": count},
            message=f"{count} notifications marked as read",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = UserNotification.objects.filter(
            user=request.user, is_read=False
        ).count()

        return success_response(
            data={"count": count},
            message="Unread count retrieved",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get notification statistics for current user"""
        user = request.user
        notifications = UserNotification.objects.filter(user=user)

        # Calculate statistics
        total_notifications = notifications.count()
        unread_count = notifications.filter(is_read=False).count()
        urgent_count = notifications.filter(priority="urgent", is_read=False).count()

        # Today's notifications
        today = timezone.now().date()
        today_count = notifications.filter(created_at__date=today).count()

        # By priority
        by_priority = dict(
            notifications.values("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        )

        # By module (via event type)
        by_module = dict(
            notifications.exclude(event_type__isnull=True)
            .values("event_type__module")
            .annotate(count=Count("id"))
            .values_list("event_type__module", "count")
        )

        stats = {
            "total_notifications": total_notifications,
            "unread_count": unread_count,
            "urgent_count": urgent_count,
            "today_count": today_count,
            "by_priority": by_priority,
            "by_module": by_module,
        }

        serializer = NotificationStatsSerializer(stats)
        return success_response(
            data=serializer.data,
            message="Notification statistics retrieved successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["delete"])
    def clear_read(self, request):
        """Delete all read notifications for current user"""
        count, _ = UserNotification.objects.filter(
            user=request.user, is_read=True
        ).delete()

        return success_response(
            data={"count": count},
            message=f"{count} read notification(s) deleted",
            status_code=status.HTTP_200_OK,
        )


class NotificationBatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notification batches
    """

    queryset = NotificationBatch.objects.all()
    serializer_class = NotificationBatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only see their own batches"""
        user = self.request.user

        # All users only see their own batches
        queryset = NotificationBatch.objects.filter(user=user)

        # Filter by frequency
        frequency = self.request.query_params.get("frequency", None)
        if frequency:
            queryset = queryset.filter(frequency=frequency)

        # Filter by sent status
        is_sent = self.request.query_params.get("is_sent", None)
        if is_sent is not None:
            queryset = queryset.filter(is_sent=is_sent.lower() == "true")

        return queryset.select_related("user")
