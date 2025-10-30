from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import (
    WorkflowTemplate, WorkflowStep, WorkflowCondition, WorkflowInstance,
    WorkflowStepExecution, WorkflowDelegation, WorkflowAuditLog
)
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested representation"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'department']
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class WorkflowConditionSerializer(serializers.ModelSerializer):
    """Serializer for workflow conditions"""
    class Meta:
        model = WorkflowCondition
        fields = [
            'id', 'workflow_step', 'condition_type', 'field_name',
            'field_value', 'logical_operator', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WorkflowStepSerializer(serializers.ModelSerializer):
    """Serializer for workflow steps"""
    approver_user_detail = UserSerializer(source='approver_user', read_only=True)
    conditions = WorkflowConditionSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowStep
        fields = [
            'id', 'workflow_template', 'step_order', 'step_name', 'step_description',
            'approver_role', 'approver_user', 'approver_user_detail',
            'is_required', 'can_skip', 'requires_comments',
            'sla_hours', 'escalation_hours', 'conditions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate step data"""
        # Ensure step_order is positive
        if data.get('step_order', 1) < 1:
            raise serializers.ValidationError("Step order must be positive")

        # Validate SLA hours
        if data.get('sla_hours') and data['sla_hours'] < 1:
            raise serializers.ValidationError("SLA hours must be at least 1")

        # Validate escalation hours
        if data.get('escalation_hours'):
            if data['escalation_hours'] < 1:
                raise serializers.ValidationError("Escalation hours must be at least 1")
            if data.get('sla_hours') and data['escalation_hours'] >= data['sla_hours']:
                raise serializers.ValidationError(
                    "Escalation hours must be less than SLA hours"
                )

        return data


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """Basic serializer for workflow templates"""
    created_by_user = UserSerializer(source='created_by', read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'name', 'description', 'entity_type', 'is_active',
            'allow_parallel_steps', 'auto_approve_on_condition',
            'step_count', 'created_by', 'created_by_user',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_step_count(self, obj):
        return obj.steps.count()

    def validate_entity_type(self, value):
        """Validate entity type is in lowercase"""
        return value.lower()


class WorkflowTemplateDetailSerializer(WorkflowTemplateSerializer):
    """Detailed serializer with nested steps"""
    steps = WorkflowStepSerializer(many=True, read_only=True)

    class Meta(WorkflowTemplateSerializer.Meta):
        fields = WorkflowTemplateSerializer.Meta.fields + ['steps']


class WorkflowTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating workflow templates with steps"""
    steps = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        write_only=True  # Only used for input, not output
    )

    class Meta:
        model = WorkflowTemplate
        fields = [
            'name', 'description', 'entity_type', 'is_active',
            'allow_parallel_steps', 'auto_approve_on_condition', 'steps'
        ]

    def to_representation(self, instance):
        """Use WorkflowTemplateDetailSerializer for output"""
        return WorkflowTemplateDetailSerializer(instance, context=self.context).data

    def create(self, validated_data):
        """Create workflow template with steps"""
        steps_data = validated_data.pop('steps', [])

        # Get created_by from validated_data (passed via perform_create) or context
        if 'created_by' not in validated_data:
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                validated_data['created_by'] = request.user

        workflow_template = WorkflowTemplate.objects.create(**validated_data)

        # Create steps
        for step_data in steps_data:
            WorkflowStep.objects.create(
                workflow_template=workflow_template,
                step_order=step_data.get('step_order'),
                step_name=step_data.get('step_name'),
                step_description=step_data.get('step_description', ''),
                approver_role=step_data.get('approver_role'),
                approver_user_id=step_data.get('approver_user') if step_data.get('approver_user') else None,
                is_required=step_data.get('is_required', True),
                can_skip=step_data.get('can_skip', False),
                requires_comments=step_data.get('requires_comments', False),
                sla_hours=step_data.get('sla_hours'),
                escalation_hours=step_data.get('escalation_hours')
            )

        return workflow_template

    def update(self, instance, validated_data):
        """Update workflow template and steps"""
        steps_data = validated_data.pop('steps', None)

        # Update template fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update steps if provided
        if steps_data is not None:
            # Delete existing steps
            instance.steps.all().delete()

            # Create new steps
            for step_data in steps_data:
                WorkflowStep.objects.create(
                    workflow_template=instance,
                    step_order=step_data.get('step_order'),
                    step_name=step_data.get('step_name'),
                    step_description=step_data.get('step_description', ''),
                    approver_role=step_data.get('approver_role'),
                    approver_user_id=step_data.get('approver_user') if step_data.get('approver_user') else None,
                    is_required=step_data.get('is_required', True),
                    can_skip=step_data.get('can_skip', False),
                    requires_comments=step_data.get('requires_comments', False),
                    sla_hours=step_data.get('sla_hours'),
                    escalation_hours=step_data.get('escalation_hours')
                )

        return instance


class WorkflowStepExecutionSerializer(serializers.ModelSerializer):
    """Serializer for workflow step executions"""
    workflow_step_detail = WorkflowStepSerializer(source='workflow_step', read_only=True)
    assigned_to_user = UserSerializer(source='assigned_to', read_only=True)
    actioned_by_user = UserSerializer(source='actioned_by', read_only=True)

    class Meta:
        model = WorkflowStepExecution
        fields = [
            'id', 'workflow_instance', 'workflow_step', 'workflow_step_detail',
            'status', 'assigned_to', 'assigned_to_user', 'actioned_by',
            'actioned_by_user', 'comments', 'action_date',
            'sla_due_date', 'escalation_date', 'is_overdue', 'is_escalated',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'actioned_by', 'action_date', 'is_overdue', 'is_escalated',
            'created_at', 'updated_at'
        ]


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    """Basic serializer for workflow instances"""
    workflow_template_detail = WorkflowTemplateSerializer(
        source='workflow_template', read_only=True
    )
    initiated_by_user = UserSerializer(source='initiated_by', read_only=True)
    entity_info = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = [
            'id', 'workflow_template', 'workflow_template_detail',
            'content_type', 'object_id', 'entity_info', 'status',
            'current_step_order', 'started_at', 'completed_at',
            'initiated_by', 'initiated_by_user', 'additional_data',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'initiated_by', 'started_at', 'completed_at',
            'created_at', 'updated_at'
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


class WorkflowInstanceDetailSerializer(WorkflowInstanceSerializer):
    """Detailed serializer with step executions"""
    step_executions = WorkflowStepExecutionSerializer(many=True, read_only=True)

    class Meta(WorkflowInstanceSerializer.Meta):
        fields = WorkflowInstanceSerializer.Meta.fields + ['step_executions']


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
                id=data['workflow_template_id'],
                is_active=True
            )
        except WorkflowTemplate.DoesNotExist:
            raise serializers.ValidationError(
                "Workflow template does not exist or is not active"
            )

        # Validate entity type matches template
        if workflow_template.entity_type.lower() != data['entity_type'].lower():
            raise serializers.ValidationError(
                f"Entity type '{data['entity_type']}' does not match "
                f"workflow template entity type '{workflow_template.entity_type}'"
            )

        # Validate content type exists
        try:
            content_type = ContentType.objects.get(
                model=data['entity_type'].lower()
            )
        except ContentType.DoesNotExist:
            raise serializers.ValidationError(
                f"Content type for '{data['entity_type']}' does not exist"
            )

        data['workflow_template'] = workflow_template
        data['content_type'] = content_type

        return data

    def create(self, validated_data):
        """Create workflow instance and initial step executions"""
        workflow_template = validated_data['workflow_template']
        content_type = validated_data['content_type']
        entity_id = validated_data['entity_id']
        additional_data = validated_data.get('additional_data')
        initiated_by = self.context['request'].user

        # Create workflow instance
        workflow_instance = WorkflowInstance.objects.create(
            workflow_template=workflow_template,
            content_type=content_type,
            object_id=entity_id,
            status='pending',
            initiated_by=initiated_by,
            additional_data=additional_data
        )

        # Create step executions for all steps
        for step in workflow_template.steps.all():
            # Determine who to assign the step to
            assigned_to = step.approver_user if step.approver_user else None

            WorkflowStepExecution.objects.create(
                workflow_instance=workflow_instance,
                workflow_step=step,
                assigned_to=assigned_to,
                status='pending' if step.step_order == 1 else 'pending'
            )

        # Create audit log
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type='created',
            action_description=f"Workflow instance created for {content_type.model} #{entity_id}",
            performed_by=initiated_by
        )

        return workflow_instance


class WorkflowDelegationSerializer(serializers.ModelSerializer):
    """Serializer for workflow delegations"""
    delegated_from_user = UserSerializer(source='delegated_from', read_only=True)
    delegated_to_user = UserSerializer(source='delegated_to', read_only=True)

    class Meta:
        model = WorkflowDelegation
        fields = [
            'id', 'workflow_step_execution', 'delegated_from',
            'delegated_from_user', 'delegated_to', 'delegated_to_user',
            'reason', 'is_active', 'delegated_at', 'expires_at'
        ]
        read_only_fields = ['id', 'delegated_from', 'delegated_at']

    def validate(self, data):
        """Validate delegation data"""
        # Ensure user is not delegating to themselves
        delegated_from = self.context['request'].user
        delegated_to = data.get('delegated_to')

        if delegated_from == delegated_to:
            raise serializers.ValidationError(
                "Cannot delegate to yourself"
            )

        # Validate expiry date is in future
        if data.get('expires_at'):
            from django.utils import timezone
            if data['expires_at'] <= timezone.now():
                raise serializers.ValidationError(
                    "Expiry date must be in the future"
                )

        return data


class WorkflowAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for workflow audit logs"""
    performed_by_user = UserSerializer(source='performed_by', read_only=True)

    class Meta:
        model = WorkflowAuditLog
        fields = [
            'id', 'workflow_instance', 'action_type', 'action_description',
            'performed_by', 'performed_by_user', 'workflow_state_snapshot',
            'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = fields


class WorkflowActionSerializer(serializers.Serializer):
    """Serializer for workflow step actions (approve/reject)"""
    action = serializers.ChoiceField(
        choices=['approve', 'reject', 'skip', 'delegate']
    )
    comments = serializers.CharField(required=False, allow_blank=True)
    delegated_to_id = serializers.IntegerField(required=False)

    def validate(self, data):
        """Validate action data"""
        action = data.get('action')

        # Reject requires comments
        if action == 'reject' and not data.get('comments'):
            raise serializers.ValidationError(
                "Comments are required when rejecting a step"
            )

        # Delegate requires delegated_to_id
        if action == 'delegate' and not data.get('delegated_to_id'):
            raise serializers.ValidationError(
                "delegated_to_id is required when delegating"
            )

        return data
