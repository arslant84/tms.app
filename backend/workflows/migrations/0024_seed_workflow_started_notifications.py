"""
Seeds WorkflowStepNotificationConfig rows for the newly-added 'workflow_started'
event type (see 0023_add_workflow_started_event_type.py), attaching them to
each active WorkflowTemplate's first step - the only step
WorkflowNotifications.notify_workflow_started() (workflows/notifications.py)
ever passes to trigger_configured_notifications() for this event, since it
fires once, when the workflow (and its first step) is created.

Unlike 'workflow_completed'/'workflow_cancelled' (seeded on every step, since
any step could end up being the *last* one at completion/cancellation time),
'workflow_started' only ever needs a config on step_order=1 - seeding it on
every step would create rows that can never be looked up.

The template itself is created by notifications/0010_add_workflow_started_template.py,
matching the precedent set by 0006_add_workflow_cancelled_template.py /
0022_seed_processing_completed_notifications.py.
"""

from django.db import migrations


def seed_workflow_started(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    WorkflowTemplate = apps.get_model("workflows", "WorkflowTemplate")
    WorkflowStepNotificationConfig = apps.get_model(
        "workflows", "WorkflowStepNotificationConfig"
    )

    template = NotificationTemplate.objects.filter(name="workflow_started").first()
    if not template:
        return

    for workflow_template in WorkflowTemplate.objects.filter(is_active=True):
        first_step = workflow_template.steps.filter(step_order=1).first()
        if not first_step:
            continue

        WorkflowStepNotificationConfig.objects.get_or_create(
            workflow_step=first_step,
            event_type="workflow_started",
            defaults={
                "notification_template": template,
                "recipient_types": ["requester"],
                "custom_recipients": [],
                "is_active": True,
                "send_email": True,
                "send_system_notification": True,
                "priority": "normal",
            },
        )


def remove_workflow_started_configs(apps, schema_editor):
    WorkflowStepNotificationConfig = apps.get_model(
        "workflows", "WorkflowStepNotificationConfig"
    )
    WorkflowStepNotificationConfig.objects.filter(
        event_type="workflow_started"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0023_add_workflow_started_event_type"),
        ("notifications", "0010_add_workflow_started_template"),
    ]

    operations = [
        migrations.RunPython(seed_workflow_started, remove_workflow_started_configs),
    ]
