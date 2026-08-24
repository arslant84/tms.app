"""
Adds the 'workflow_started' NotificationTemplate, which never existed.

WorkflowNotifications.notify_workflow_started() (workflows/notifications.py)
has always been fully hardcoded - no config could ever exist for the
'workflow_started' event type without a template to point at, unlike
assignment/approval/rejection/delegation/workflow_completed/workflow_cancelled,
which are all admin-configurable via WorkflowStepNotificationConfig. This
closes that gap the same way 0006_add_workflow_cancelled_template.py closed
the equivalent 'workflow_cancelled' gap - see
workflows/management/commands/populate_default_notification_configs.py and
workflows/serializers.py's WorkflowTemplateCreateSerializer.DEFAULT_NOTIFICATION_CONFIGS
for the matching default-config wiring added alongside this template.

Content mirrors the hardcoded text notify_workflow_started() previously sent
directly, using only variables _build_notification_context() actually
populates (requestorName, requestType, entityId, approverName, actionUrl).
"""

from django.db import migrations

SUBJECT = "Workflow Started: {{workflowName}}"
BODY = """Hi {{requestorName}},

Your **{{requestType}}** request (ID: **#{{entityId}}**) has been submitted \
and the approval workflow has started.

It is currently awaiting review by {{approverName}}.

[View Request Details]({{actionUrl}})

Thank you,
The TMS Team"""
VARIABLES_AVAILABLE = [
    "requestorName",
    "requestType",
    "entityId",
    "approverName",
    "actionUrl",
]


def create_workflow_started_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")

    event_type = NotificationEventType.objects.filter(name="WORKFLOW_STARTED").first()

    NotificationTemplate.objects.update_or_create(
        name="workflow_started",
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


def remove_workflow_started_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplate.objects.filter(name="workflow_started").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0009_fix_stale_action_urls"),
    ]

    operations = [
        migrations.RunPython(
            create_workflow_started_template, remove_workflow_started_template
        ),
    ]
