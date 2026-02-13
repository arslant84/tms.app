from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import (
    NotificationEventType, NotificationTemplate, UserNotificationPreference,
    UserNotificationSubscription, UserNotification, NotificationBatch
)


@admin.register(NotificationEventType)
class NotificationEventTypeAdmin(admin.ModelAdmin):
    """Admin configuration for NotificationEventType model"""
    list_display = ['id', 'name', 'description', 'category', 'module', 'is_active']
    list_filter = ['category', 'module', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['module', 'name']


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for NotificationTemplate model"""
    list_display = ['id', 'name', 'event_type', 'notification_type', 'recipient_type', 'is_active']
    list_filter = ['notification_type', 'recipient_type', 'is_active', 'event_type__module']
    search_fields = ['name', 'subject', 'description']
    ordering = ['name']


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin configuration for UserNotificationPreference model"""
    list_display = [
        'id', 'user', 'email_notifications_enabled', 'in_app_notifications_enabled',
        'digest_frequency', 'quiet_hours_enabled'
    ]
    list_filter = ['digest_frequency', 'quiet_hours_enabled']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['user']


@admin.register(UserNotificationSubscription)
class UserNotificationSubscriptionAdmin(admin.ModelAdmin):
    """Admin configuration for UserNotificationSubscription model"""
    list_display = [
        'id', 'user', 'event_type', 'receive_email', 'receive_in_app', 'is_active'
    ]
    list_filter = ['is_active', 'receive_email', 'receive_in_app', 'event_type__module']
    search_fields = ['user__email', 'event_type__name']
    ordering = ['user', 'event_type']


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    """Admin configuration for UserNotification model"""
    list_display = [
        'id', 'user', 'title', 'priority', 'is_read', 'sent_via_email', 'created_at'
    ]
    list_filter = ['priority', 'is_read', 'sent_via_email', 'event_type__module', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    readonly_fields = ['created_at', 'read_at', 'email_sent_at']
    ordering = ['-created_at']
    actions = ['mark_as_read', 'mark_as_unread', 'delete_selected_notifications', 'create_test_notifications']

    fieldsets = (
        ('User', {
            'fields': ('user', 'event_type')
        }),
        ('Content', {
            'fields': ('title', 'message', 'priority')
        }),
        ('Action', {
            'fields': ('action_url', 'action_text')
        }),
        ('Related Entity', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Delivery', {
            'fields': ('sent_via_email', 'email_sent_at', 'email_error'),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': ('additional_data', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    @admin.action(description='Mark selected notifications as read')
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read"""
        count = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'{count} notification(s) marked as read.', messages.SUCCESS)

    @admin.action(description='Mark selected notifications as unread')
    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread"""
        count = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{count} notification(s) marked as unread.', messages.SUCCESS)

    @admin.action(description='Delete selected notifications')
    def delete_selected_notifications(self, request, queryset):
        """Delete selected notifications"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} notification(s) deleted.', messages.SUCCESS)

    @admin.action(description='Create 5 test notifications for selected users')
    def create_test_notifications(self, request, queryset):
        """Create test notifications for selected users"""
        from accounts.models import User
        from trf.models import TravelRequest
        from visa.models import VisaApplication
        from transport.models import TransportRequest
        from expenses.models import ExpenseClaim

        # Get unique users from selected notifications
        user_ids = queryset.values_list('user_id', flat=True).distinct()
        users = User.objects.filter(id__in=user_ids)

        if not users.exists():
            self.message_user(request, 'No users found in selected notifications.', messages.WARNING)
            return

        # Get or create event type
        event_type, _ = NotificationEventType.objects.get_or_create(
            name='SYSTEM_TEST',
            defaults={
                'description': 'System test notification',
                'category': 'system',
                'module': 'general',
                'is_active': True
            }
        )

        # Get real IDs to avoid 404 errors
        trf_id = TravelRequest.objects.values_list('id', flat=True).first() or 'demo'
        visa_id = VisaApplication.objects.values_list('id', flat=True).first() or 'demo'
        transport_id = TransportRequest.objects.values_list('id', flat=True).first() or 'demo'
        expense_id = ExpenseClaim.objects.values_list('id', flat=True).first() or 'demo'

        # Notification templates with real URLs
        templates = [
            {'title': '📝 Test: Travel Request', 'message': 'This is a test travel request notification.', 'priority': 'normal', 'url': f'/trf/{trf_id}'},
            {'title': '⏰ Test: Approval Required', 'message': 'This is a test approval notification.', 'priority': 'high', 'url': '/approvals'},
            {'title': '✅ Test: Request Approved', 'message': 'This is a test approval confirmation.', 'priority': 'normal', 'url': f'/expenses/{expense_id}'},
            {'title': '🚨 Test: Urgent Alert', 'message': 'This is a test urgent notification.', 'priority': 'urgent', 'url': f'/transport/{transport_id}'},
            {'title': '💬 Test: Comment Added', 'message': 'This is a test comment notification.', 'priority': 'low', 'url': f'/visa/{visa_id}'},
        ]

        total_created = 0
        for user in users:
            for i, template in enumerate(templates):
                UserNotification.objects.create(
                    user=user,
                    event_type=event_type,
                    title=template['title'],
                    message=template['message'],
                    priority=template['priority'],
                    action_url=template['url'],
                    action_text='View',
                    is_read=(i >= 2),
                    sent_via_email=False,
                    created_at=timezone.now() - timedelta(minutes=i * 10)
                )
                total_created += 1

        self.message_user(
            request,
            f'✅ Created {total_created} test notifications for {users.count()} user(s).',
            messages.SUCCESS
        )


@admin.register(NotificationBatch)
class NotificationBatchAdmin(admin.ModelAdmin):
    """Admin configuration for NotificationBatch model"""
    list_display = [
        'id', 'user', 'frequency', 'notification_count', 'is_sent', 'sent_at'
    ]
    list_filter = ['frequency', 'is_sent', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']
