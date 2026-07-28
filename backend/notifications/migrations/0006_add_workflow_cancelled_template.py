"""
Adds the 'workflow_cancelled' NotificationTemplate, which never existed.

WorkflowNotifications.notify_workflow_cancelled() (workflows/notifications.py)
has always fallen back to hardcoded text because no config could ever exist
for the 'workflow_cancelled' event type without a template to point at.
This closes that gap alongside the 'workflow_completed' event-type default
config added in the same fix (see
workflows/management/commands/populate_default_notification_configs.py and
workflows/serializers.py's WorkflowTemplateCreateSerializer.DEFAULT_NOTIFICATION_CONFIGS).

Content follows the exact style of the sibling 'workflow_rejected' /
'workflow_completed' templates already in this table (see
0004_update_notification_templates.py).
"""

from django.db import migrations

SUBJECT = "Your {{requestType}} Request #{{entityId}} Has Been Cancelled"
BODY = """Hi {{requestorName}},

Your **{{requestType}}** request (ID: **#{{entityId}}**) has been cancelled.

You can submit a new request at any time.

[View Request Details]({{actionUrl}})

Thank you,
The TMS Team"""
# Note: 'cancellationReason' is intentionally not referenced here.
# WorkflowNotifications.trigger_configured_notifications() (workflows/notifications.py)
# renders configured templates from _build_notification_context(step_execution) only -
# the cancellation `reason` param passed to notify_workflow_cancelled() at call time
# isn't part of that context and would render as a literal, unresolved
# "{{cancellationReason}}" if referenced here.
VARIABLES_AVAILABLE = [
    "requestorName",
    "requestType",
    "entityId",
    "actionUrl",
]


def create_workflow_cancelled_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")

    event_type = NotificationEventType.objects.filter(name="WORKFLOW_CANCELLED").first()

    NotificationTemplate.objects.update_or_create(
        name="workflow_cancelled",
        defaults={
            "event_type": event_type,
            "subject": SUBJECT,
            "body": BODY,
            "notification_type": "both",
            "recipient_type": "requestor",
            "variables_available": VARIABLES_AVAILABLE,
            "is_active": True,
        },
    )


def remove_workflow_cancelled_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplate.objects.filter(name="workflow_cancelled").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0005_remove_escalation_template"),
    ]

    operations = [
        migrations.RunPython(
            create_workflow_cancelled_template, remove_workflow_cancelled_template
        ),
    ]
