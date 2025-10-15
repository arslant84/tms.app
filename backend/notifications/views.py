from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta

from .models import (
    NotificationEventType, NotificationTemplate, UserNotificationPreference,
    UserNotificationSubscription, UserNotification, NotificationBatch
)
from .serializers import (
    NotificationEventTypeSerializer, NotificationTemplateSerializer,
    UserNotificationPreferenceSerializer, UserNotificationSubscriptionSerializer,
    UserNotificationSerializer, UserNotificationCreateSerializer,
    NotificationBatchSerializer, NotificationStatsSerializer
)
from .services import NotificationService


class NotificationEventTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification event types (admin only)
    """
    queryset = NotificationEventType.objects.all()
    serializer_class = NotificationEventTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """Filter event types by module and status"""
        queryset = super().get_queryset()

        module = self.request.query_params.get('module', None)
        if module:
            queryset = queryset.filter(module=module)

        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification templates (admin only)
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """Filter templates by event type"""
        queryset = super().get_queryset()

        event_type_id = self.request.query_params.get('event_type', None)
        if event_type_id:
            queryset = queryset.filter(event_type_id=event_type_id)

        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.select_related('event_type')


class UserNotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notification preferences
    """
    serializer_class = UserNotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only see their own preferences"""
        user = self.request.user

        if user.is_staff:
            return UserNotificationPreference.objects.all()

        return UserNotificationPreference.objects.filter(user=user)

    def perform_create(self, serializer):
        """Set user to current user"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_preferences(self, request):
        """Get current user's preferences"""
        try:
            preferences = request.user.notification_preferences
        except UserNotificationPreference.DoesNotExist:
            # Create default preferences
            preferences = UserNotificationPreference.objects.create(user=request.user)

        serializer = self.get_serializer(preferences)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
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

        if user.is_staff:
            queryset = UserNotificationSubscription.objects.all()
        else:
            queryset = UserNotificationSubscription.objects.filter(user=user)

        # Filter by event type
        event_type_id = self.request.query_params.get('event_type', None)
        if event_type_id:
            queryset = queryset.filter(event_type_id=event_type_id)

        return queryset.select_related('user', 'event_type')

    def perform_create(self, serializer):
        """Set user to current user"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_subscriptions(self, request):
        """Get current user's subscriptions"""
        subscriptions = request.user.notification_subscriptions.filter(is_active=True)
        serializer = self.get_serializer(subscriptions, many=True)
        return Response(serializer.data)


class UserNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notifications
    """
    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only see their own notifications"""
        user = self.request.user

        if user.is_staff:
            queryset = UserNotification.objects.all()
        else:
            queryset = UserNotification.objects.filter(user=user)

        # Filter by read status
        is_read = self.request.query_params.get('is_read', None)
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        # Filter by priority
        priority = self.request.query_params.get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)

        # Filter by event type
        event_type_id = self.request.query_params.get('event_type', None)
        if event_type_id:
            queryset = queryset.filter(event_type_id=event_type_id)

        # Filter by date range
        from_date = self.request.query_params.get('from_date', None)
        to_date = self.request.query_params.get('to_date', None)
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)

        return queryset.select_related('user', 'event_type', 'content_type')

    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action == 'create':
            return UserNotificationCreateSerializer
        return UserNotificationSerializer

    def create(self, request, *args, **kwargs):
        """Create notifications for multiple users (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin can create notifications'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create notifications using service
        notifications = NotificationService.notify_users(
            user_ids=serializer.validated_data['recipient_ids'],
            title=serializer.validated_data['title'],
            message=serializer.validated_data['message'],
            priority=serializer.validated_data.get('priority', 'normal'),
            action_url=serializer.validated_data.get('action_url'),
            action_text=serializer.validated_data.get('action_text', 'View'),
            send_email=serializer.validated_data.get('send_email', False),
            additional_data=serializer.validated_data.get('additional_data')
        )

        response_serializer = UserNotificationSerializer(notifications, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()

        if notification.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You can only mark your own notifications as read'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification.mark_as_read()

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_unread(self, request, pk=None):
        """Mark a notification as unread"""
        notification = self.get_object()

        if notification.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You can only mark your own notifications as unread'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification.is_read = False
        notification.read_at = None
        notification.save(update_fields=['is_read', 'read_at'])

        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read for current user"""
        count = NotificationService.mark_all_as_read(request.user)
        return Response({'count': count, 'message': f'{count} notifications marked as read'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return Response({'unread_count': count})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics for current user"""
        user = request.user
        notifications = UserNotification.objects.filter(user=user)

        # Calculate statistics
        total_notifications = notifications.count()
        unread_count = notifications.filter(is_read=False).count()
        urgent_count = notifications.filter(priority='urgent', is_read=False).count()

        # Today's notifications
        today = timezone.now().date()
        today_count = notifications.filter(created_at__date=today).count()

        # By priority
        by_priority = dict(notifications.values('priority').annotate(count=Count('id')).values_list('priority', 'count'))

        # By module (via event type)
        by_module = dict(
            notifications.exclude(event_type__isnull=True)
            .values('event_type__module')
            .annotate(count=Count('id'))
            .values_list('event_type__module', 'count')
        )

        stats = {
            'total_notifications': total_notifications,
            'unread_count': unread_count,
            'urgent_count': urgent_count,
            'today_count': today_count,
            'by_priority': by_priority,
            'by_module': by_module
        }

        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['delete'])
    def clear_read(self, request):
        """Delete all read notifications for current user"""
        count, _ = UserNotification.objects.filter(
            user=request.user,
            is_read=True
        ).delete()

        return Response({
            'count': count,
            'message': f'{count} read notifications deleted'
        })


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

        if user.is_staff:
            queryset = NotificationBatch.objects.all()
        else:
            queryset = NotificationBatch.objects.filter(user=user)

        # Filter by frequency
        frequency = self.request.query_params.get('frequency', None)
        if frequency:
            queryset = queryset.filter(frequency=frequency)

        # Filter by sent status
        is_sent = self.request.query_params.get('is_sent', None)
        if is_sent is not None:
            queryset = queryset.filter(is_sent=is_sent.lower() == 'true')

        return queryset.select_related('user')
