"""
Fixes 'approval_reminder's body: it referenced {{reminderType}},
{{statusMessage}}, {{reminderMessage}} - none of which
WorkflowNotifications._build_notification_context() (workflows/notifications.py)
ever populates when rendering a configured template via
trigger_configured_notifications(). Those placeholders would have rendered
as literal, unresolved text in every reminder notification once
send_step_reminders (see workflows/management/commands/send_step_reminders.py)
started actually firing this template for the first time - this template
was never exercised dynamically before.
"""

from django.db import migrations

NEW_BODY = """Hi {{approverName}},

This is a reminder that {{requestType}} request #{{entityId}} from {{requestorName}} is still awaiting your approval.

**Due:** {{dueDate}}

Please take action to avoid delays.

[Review & Approve]({{actionUrl}})

Thank you,
The TMS Team"""
NEW_VARIABLES_AVAILABLE = [
    "approverName",
    "requestType",
    "entityId",
    "requestorName",
    "dueDate",
    "actionUrl",
]

OLD_BODY = """Hi {{approverName}},

This is a {{reminderType}} for the **{{requestType}}** request (ID: **#{{entityId}}**).

**Status:** {{statusMessage}}

{{reminderMessage}}

Please take action to avoid delays.

"""
OLD_VARIABLES_AVAILABLE = [
    "approverName",
    "reminderType",
    "requestType",
    "entityId",
    "statusMessage",
    "reminderMessage",
]


def fix_approval_reminder_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplate.objects.filter(name="approval_reminder").update(
        body=NEW_BODY, variables_available=NEW_VARIABLES_AVAILABLE
    )


def revert_approval_reminder_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplate.objects.filter(name="approval_reminder").update(
        body=OLD_BODY, variables_available=OLD_VARIABLES_AVAILABLE
    )


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0006_add_workflow_cancelled_template"),
    ]

    operations = [
        migrations.RunPython(
            fix_approval_reminder_template, revert_approval_reminder_template
        ),
    ]
