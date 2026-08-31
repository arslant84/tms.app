from django.contrib import admin

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


class WorkflowStepInline(admin.TabularInline):
    """Inline admin for workflow steps"""

    model = WorkflowStep
    extra = 1
    fields = [
        "step_order",
        "step_name",
        "approver_permission",
        "approver_role",
        "is_required",
    ]
    ordering = ["step_order"]


class WorkflowStepNotificationConfigInline(admin.TabularInline):
    """Inline admin for workflow step notification configurations"""

    model = WorkflowStepNotificationConfig
    extra = 0
    fields = ["event_type", "notification_template", "priority", "is_active"]
    ordering = ["event_type"]


class WorkflowConditionInline(admin.TabularInline):
    """Inline admin for workflow conditions"""

    model = WorkflowCondition
    extra = 0
    fields = [
        "condition_type",
        "field_name",
        "field_value",
        "logical_operator",
        "is_active",
    ]


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowTemplate model"""

    list_display = [
        "id",
        "name",
        "entity_type",
        "is_active",
        "allow_parallel_steps",
        "step_count",
        "created_by",
        "created_at",
    ]
    list_filter = ["entity_type", "is_active", "created_at"]
    search_fields = ["name", "description", "entity_type"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [WorkflowStepInline]
    ordering = ["entity_type", "name"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "description", "entity_type", "is_active")},
        ),
        (
            "Configuration",
            {"fields": ("allow_parallel_steps", "auto_approve_on_condition")},
        ),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def step_count(self, obj):
        """Display number of active steps"""
        return obj.steps.filter(is_active=True).count()

    step_count.short_description = "Steps"


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowStep model"""

    list_display = [
        "id",
        "workflow_template",
        "step_order",
        "step_name",
        "approver_permission",
        "approver_role",
        "is_required",
        "can_skip",
        "is_active",
    ]
    list_filter = [
        "is_required",
        "can_skip",
        "requires_comments",
        "is_active",
        "workflow_template",
    ]
    search_fields = [
        "step_name",
        "step_description",
        "approver_permission",
        "approver_role",
    ]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [WorkflowStepNotificationConfigInline, WorkflowConditionInline]
    ordering = ["workflow_template", "step_order"]

    fieldsets = (
        ("Template", {"fields": ("workflow_template",)}),
        ("Step Details", {"fields": ("step_order", "step_name", "step_description")}),
        (
            "Approval Configuration",
            {
                "fields": ("approver_permission", "approver_role", "approver_user"),
                "description": "Use approver_permission (preferred) or approver_role (deprecated) to assign approvers",
            },
        ),
        (
            "Behavior",
            {"fields": ("is_required", "can_skip", "requires_comments", "is_active")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(WorkflowCondition)
class WorkflowConditionAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowCondition model"""

    list_display = [
        "id",
        "workflow_step",
        "condition_type",
        "field_name",
        "field_value",
        "logical_operator",
        "is_active",
    ]
    list_filter = ["condition_type", "logical_operator", "is_active"]
    search_fields = ["field_name", "field_value"]
    readonly_fields = ["created_at"]
    ordering = ["workflow_step", "created_at"]


@admin.register(WorkflowStepNotificationConfig)
class WorkflowStepNotificationConfigAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowStepNotificationConfig model"""

    list_display = [
        "id",
        "workflow_step",
        "event_type",
        "notification_template",
        "priority",
        "is_active",
        "send_email",
        "send_system_notification",
    ]
    list_filter = [
        "event_type",
        "priority",
        "is_active",
        "send_email",
        "send_system_notification",
    ]
    search_fields = ["workflow_step__step_name", "notification_template__name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["workflow_step", "event_type"]

    fieldsets = (
        ("Workflow Step", {"fields": ("workflow_step",)}),
        (
            "Notification Configuration",
            {"fields": ("event_type", "notification_template", "priority")},
        ),
        ("Recipients", {"fields": ("recipient_types", "custom_recipients")}),
        (
            "Delivery Options",
            {"fields": ("is_active", "send_email", "send_system_notification")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class WorkflowStepExecutionInline(admin.TabularInline):
    """Inline admin for workflow step executions"""

    model = WorkflowStepExecution
    extra = 0
    fields = ["workflow_step", "status", "assigned_to", "actioned_by", "action_date"]
    readonly_fields = ["actioned_by", "action_date"]
    ordering = ["workflow_step__step_order"]


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowInstance model"""

    list_display = [
        "id",
        "workflow_template",
        "status",
        "current_step_order",
        "entity_display",
        "initiated_by",
        "started_at",
    ]
    list_filter = ["status", "workflow_template", "content_type", "started_at"]
    search_fields = ["id", "workflow_template__name", "initiated_by__email"]
    readonly_fields = ["started_at", "completed_at", "created_at", "updated_at"]
    inlines = [WorkflowStepExecutionInline]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "Workflow Configuration",
            {"fields": ("workflow_template", "status", "current_step_order")},
        ),
        ("Entity Reference", {"fields": ("content_type", "object_id")}),
        ("Initiator", {"fields": ("initiated_by",)}),
        ("Additional Data", {"fields": ("additional_data",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {
                "fields": ("started_at", "completed_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def entity_display(self, obj):
        """Display entity information"""
        if obj.content_object:
            return f"{obj.content_type.model} #{obj.object_id}"
        return f"{obj.content_type.model} #{obj.object_id} (deleted)"

    entity_display.short_description = "Entity"


@admin.register(WorkflowStepExecution)
class WorkflowStepExecutionAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowStepExecution model"""

    list_display = [
        "id",
        "workflow_instance",
        "workflow_step_name",
        "status",
        "assigned_to",
        "actioned_by",
        "action_date",
    ]
    list_filter = ["status", "action_date"]
    search_fields = [
        "workflow_instance__id",
        "workflow_step__step_name",
        "assigned_to__email",
        "actioned_by__email",
    ]
    readonly_fields = ["actioned_by", "action_date", "created_at", "updated_at"]
    ordering = ["workflow_instance", "workflow_step__step_order"]

    fieldsets = (
        ("Workflow Instance", {"fields": ("workflow_instance", "workflow_step")}),
        ("Status", {"fields": ("status",)}),
        ("Assignment", {"fields": ("assigned_to", "actioned_by", "action_date")}),
        ("Comments", {"fields": ("comments",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def workflow_step_name(self, obj):
        """Display step name"""
        return obj.workflow_step.step_name

    workflow_step_name.short_description = "Step"


@admin.register(WorkflowDelegation)
class WorkflowDelegationAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowDelegation model"""

    list_display = [
        "id",
        "workflow_step_execution",
        "delegated_from",
        "delegated_to",
        "is_active",
        "delegated_at",
        "expires_at",
    ]
    list_filter = ["is_active", "delegated_at", "expires_at"]
    search_fields = ["delegated_from__email", "delegated_to__email", "reason"]
    readonly_fields = ["delegated_at"]
    ordering = ["-delegated_at"]

    fieldsets = (
        (
            "Delegation",
            {"fields": ("workflow_step_execution", "delegated_from", "delegated_to")},
        ),
        ("Details", {"fields": ("reason", "is_active", "expires_at")}),
        ("Timestamp", {"fields": ("delegated_at",)}),
    )


@admin.register(WorkflowAuditLog)
class WorkflowAuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowAuditLog model"""

    list_display = [
        "id",
        "workflow_instance",
        "action_type",
        "performed_by",
        "created_at",
    ]
    list_filter = ["action_type", "created_at"]
    search_fields = [
        "workflow_instance__id",
        "action_description",
        "performed_by__email",
    ]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Workflow Instance", {"fields": ("workflow_instance",)}),
        ("Action", {"fields": ("action_type", "action_description", "performed_by")}),
        (
            "State Snapshot",
            {"fields": ("workflow_state_snapshot",), "classes": ("collapse",)},
        ),
        ("Context", {"fields": ("ip_address", "user_agent"), "classes": ("collapse",)}),
        ("Timestamp", {"fields": ("created_at",)}),
    )
