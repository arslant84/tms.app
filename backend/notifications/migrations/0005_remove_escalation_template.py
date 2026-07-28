"""
Data cleanup following the removal of the escalation notification feature
(workflows/migrations/0013_remove_workflowstep_escalation_hours_and_more.py).

The 'escalation_required' NotificationTemplate and 'ESCALATION'
NotificationEventType rows are no longer reachable by any code path:
WorkflowStepNotificationConfig.EVENT_TYPE_CHOICES no longer has an
'escalation' option, so no config can ever be created pointing at either
row again. Confirmed 0 WorkflowStepNotificationConfig rows referenced the
template before removing it.
"""

from django.db import migrations


def remove_escalation_notification_data(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")

    NotificationTemplate.objects.filter(name="escalation_required").delete()
    NotificationEventType.objects.filter(name="ESCALATION").delete()


def restore_escalation_notification_data(apps, schema_editor):
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")

    event_type, _ = NotificationEventType.objects.get_or_create(
        name="ESCALATION",
        defaults={
            "description": "Step escalated due to SLA timeout",
            "category": "workflow",
            "module": "general",
            "is_active": True,
        },
    )
    NotificationTemplate.objects.get_or_create(
        name="escalation_required",
        defaults={
            "event_type": event_type,
            "subject": "Escalation: {{requestType}} Request #{{entityId}} is Overdue",
            "body": (
                "{{requestType}} request #{{entityId}} is overdue and has been "
                "escalated.\n\n→ Review: {{actionUrl}}"
            ),
            "notification_type": "both",
            "recipient_type": "approver",
            "variables_available": ["requestType", "entityId", "actionUrl"],
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0004_update_notification_templates"),
    ]

    operations = [
        migrations.RunPython(
            remove_escalation_notification_data, restore_escalation_notification_data
        ),
    ]
