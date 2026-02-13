from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
import uuid


class NotificationEventType(models.Model):
    """
    Defines types of events that can trigger notifications
    Matches syntra database: notification_event_types table
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier for the event type (e.g., 'trf_submitted')"
    )
    description = models.TextField(blank=True, null=True)

    # Event categorization
    category = models.CharField(
        max_length=50,
        help_text="Category: approval, status_update, reminder, system"
    )

    # Module association
    module = models.CharField(
        max_length=50,
        help_text="Module: trf, visa, accommodation, transport, claims, general"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module', 'category', 'name']
        db_table = 'notification_event_types'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['module']),
        ]

    def __str__(self):
        return f"{self.name} ({self.module})"


class NotificationTemplate(models.Model):
    """
    Templates for notification content with HTML email support
    Matches syntra database: notification_templates table
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique template name identifier"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Template description and purpose"
    )

    subject = models.TextField(
        help_text="Email subject line with variables like {userName}, {entityId}"
    )

    body = models.TextField(
        help_text="HTML email body template with variables"
    )

    event_type = models.ForeignKey(
        NotificationEventType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates',
        db_column='event_type_id'
    )

    notification_type = models.CharField(
        max_length=50,
        default='email',
        help_text="Type: email, system, or both"
    )

    recipient_type = models.CharField(
        max_length=50,
        default='approver',
        help_text="Recipient: approver, requestor, or both"
    )

    variables_available = ArrayField(
        models.TextField(),
        blank=True,
        null=True,
        help_text="Array of available template variables"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        db_table = 'notification_templates'
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['recipient_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name}"


class UserNotificationPreference(models.Model):
    """
    User preferences for receiving notifications
    Controls which notifications they receive and via which channels
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Global preferences
    email_notifications_enabled = models.BooleanField(
        default=True,
        help_text="Receive notifications via email"
    )
    in_app_notifications_enabled = models.BooleanField(
        default=True,
        help_text="Receive in-app notifications"
    )
    push_notifications_enabled = models.BooleanField(
        default=False,
        help_text="Receive push notifications (future feature)"
    )

    # Frequency settings
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('instant', 'Instant'),
            ('hourly', 'Hourly Digest'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
        ],
        default='instant'
    )

    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Start of quiet hours (no notifications)"
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="End of quiet hours"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.email}"


class UserNotificationSubscription(models.Model):
    """
    User subscriptions to specific event types
    Allows fine-grained control over which events trigger notifications
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_subscriptions'
    )
    event_type = models.ForeignKey(
        NotificationEventType,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )

    # Channel preferences for this event type
    receive_email = models.BooleanField(default=True)
    receive_in_app = models.BooleanField(default=True)
    receive_push = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'event_type']
        ordering = ['user', 'event_type']

    def __str__(self):
        return f"{self.user.email} → {self.event_type.name}"


class UserNotification(models.Model):
    """
    Individual notification instance sent to a user
    Tracks read/unread status and delivery
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    event_type = models.ForeignKey(
        NotificationEventType,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notifications'
    )

    # Notification content
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Related entity (generic relation)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Action
    action_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL for the notification action"
    )
    action_text = models.CharField(
        max_length=100,
        default='View',
        help_text="Text for the action button"
    )

    # Priority and status
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('normal', 'Normal'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        default='normal'
    )

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Delivery tracking
    sent_via_email = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True, null=True)

    sent_via_push = models.BooleanField(default=False)
    push_sent_at = models.DateTimeField(null=True, blank=True)

    # Additional data
    additional_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional context data for the notification"
    )

    # Expiry
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this notification expires and should be auto-archived"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.title} → {self.user.email}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationBatch(models.Model):
    """
    Batch notifications for digest delivery
    Groups notifications by user and digest frequency
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_batches'
    )

    frequency = models.CharField(
        max_length=20,
        choices=[
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ]
    )

    # Batch details
    notification_count = models.IntegerField(default=0)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()

    # Delivery status
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_via_email = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.frequency} batch for {self.user.email} ({self.notification_count} notifications)"
