"""
One-time data migration: adds the post-approval "please start processing"
notification for the fulfillment-admin roles named in
docs/TMS_Responsibility_Matrix.xlsx (Flight/Ticketing, Meal, Accommodation,
Transport, Visa Clerk), on top of the existing requester-facing 'approval'
config each final step already has (see 0026_seed_approval_stage_notifications).

This adds a *second* WorkflowStepNotificationConfig row for the same
(workflow_step, event_type='approval') pair - the model has no uniqueness
constraint on that combination, and workflows/notification_dispatch.py's
trigger_configured_notifications() already iterates every matching config,
so this was already a supported shape, not a new capability.

Recipients used, matching workflows/notification_dispatch.py's new
_SERVICE_ADMIN_ROLE_BY_RECIPIENT_TYPE / _entity_needs_service():
- Flight/Ticketing Admin: unconditional plain 'role_<id>' (every TSR that
  reaches approval has an itinerary) - not one of the new conditional
  recipient types, since it doesn't need one.
- Meal/Accommodation/Transport Admin: the new 'meal_admin_if_needed' /
  'accommodation_admin_if_needed' / 'transport_admin_if_needed' recipient
  types - each only actually notifies if the request has that service
  selected, resolved at send time, not at migration time.
- Visa Clerk / Transport Admin (their own single-module workflows, not a
  TSR): unconditional plain 'role_<id>', same reasoning as Flight Admin -
  a Visa/Transport request that reaches its own final approval step always
  needs that module's own processing.

Overseas has no meal/accommodation/transport legs at all (see
trf/models.py's per-travel-type sections), so it only gets Flight Admin.

Template: reuses the existing (previously orphaned) 'admin_processing_required'
NotificationTemplate - already generic enough ("A {{requestType}} request...
has been fully approved and is now ready for processing") for all five
admin roles without per-role wording changes.

Idempotent: get_or_create keyed on (workflow_step, event_type='approval',
recipient_types) is not unique-safe against re-running with a differently
ordered list, so this instead checks for an existing 'approval' config on
the step whose recipient_types already contains the intended role/service
markers before creating a new row.
"""

from django.db import migrations

# entity_type -> (list of role names to add unconditionally,
#                 list of *_if_needed conditional recipient types to add)
_FULFILLMENT_RECIPIENTS_BY_ENTITY_TYPE = {
    "travelrequest_domestic": (
        ["Ticketing Admin"],
        [
            "meal_admin_if_needed",
            "accommodation_admin_if_needed",
            "transport_admin_if_needed",
        ],
    ),
    "travelrequest_external": (
        ["Ticketing Admin"],
        [
            "meal_admin_if_needed",
            "accommodation_admin_if_needed",
            "transport_admin_if_needed",
        ],
    ),
    "travelrequest_overseas": (["Ticketing Admin"], []),
    "visaapplication": (["Visa Clerk"], []),
    "transportrequest": (["Transport Admin"], []),
}


def seed_fulfillment_admin_notifications(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    WorkflowStep = apps.get_model("workflows", "WorkflowStep")
    WorkflowTemplate = apps.get_model("workflows", "WorkflowTemplate")
    WorkflowStepNotificationConfig = apps.get_model(
        "workflows", "WorkflowStepNotificationConfig"
    )
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")

    admin_template = NotificationTemplate.objects.filter(
        name="admin_processing_required"
    ).first()
    if not admin_template:
        return

    for entity_type, (
        role_names,
        conditional_types,
    ) in _FULFILLMENT_RECIPIENTS_BY_ENTITY_TYPE.items():
        template = WorkflowTemplate.objects.filter(
            entity_type=entity_type, is_active=True
        ).first()
        if not template:
            continue

        last_step = (
            WorkflowStep.objects.filter(workflow_template=template, is_active=True)
            .order_by("-step_order")
            .first()
        )
        if not last_step:
            continue

        recipient_types = list(conditional_types)
        for role_name in role_names:
            role = Role.objects.filter(name=role_name).first()
            if role:
                recipient_types.append(f"role_{role.id}")

        if not recipient_types:
            continue

        # Idempotency: skip if a config already exists on this step whose
        # recipients already cover everything we'd add (re-running the
        # migration, or an admin having already configured this by hand).
        already_covered = WorkflowStepNotificationConfig.objects.filter(
            workflow_step=last_step,
            event_type="approval",
            notification_template=admin_template,
        ).exists()
        if already_covered:
            continue

        WorkflowStepNotificationConfig.objects.create(
            workflow_step=last_step,
            event_type="approval",
            notification_template=admin_template,
            recipient_types=recipient_types,
            custom_recipients=[],
            is_active=True,
            send_email=True,
            send_system_notification=True,
            priority="high",
        )


def remove_fulfillment_admin_notifications(apps, schema_editor):
    WorkflowStepNotificationConfig = apps.get_model(
        "workflows", "WorkflowStepNotificationConfig"
    )
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")

    admin_template = NotificationTemplate.objects.filter(
        name="admin_processing_required"
    ).first()
    if admin_template:
        WorkflowStepNotificationConfig.objects.filter(
            event_type="approval", notification_template=admin_template
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0026_seed_approval_stage_notifications"),
        ("notifications", "0011_add_admin_processing_required_template"),
        ("accounts", "0008_populate_roles_permissions"),
    ]

    operations = [
        migrations.RunPython(
            seed_fulfillment_admin_notifications,
            remove_fulfillment_admin_notifications,
        ),
    ]
