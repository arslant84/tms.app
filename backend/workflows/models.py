from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class WorkflowTemplate(models.Model):
    """
    Template defining a workflow that can be applied to different entity types
    (TRF, Visa, Transport, Accommodation, Expenses, etc.)
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    entity_type = models.CharField(
        max_length=100,
        help_text="Type of entity this workflow applies to (e.g., 'trf', 'visa', 'transport')"
    )
    is_active = models.BooleanField(default=True)

    # Workflow configuration
    allow_parallel_steps = models.BooleanField(
        default=False,
        help_text="Allow multiple steps to be active simultaneously"
    )
    auto_approve_on_condition = models.BooleanField(
        default=False,
        help_text="Automatically approve steps when conditions are met"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflow_templates_created'
    )

    class Meta:
        ordering = ['entity_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.entity_type})"


class WorkflowStep(models.Model):
    """
    Individual step within a workflow template
    Defines who can approve and in what order
    """
    workflow_template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='steps'
    )

    step_order = models.IntegerField(
        help_text="Order in which this step should be executed (1, 2, 3, ...)"
    )
    step_name = models.CharField(max_length=255)
    step_description = models.TextField(blank=True, null=True)

    # Who can approve this step
    approver_role = models.CharField(
        max_length=100,
        help_text="Role name required to approve this step (e.g., 'HOD', 'Finance')"
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_steps_assigned',
        help_text="Specific user assigned to this step (optional, overrides role)"
    )

    # Step behavior
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this step must be completed for workflow to proceed"
    )
    can_skip = models.BooleanField(
        default=False,
        help_text="Whether this step can be skipped"
    )
    requires_comments = models.BooleanField(
        default=False,
        help_text="Whether approver must provide comments"
    )

    # Time constraints
    sla_hours = models.IntegerField(
        null=True,
        blank=True,
        help_text="Service Level Agreement - expected hours to complete this step"
    )
    escalation_hours = models.IntegerField(
        null=True,
        blank=True,
        help_text="Hours before escalation notification is sent"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['workflow_template', 'step_order']
        unique_together = ['workflow_template', 'step_order']

    def __str__(self):
        return f"{self.workflow_template.name} - Step {self.step_order}: {self.step_name}"


class WorkflowCondition(models.Model):
    """
    Conditional logic for workflow steps
    Determines if a step should be executed based on entity data
    """
    workflow_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name='conditions'
    )

    condition_type = models.CharField(
        max_length=50,
        choices=[
            ('field_equals', 'Field Equals'),
            ('field_greater_than', 'Field Greater Than'),
            ('field_less_than', 'Field Less Than'),
            ('field_contains', 'Field Contains'),
            ('field_exists', 'Field Exists'),
            ('custom_logic', 'Custom Logic'),
        ]
    )

    field_name = models.CharField(
        max_length=100,
        help_text="Name of the field to check on the entity"
    )
    field_value = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Value to compare against"
    )

    # Logical operators
    logical_operator = models.CharField(
        max_length=10,
        choices=[
            ('AND', 'AND'),
            ('OR', 'OR'),
        ],
        default='AND',
        help_text="How to combine multiple conditions"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.workflow_step.step_name} - {self.condition_type}: {self.field_name}"


class WorkflowInstance(models.Model):
    """
    Instance of a workflow applied to a specific entity
    Tracks the current state of workflow execution
    """
    workflow_template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name='instances'
    )

    # Generic relation to any entity (TRF, Visa, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Workflow state
    status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
            ('on_hold', 'On Hold'),
        ],
        default='pending'
    )

    current_step_order = models.IntegerField(
        default=1,
        help_text="Current step order being executed"
    )

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Initiator
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflow_instances_initiated'
    )

    # Additional data
    additional_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional context data for workflow execution"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status', 'current_step_order']),
        ]

    def __str__(self):
        return f"{self.workflow_template.name} - Instance #{self.id} ({self.status})"


class WorkflowStepExecution(models.Model):
    """
    Execution record for each step in a workflow instance
    Tracks who approved/rejected and when
    """
    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name='step_executions'
    )
    workflow_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name='executions'
    )

    status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('skipped', 'Skipped'),
            ('delegated', 'Delegated'),
        ],
        default='pending'
    )

    # Approver information
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflow_steps_assigned_to',
        help_text="User assigned to complete this step"
    )
    actioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_steps_actioned',
        help_text="User who took action on this step"
    )

    # Action details
    comments = models.TextField(blank=True, null=True)
    action_date = models.DateTimeField(null=True, blank=True)

    # SLA tracking
    sla_due_date = models.DateTimeField(null=True, blank=True)
    escalation_date = models.DateTimeField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False)
    is_escalated = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['workflow_instance', 'workflow_step__step_order']
        unique_together = ['workflow_instance', 'workflow_step']

    def __str__(self):
        return f"{self.workflow_instance} - {self.workflow_step.step_name} ({self.status})"


class WorkflowDelegation(models.Model):
    """
    Delegation of workflow approval to another user
    """
    workflow_step_execution = models.ForeignKey(
        WorkflowStepExecution,
        on_delete=models.CASCADE,
        related_name='delegations'
    )

    delegated_from = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegations_made'
    )
    delegated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegations_received'
    )

    reason = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    delegated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When delegation expires (null = no expiry)"
    )

    class Meta:
        ordering = ['-delegated_at']

    def __str__(self):
        return f"{self.delegated_from.email} → {self.delegated_to.email}"


class WorkflowAuditLog(models.Model):
    """
    Comprehensive audit log for all workflow actions
    """
    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )

    action_type = models.CharField(
        max_length=50,
        choices=[
            ('created', 'Created'),
            ('started', 'Started'),
            ('step_completed', 'Step Completed'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('delegated', 'Delegated'),
            ('cancelled', 'Cancelled'),
            ('on_hold', 'Put On Hold'),
            ('resumed', 'Resumed'),
            ('escalated', 'Escalated'),
        ]
    )

    action_description = models.TextField()

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflow_actions_performed'
    )

    # Snapshot of workflow state at time of action
    workflow_state_snapshot = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON snapshot of workflow state when action was performed"
    )

    # Additional context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.workflow_instance} - {self.action_type} at {self.created_at}"
