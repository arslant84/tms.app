from accounts.models import Role, User
from django.contrib.contenttypes.models import ContentType
from notifications.models import NotificationTemplate
from rest_framework import serializers

from .models import (
    WorkflowAuditLog,
    WorkflowCondition,
    WorkflowDelegation,
    WorkflowInstance,
    WorkflowStep,
    WorkflowStepExecution,
    WorkflowStepNotificationConfig,
    WorkflowTemplate,
)


class RoleSimpleSerializer(serializers.ModelSerializer):
    """Minimal role representation for notification-config dropdown options"""

    class Meta:
        model = Role
        fields = ["id", "name"]


class UserSimpleSerializer(serializers.ModelSerializer):
    """Minimal user representation for notification-config dropdown options"""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "department"]

    def get_full_name(self, obj):
        return obj.get_full_name()


class NotificationTemplateSimpleSerializer(serializers.ModelSerializer):
    """Minimal notification template representation for notification-config dropdown options"""

    class Meta:
        model = NotificationTemplate
        fields = ["id", "name", "subject"]


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested representation"""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "department"]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class WorkflowConditionSerializer(serializers.ModelSerializer):
    """Serializer for workflow conditions"""

    class Meta:
        model = WorkflowCondition
        fields = [
            "id",
            "workflow_step",
            "condition_type",
            "field_name",
            "field_value",
            "logical_operator",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class WorkflowStepNotificationConfigSerializer(serializers.ModelSerializer):
    """Serializer for workflow step notification configurations"""

    notification_template_name = serializers.SerializerMethodField()
    event_type_display = serializers.CharField(
        source="get_event_type_display", read_only=True
    )
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )

    class Meta:
        model = WorkflowStepNotificationConfig
        fields = [
            "id",
            "workflow_step",
            "event_type",
            "event_type_display",
            "notification_template",
            "notification_template_name",
            "recipient_types",
            "custom_recipients",
            "is_active",
            "send_email",
            "send_system_notification",
            "priority",
            "priority_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_notification_template_name(self, obj):
        """Safely get notification template name, handling null case"""
        if obj.notification_template:
            return obj.notification_template.name
        return None

    def validate_recipient_types(self, value):
        """Validate recipient types"""
        if not isinstance(value, list):
            raise serializers.ValidationError("recipient_types must be a list")

        # Get predefined valid types
        valid_types = [
            choice[0]
            for choice in WorkflowStepNotificationConfig.RECIPIENT_TYPE_CHOICES
        ]

        for recipient_type in value:
            # Allow predefined types or dynamic role-based types (role_*)
            if recipient_type not in valid_types and not recipient_type.startswith(
                "role_"
            ):
                raise serializers.ValidationError(
                    f"Invalid recipient type: {recipient_type}. "
                    f"Must be one of: {', '.join(valid_types)} or a role ID (role_*)"
                )

        return value

    def validate_custom_recipients(self, value):
        """Validate custom email addresses"""
        if not isinstance(value, list):
            raise serializers.ValidationError("custom_recipients must be a list")

        # Basic email validation for custom recipients
        import re

        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        for email in value:
            if not email_pattern.match(email):
                raise serializers.ValidationError(f"Invalid email address: {email}")

        return value

    def validate(self, data):
        """Cross-field validation"""
        # If custom_emails is in recipient_types, custom_recipients must be provided
        recipient_types = data.get("recipient_types", [])
        custom_recipients = data.get("custom_recipients", [])

        if "custom_emails" in recipient_types and not custom_recipients:
            raise serializers.ValidationError(
                "custom_recipients is required when 'custom_emails' is selected in recipient_types"
            )

        return data


class WorkflowStepSerializer(serializers.ModelSerializer):
    """Serializer for workflow steps"""

    approver_user_detail = UserSerializer(source="approver_user", read_only=True)
    conditions = WorkflowConditionSerializer(many=True, read_only=True)
    notification_configs = WorkflowStepNotificationConfigSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = WorkflowStep
        fields = [
            "id",
            "workflow_template",
            "step_order",
            "step_name",
            "step_description",
            "approver_role",
            "approver_permission",
            "approver_user",
            "approver_user_detail",
            "is_required",
            "can_skip",
            "requires_comments",
            "conditions",
            "notification_configs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        """Validate step data"""
        # Ensure step_order is positive
        if data.get("step_order", 1) < 1:
            raise serializers.ValidationError("Step order must be positive")

        return data


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """Basic serializer for workflow templates"""

    created_by_user = UserSerializer(source="created_by", read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id",
            "name",
            "description",
            "entity_type",
            "is_active",
            "allow_parallel_steps",
            "auto_approve_on_condition",
            "step_count",
            "created_by",
            "created_by_user",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_step_count(self, obj):
        return obj.steps.count()

    def validate_entity_type(self, value):
        """Validate entity type is in lowercase"""
        return value.lower()


class WorkflowTemplateDetailSerializer(WorkflowTemplateSerializer):
    """Detailed serializer with nested steps"""

    steps = WorkflowStepSerializer(many=True, read_only=True)

    class Meta(WorkflowTemplateSerializer.Meta):
        fields = WorkflowTemplateSerializer.Meta.fields + ["steps"]


class WorkflowTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating workflow templates with steps"""

    steps = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        write_only=True,  # Only used for input, not output
    )

    class Meta:
        model = WorkflowTemplate
        fields = [
            "name",
            "description",
            "entity_type",
            "is_active",
            "allow_parallel_steps",
            "auto_approve_on_condition",
            "steps",
        ]

    def to_representation(self, instance):
        """Use WorkflowTemplateDetailSerializer for output"""
        return WorkflowTemplateDetailSerializer(instance, context=self.context).data

    # Default notification configs to create for new workflow steps
    DEFAULT_NOTIFICATION_CONFIGS = [
        {
            "event_type": "assignment",
            "template_name": "approval_required",
            "recipient_types": ["current_approver"],
            "priority": "high",
        },
        {
            "event_type": "approval",
            "template_name": "workflow_completed",
            "recipient_types": ["requester"],
            "priority": "normal",
        },
        {
            "event_type": "rejection",
            "template_name": "workflow_rejected",
            "recipient_types": ["requester"],
            "priority": "urgent",
        },
        {
            "event_type": "delegation",
            "template_name": "delegation_confirmed",
            "recipient_types": ["current_approver"],
            "priority": "high",
        },
        {
            "event_type": "workflow_completed",
            "template_name": "workflow_completed",
            "recipient_types": ["requester"],
            "priority": "high",
        },
        {
            "event_type": "workflow_cancelled",
            "template_name": "workflow_cancelled",
            "recipient_types": ["requester"],
            "priority": "normal",
        },
    ]

    def _create_default_notification_configs(self, step):
        """Create default notification configs for a workflow step"""
        from notifications.models import NotificationTemplate

        for config in self.DEFAULT_NOTIFICATION_CONFIGS:
            try:
                template = NotificationTemplate.objects.get(
                    name=config["template_name"]
                )
                WorkflowStepNotificationConfig.objects.create(
                    workflow_step=step,
                    event_type=config["event_type"],
                    notification_template=template,
                    recipient_types=config["recipient_types"],
                    custom_recipients=[],
                    is_active=True,
                    send_email=True,
                    send_system_notification=True,
                    priority=config["priority"],
                )
            except NotificationTemplate.DoesNotExist:
                pass  # Skip if template doesn't exist

    def create(self, validated_data):
        """Create workflow template with steps"""
        steps_data = validated_data.pop("steps", [])

        # Get created_by from validated_data (passed via perform_create) or context
        if "created_by" not in validated_data:
            request = self.context.get("request")
            if request and hasattr(request, "user"):
                validated_data["created_by"] = request.user

        workflow_template = WorkflowTemplate.objects.create(**validated_data)

        # Create steps
        for step_data in steps_data:
            notification_configs_data = step_data.pop("notification_configs", [])

            step = WorkflowStep.objects.create(
                workflow_template=workflow_template,
                step_order=step_data.get("step_order"),
                step_name=step_data.get("step_name"),
                step_description=step_data.get("step_description", ""),
                approver_role=step_data.get("approver_role"),
                approver_permission=step_data.get("approver_permission"),
                approver_user_id=(
                    step_data.get("approver_user")
                    if step_data.get("approver_user")
                    else None
                ),
                is_required=step_data.get("is_required", True),
                can_skip=step_data.get("can_skip", False),
                requires_comments=step_data.get("requires_comments", False),
            )

            # Create notification configs for this step (CREATE always gets defaults if none provided)
            if notification_configs_data:
                # Use provided configs
                for config_data in notification_configs_data:
                    WorkflowStepNotificationConfig.objects.create(
                        workflow_step=step,
                        event_type=config_data.get("event_type"),
                        notification_template_id=config_data.get(
                            "notification_template"
                        ),
                        recipient_types=config_data.get("recipient_types", []),
                        custom_recipients=config_data.get("custom_recipients", []),
                        is_active=config_data.get("is_active", True),
                        send_email=config_data.get("send_email", True),
                        send_system_notification=config_data.get(
                            "send_system_notification", True
                        ),
                        priority=config_data.get("priority", "normal"),
                    )
            else:
                # Create default notification configs for new workflows
                self._create_default_notification_configs(step)

        return workflow_template

    def update(self, instance, validated_data):
        """Update workflow template and steps"""
        import logging

        logger = logging.getLogger(__name__)

        steps_data = validated_data.pop("steps", None)

        try:
            # Update template fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Update steps if provided
            if steps_data is not None:
                # Match incoming steps to existing ones by step_order and update
                # them in place. WorkflowStepExecution.workflow_step cascades on
                # delete, so wholesale delete-and-recreate here would wipe out the
                # approval history of every past instance run against this
                # template. Steps no longer present are only removed if they
                # have no execution history to preserve.
                existing_steps_by_order = {
                    step.step_order: step for step in instance.steps.all()
                }
                incoming_orders = set()

                for step_data in steps_data:
                    notification_configs_data = step_data.pop(
                        "notification_configs", []
                    )
                    step_order = step_data.get("step_order")
                    incoming_orders.add(step_order)
                    approver_user_id = step_data.get("approver_user") or None

                    step = existing_steps_by_order.get(step_order)
                    if step:
                        step.step_name = step_data.get("step_name")
                        step.step_description = step_data.get("step_description", "")
                        step.approver_role = step_data.get("approver_role")
                        step.approver_permission = step_data.get("approver_permission")
                        step.approver_user_id = approver_user_id
                        step.is_required = step_data.get("is_required", True)
                        step.can_skip = step_data.get("can_skip", False)
                        step.requires_comments = step_data.get(
                            "requires_comments", False
                        )
                        step.save()
                        step.notification_configs.all().delete()
                    else:
                        step = WorkflowStep.objects.create(
                            workflow_template=instance,
                            step_order=step_order,
                            step_name=step_data.get("step_name"),
                            step_description=step_data.get("step_description", ""),
                            approver_role=step_data.get("approver_role"),
                            approver_permission=step_data.get("approver_permission"),
                            approver_user_id=approver_user_id,
                            is_required=step_data.get("is_required", True),
                            can_skip=step_data.get("can_skip", False),
                            requires_comments=step_data.get("requires_comments", False),
                        )

                    # On UPDATE: Use exactly what frontend sends (respect user's changes)
                    # If user deleted all configs, they get none. If user added/modified, those are used.
                    for config_data in notification_configs_data:
                        WorkflowStepNotificationConfig.objects.create(
                            workflow_step=step,
                            event_type=config_data.get("event_type"),
                            notification_template_id=config_data.get(
                                "notification_template"
                            ),
                            recipient_types=config_data.get("recipient_types", []),
                            custom_recipients=config_data.get("custom_recipients", []),
                            is_active=config_data.get("is_active", True),
                            send_email=config_data.get("send_email", True),
                            send_system_notification=config_data.get(
                                "send_system_notification", True
                            ),
                            priority=config_data.get("priority", "normal"),
                        )

                # Remove steps that are no longer part of the template, as long
                # as they have no execution history to lose.
                for step_order, step in existing_steps_by_order.items():
                    if (
                        step_order not in incoming_orders
                        and not step.executions.exists()
                    ):
                        step.delete()

            return instance
        except Exception as e:
            logger.error(
                f"Error updating workflow template {instance.id}: {str(e)}",
                exc_info=True,
            )
            raise


