"""
One-time data migration: seeds the 'fully_arranged' notification config onto
each TSR workflow template's final approval step - the trigger
trf/services.py::notify_department_focal_if_ready() now fires through
(see workflows/0029_alter_workflowstepnotificationconfig_event_type and
notifications/0013_add_fully_arranged_template), instead of a hardcoded
recipient/message.

Only Domestic/External Parties/Overseas get this - notify_department_focal_if_ready()
is only ever called for TravelRequest objects (flight ticketing, meal status,
accommodation assign, transport complete are all TRF-linked touchpoints).
Ad-Hoc Transport/Visa's own standalone completion uses the separate
'processing_completed' event.

Two separate rows per template (same reasoning as 0027's admin/requester
split): Department Focal and the requester get different wording -
'fully_arranged' is "Hi Team..." phrasing appropriate for Department Focal,
while the requester gets the existing requester-facing 'processing_completed'
template ("Your ... request ... has been completed") reused here for its
matching tone, not because the two events are otherwise related.

Idempotent: skips a step that already has a 'fully_arranged' config for the
given recipient group.
"""

from django.db import migrations

_TSR_ENTITY_TYPES = [
    "travelrequest_domestic",
    "travelrequest_external",
    "travelrequest_overseas",
]


def seed_fully_arranged_notifications(apps, schema_editor):
    WorkflowStep = apps.get_model("workflows", "WorkflowStep")
    WorkflowTemplate = apps.get_model("workflows", "WorkflowTemplate")
    WorkflowStepNotificationConfig = apps.get_model(
        "workflows", "WorkflowStepNotificationConfig"
    )
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")

    fully_arranged_template = NotificationTemplate.objects.filter(
        name="fully_arranged"
    ).first()
    processing_completed_template = NotificationTemplate.objects.filter(
        name="processing_completed"
    ).first()
    if not (fully_arranged_template and processing_completed_template):
        return

    rows = [
        (["department_focal"], fully_arranged_template),
        (["requester"], processing_completed_template),
    ]

    for entity_type in _TSR_ENTITY_TYPES:
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

        for recipient_types, notification_template in rows:
            already_exists = WorkflowStepNotificationConfig.objects.filter(
                workflow_step=last_step,
                event_type="fully_arranged",
                notification_template=notification_template,
            ).exists()
            if already_exists:
                continue

            WorkflowStepNotificationConfig.objects.create(
                workflow_step=last_step,
                event_type="fully_arranged",
                notification_template=notification_template,
                recipient_types=recipient_types,
                custom_recipients=[],
                is_active=True,
                send_email=True,
                send_system_notification=True,
                priority="normal",
            )


def remove_fully_arranged_notifications(apps, schema_editor):
    WorkflowStepNotificationConfig = apps.get_model(
        "workflows", "WorkflowStepNotificationConfig"
    )
    WorkflowStepNotificationConfig.objects.filter(
        event_type="fully_arranged",
        workflow_step__workflow_template__entity_type__in=_TSR_ENTITY_TYPES,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0029_alter_workflowstepnotificationconfig_event_type"),
        ("notifications", "0013_add_fully_arranged_template"),
    ]

    operations = [
        migrations.RunPython(
            seed_fully_arranged_notifications, remove_fully_arranged_notifications
        ),
    ]
