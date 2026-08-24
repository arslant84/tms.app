"""
Adds the 'admin_processing_required' NotificationTemplate.

Gap: when a TRF, Transport, Visa, or Accommodation request finishes its
approval workflow, notify_workflow_completed() (workflows/notifications.py)
only ever notifies the requester ('Your request has been approved') - the
admin who actually needs to act next (Ticketing Admin books the flight,
Transport Admin arranges the vehicle, Visa Clerk processes the visa,
Accommodation Admin books the room) is never notified and has to check
their dashboard manually to find newly-approved work.

This migration only adds the template - it does NOT create any
WorkflowStepNotificationConfig rows or hardcode a role/module mapping.
The role-based recipient mechanism (recipient_types: ["role_<uuid>"], see
WorkflowNotifications._resolve_recipients) already supports this; an admin
can now attach this template to a 'workflow_completed' (or
'processing_completed') config on whichever step/role they choose via the
existing Workflow Configuration screen, per module, without any code
change - trigger_configured_notifications() already sends to every active
config for a given (step, event_type) pair, so this can sit alongside the
existing requester-facing 'workflow_completed' config rather than
replacing it.

Content follows the same style as the sibling 'workflow_completed' /
'processing_completed' templates (0004_update_notification_templates.py,
0022_seed_processing_completed_notifications.py in the workflows app).
"""

from django.db import migrations

SUBJECT = "Action Required: {{requestType}} Request #{{entityId}} Approved"
BODY = """Hi Team,

A **{{requestType}}** request (ID: **#{{entityId}}**) submitted by \
**{{requestorName}}** has been fully approved and is now ready for \
processing.

[View Request Details]({{actionUrl}})

Thank you,
The TMS Team"""
VARIABLES_AVAILABLE = [
    "requestorName",
    "requestType",
    "entityId",
    "actionUrl",
]


def create_admin_processing_required_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")

    event_type = NotificationEventType.objects.filter(name="WORKFLOW_UPDATED").first()

    NotificationTemplate.objects.update_or_create(
        name="admin_processing_required",
        defaults={
            "event_type": event_type,
            "subject": SUBJECT,
            "body": BODY,
            "notification_type": "both",
            "recipient_type": "approver",
            "variables_available": VARIABLES_AVAILABLE,
            "is_active": True,
        },
    )


def remove_admin_processing_required_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplate.objects.filter(name="admin_processing_required").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0010_add_workflow_started_template"),
    ]

    operations = [
        migrations.RunPython(
            create_admin_processing_required_template,
            remove_admin_processing_required_template,
        ),
    ]
