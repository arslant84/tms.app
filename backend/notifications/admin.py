from django.contrib import admin
from .models import (
    NotificationEventType, NotificationTemplate, UserNotificationPreference,
    UserNotificationSubscription, UserNotification, NotificationBatch
)


@admin.register(NotificationEventType)
class NotificationEventTypeAdmin(admin.ModelAdmin):
    """Admin configuration for NotificationEventType model"""
    list_display = ['id', 'name', 'display_name', 'category', 'module', 'is_active']
    list_filter = ['category', 'module', 'is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['module', 'name']


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for NotificationTemplate model"""
    list_display = ['id', 'name', 'event_type', 'priority', 'is_active']
    list_filter = ['priority', 'is_active', 'event_type__module']
    search_fields = ['name', 'in_app_title', 'email_subject']
    ordering = ['event_type', 'name']


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