class WorkflowStepExecutionSerializer(serializers.ModelSerializer):
    """Serializer for workflow step executions"""

    workflow_step_detail = WorkflowStepSerializer(
        source="workflow_step", read_only=True
    )
    assigned_to_user = UserSerializer(source="assigned_to", read_only=True)
    actioned_by_user = UserSerializer(source="actioned_by", read_only=True)

    class Meta:
        model = WorkflowStepExecution
        fields = [
            "id",
            "workflow_instance",
            "workflow_step",
            "workflow_step_detail",
            "status",
            "assigned_to",
            "assigned_to_user",
            "actioned_by",
            "actioned_by_user",
            "comments",
            "action_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "actioned_by",
            "action_date",
            "created_at",
            "updated_at",
        ]


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    """Basic serializer for workflow instances"""

    workflow_template_detail = WorkflowTemplateSerializer(
        source="workflow_template", read_only=True
    )
    initiated_by_user = UserSerializer(source="initiated_by", read_only=True)
    entity_info = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = [
            "id",
            "workflow_template",
            "workflow_template_detail",
            "content_type",
            "object_id",
            "entity_info",
            "status",
            "current_step_order",
            "started_at",
            "completed_at",
            "initiated_by",
            "initiated_by_user",
            "additional_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "initiated_by",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_entity_info(self, obj):
        """Get basic info about the related entity"""
        if obj.content_object:
            return {
                "type": obj.content_type.model,
                "id": obj.object_id,
                "str": str(obj.content_object),
            }
        return None


class WorkflowInstanceDetailSerializer(WorkflowInstanceSerializer):
    """
    Detailed serializer with step executions. workflow_template_detail is
    upgraded to the richer WorkflowTemplateDetailSerializer (adds the
    template's full ordered `steps` list) so the frontend can render a
    complete stepper - including steps not yet reached, which have no
    step_execution row yet since WorkflowEngine creates those lazily.
    """

    step_executions = WorkflowStepExecutionSerializer(many=True, read_only=True)
    workflow_template_detail = WorkflowTemplateDetailSerializer(
        source="workflow_template", read_only=True
    )

    class Meta(WorkflowInstanceSerializer.Meta):
        fields = WorkflowInstanceSerializer.Meta.fields + ["step_executions"]


class WorkflowInstanceCreateSerializer(serializers.Serializer):
    """Serializer for creating workflow instances"""

    workflow_template_id = serializers.IntegerField()
    entity_type = serializers.CharField(
        help_text="Model name of the entity (e.g., 'travelrequest', 'visaapplication')"
    )
    entity_id = serializers.IntegerField()
    additional_data = serializers.JSONField(required=False)

    def validate(self, data):
        """Validate workflow instance data"""
        # Validate workflow template exists and is active
        try:
            workflow_template = WorkflowTemplate.objects.get(
                id=data["workflow_template_id"], is_active=True
            )
        except WorkflowTemplate.DoesNotExist:
            raise serializers.ValidationError(
                "Workflow template does not exist or is not active"
            )

        # Validate entity type matches template
        if workflow_template.entity_type.lower() != data["entity_type"].lower():
            raise serializers.ValidationError(
                f"Entity type '{data['entity_type']}' does not match "
                f"workflow template entity type '{workflow_template.entity_type}'"
            )

        # Validate content type exists
        try:
            content_type = ContentType.objects.get(model=data["entity_type"].lower())
        except ContentType.DoesNotExist:
            raise serializers.ValidationError(
                f"Content type for '{data['entity_type']}' does not exist"
            )

        data["workflow_template"] = workflow_template
        data["content_type"] = content_type

        return data

    def create(self, validated_data):
        """Create workflow instance and initial step executions"""
        workflow_template = validated_data["workflow_template"]
        content_type = validated_data["content_type"]
        entity_id = validated_data["entity_id"]
        additional_data = validated_data.get("additional_data")
        initiated_by = self.context["request"].user

        # Create workflow instance
        workflow_instance = WorkflowInstance.objects.create(
            workflow_template=workflow_template,
            content_type=content_type,
            object_id=entity_id,
            status="pending",
            initiated_by=initiated_by,
            additional_data=additional_data,
        )

        # Create step executions for all steps
        for step in workflow_template.steps.all().order_by("step_order"):
            # Determine who to assign the step to
            assigned_to = step.approver_user if step.approver_user else None

            # First step is 'pending', subsequent steps are 'waiting'
            WorkflowStepExecution.objects.create(
                workflow_instance=workflow_instance,
                workflow_step=step,
                assigned_to=assigned_to,
                status="pending" if step.step_order == 1 else "waiting",
            )

        # Create audit log
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type="created",
            action_description=f"Workflow instance created for {content_type.model} #{entity_id}",
            performed_by=initiated_by,
        )

        return workflow_instance


