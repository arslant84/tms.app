from rest_framework import serializers
from .models import (
    NotificationEventType, NotificationTemplate, UserNotificationPreference,
    UserNotificationSubscription, UserNotification, NotificationBatch
)
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested representation"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class NotificationEventTypeSerializer(serializers.ModelSerializer):
    """Serializer for notification event types"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = NotificationEventType
        fields = [
            'id', 'name', 'display_name', 'description', 'category',
            'module', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_display_name(self, obj):
        """Convert name like WORKFLOW_STARTED to 'Workflow Started'"""
        return ' '.join(word.capitalize() for word in obj.name.split('_'))


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification templates with full details"""
    event_type_detail = NotificationEventTypeSerializer(source='event_type', read_only=True)
    event_type_name = serializers.CharField(source='event_type.name', read_only=True)
    event_type_module = serializers.CharField(source='event_type.module', read_only=True)

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'description', 'subject', 'body',
            'event_type', 'event_type_detail', 'event_type_name', 'event_type_module',
            'notification_type', 'recipient_type', 'variables_available',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Ensure template name is unique"""
        instance = self.instance
        if instance:
            # Editing existing template - exclude self from uniqueness check
            if NotificationTemplate.objects.exclude(pk=instance.pk).filter(name=value).exists():
                raise serializers.ValidationError("A template with this name already exists.")
        else:
            # Creating new template
            if NotificationTemplate.objects.filter(name=value).exists():
                raise serializers.ValidationError("A template with this name already exists.")
        return value


class NotificationTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing templates (without body)"""
    event_type_name = serializers.CharField(source='event_type.name', read_only=True)
    event_type_module = serializers.CharField(source='event_type.module', read_only=True)

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'subject', 'event_type', 'event_type_name',
            'event_type_module', 'notification_type', 'recipient_type',
            'is_active', 'created_at', 'updated_at'
        ]


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user notification preferences"""
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = UserNotificationPreference
        fields = [
            'id', 'user', 'user_detail', 'email_notifications_enabled',
            'in_app_notifications_enabled', 'push_notifications_enabled',
            'digest_frequency', 'quiet_hours_enabled', 'quiet_hours_start',
            'quiet_hours_end', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate quiet hours configuration"""
        if data.get('quiet_hours_enabled'):
            if not data.get('quiet_hours_start') or not data.get('quiet_hours_end'):
                raise serializers.ValidationError(
                    "Quiet hours start and end times are required when quiet hours are enabled"
                )
        return data


class UserNotificationSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user notification subscriptions"""
    user_detail = UserSerializer(source='user', read_only=True)
    event_type_detail = NotificationEventTypeSerializer(source='event_type', read_only=True)

    class Meta:
        model = UserNotificationSubscription
        fields = [
            'id', 'user', 'user_detail', 'event_type', 'event_type_detail',
            'receive_email', 'receive_in_app', 'receive_push', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class UserNotificationSerializer(serializers.ModelSerializer):
    """Basic serializer for user notifications"""
    event_type_detail = NotificationEventTypeSerializer(source='event_type', read_only=True)
    entity_info = serializers.SerializerMethodField()

    class Meta:
        model = UserNotification
        fields = [
            'id', 'user', 'event_type', 'event_type_detail', 'title', 'message',
            'content_type', 'object_id', 'entity_info', 'action_url', 'action_text',
            'priority', 'is_read', 'read_at', 'sent_via_email', 'email_sent_at',
            'sent_via_push', 'push_sent_at', 'additional_data', 'expires_at',
            'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'read_at', 'sent_via_email', 'email_sent_at',
            'sent_via_push', 'push_sent_at', 'created_at'
        ]

    def get_entity_info(self, obj):
        """Get basic info about the related entity"""
        if obj.content_object:
            return {
                'type': obj.content_type.model,
                'id': obj.object_id,
                'str': str(obj.content_object)
            }
        return None


class UserNotificationCreateSerializer(serializers.Serializer):
    """Serializer for creating notifications"""
    recipient_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of user IDs to send notification to"
    )
    event_type_id = serializers.IntegerField(required=False)
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    action_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    action_text = serializers.CharField(max_length=100, required=False, default='View')
    priority = serializers.ChoiceField(
        choices=['low', 'normal', 'high', 'urgent'],
        default='normal'
    )
    send_email = serializers.BooleanField(default=False)
    entity_type = serializers.CharField(required=False, allow_blank=True)
    entity_id = serializers.IntegerField(required=False, allow_null=True)
    additional_data = serializers.JSONField(required=False)

    def validate_recipient_ids(self, value):
        """Validate recipient users exist"""
        if not value:
            raise serializers.ValidationError("At least one recipient is required")

        existing_ids = User.objects.filter(id__in=value).values_list('id', flat=True)
        invalid_ids = set(value) - set(existing_ids)

        if invalid_ids:
            raise serializers.ValidationError(
                f"Invalid user IDs: {', '.join(map(str, invalid_ids))}"
            )

        return value

    def validate_event_type_id(self, value):
        """Validate event type exists"""
        if value:
            if not NotificationEventType.objects.filter(id=value, is_active=True).exists():
                raise serializers.ValidationError(
                    "Event type does not exist or is not active"
                )
        return value


class NotificationBatchSerializer(serializers.ModelSerializer):
    """Serializer for notification batches"""
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = NotificationBatch
        fields = [
            'id', 'user', 'user_detail', 'frequency', 'notification_count',
            'period_start', 'period_end', 'is_sent', 'sent_at',
            'sent_via_email', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    total_notifications = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    urgent_count = serializers.IntegerField()
    today_count = serializers.IntegerField()
    by_priority = serializers.DictField()
    by_module = serializers.DictField()
