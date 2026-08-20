"""
Data cleanup following the removal of the SLA due-date / reminder feature
(workflows/migrations/0018_remove_sla_tracking.py).

The 'approval_reminder' NotificationTemplate and 'APPROVAL_REMINDER'
NotificationEventType rows are no longer reachable by any code path -
send_step_reminders (the only thing that ever fired the 'reminder' event)
has been deleted, and 'reminder' is no longer a valid
WorkflowStepNotificationConfig.event_type choice. Mirrors
0005_remove_escalation_template.py's precedent for a defunct-feature
template removal.

Also strips the "Due Date" line from the still-active 'approval_required'
template (the one used for every real approval-assignment email) - its
{{dueDate}} variable is no longer populated by workflows/notifications.py.
"""

from django.db import migrations

APPROVAL_REQUIRED_BODY_WITH_DUE_DATE = (
    "Hi {{approverName}},\n\n"
    "A **{{requestType}}** request (ID: **#{{entityId}}**) from **{{requestorName}}** "
    "requires your approval.\n\n"
    "**Details:**\n"
    "*   **Requestor:** {{requestorName}}\n"
    "*   **Due Date:** {{dueDate}}\n"
    "*   **Urgency:** {{urgencyHint}}\n\n"
    "Please review the request and take action by the due date.\n\n"
    "[Review & Approve]({{actionUrl}})\n\n"
    "Thank you,\n"
    "The TMS Team"
)

APPROVAL_REQUIRED_BODY_WITHOUT_DUE_DATE = (
    "Hi {{approverName}},\n\n"
    "A **{{requestType}}** request (ID: **#{{entityId}}**) from **{{requestorName}}** "
    "requires your approval.\n\n"
    "**Details:**\n"
    "*   **Requestor:** {{requestorName}}\n"
    "*   **Urgency:** {{urgencyHint}}\n\n"
    "Please review the request and take action.\n\n"
    "[Review & Approve]({{actionUrl}})\n\n"
    "Thank you,\n"
    "The TMS Team"
)


def remove_reminder_data_and_strip_due_date(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")

    NotificationTemplate.objects.filter(name="approval_reminder").delete()
    NotificationEventType.objects.filter(name="APPROVAL_REMINDER").delete()

    NotificationTemplate.objects.filter(name="approval_required").update(
        body=APPROVAL_REQUIRED_BODY_WITHOUT_DUE_DATE
    )


def restore_reminder_data_and_due_date(apps, schema_editor):
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")

    event_type, _ = NotificationEventType.objects.get_or_create(
        name="APPROVAL_REMINDER",
        defaults={
            "description": "Reminder that a pending approval step is due soon",
            "category": "workflow",
            "module": "general",
            "is_active": True,
        },
    )
    NotificationTemplate.objects.get_or_create(
        name="approval_reminder",
        defaults={
            "event_type": event_type,
            "subject": "Reminder: {{requestType}} Request #{{entityId}} Awaiting Your Approval",
            "body": (
                "Hi {{approverName}},\n\n"
                "This is a reminder that {{requestType}} request #{{entityId}} from "
                "{{requestorName}} is still awaiting your approval.\n\n"
                "**Due:** {{dueDate}}\n\n"
                "Please take action to avoid delays.\n\n"
                "[Review & Approve]({{actionUrl}})\n\n"
                "Thank you,\nThe TMS Team"
            ),
            "notification_type": "both",
            "recipient_type": "approver",
            "variables_available": [
                "approverName",
                "requestType",
                "entityId",
                "requestorName",
                "dueDate",
                "actionUrl",
            ],
            "is_active": True,
        },
    )

    NotificationTemplate.objects.filter(name="approval_required").update(
        body=APPROVAL_REQUIRED_BODY_WITH_DUE_DATE
    )


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0007_fix_approval_reminder_template"),
    ]

    operations = [
        migrations.RunPython(
            remove_reminder_data_and_strip_due_date,
            restore_reminder_data_and_due_date,
        ),
    ]