class WorkflowDelegationSerializer(serializers.ModelSerializer):
    """Serializer for workflow delegations"""

    delegated_from_user = UserSerializer(source="delegated_from", read_only=True)
    delegated_to_user = UserSerializer(source="delegated_to", read_only=True)

    class Meta:
        model = WorkflowDelegation
        fields = [
            "id",
            "workflow_step_execution",
            "delegated_from",
            "delegated_from_user",
            "delegated_to",
            "delegated_to_user",
            "reason",
            "is_active",
            "delegated_at",
            "expires_at",
        ]
        read_only_fields = ["id", "delegated_from", "delegated_at"]

    def validate(self, data):
        """Validate delegation data"""
        # Ensure user is not delegating to themselves
        delegated_from = self.context["request"].user
        delegated_to = data.get("delegated_to")

        if delegated_from == delegated_to:
            raise serializers.ValidationError("Cannot delegate to yourself")

        # Validate expiry date is in future
        if data.get("expires_at"):
            from django.utils import timezone

            if data["expires_at"] <= timezone.now():
                raise serializers.ValidationError("Expiry date must be in the future")

        return data


class WorkflowAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for workflow audit logs"""

    performed_by_user = UserSerializer(source="performed_by", read_only=True)

    class Meta:
        model = WorkflowAuditLog
        fields = [
            "id",
            "workflow_instance",
            "action_type",
            "action_description",
            "performed_by",
            "performed_by_user",
            "workflow_state_snapshot",
            "ip_address",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields


class WorkflowActionSerializer(serializers.Serializer):
    """Serializer for workflow step actions (approve/reject)"""

    action = serializers.ChoiceField(choices=["approve", "reject", "skip", "delegate"])
    comments = serializers.CharField(required=False, allow_blank=True)
    delegated_to_id = serializers.IntegerField(required=False)

    def validate(self, data):
        """Validate action data"""
        action = data.get("action")

        # Reject requires comments
        if action == "reject" and not data.get("comments"):
            raise serializers.ValidationError(
                "Comments are required when rejecting a step"
            )

        # Delegate requires delegated_to_id
        if action == "delegate" and not data.get("delegated_to_id"):
            raise serializers.ValidationError(
                "delegated_to_id is required when delegating"
            )

        return data
