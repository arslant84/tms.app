"""
Seeds the 'processing_completed' NotificationTemplate and
WorkflowStepNotificationConfig rows so the newly-added event type (see
0021_add_processing_completed_event_type.py) is actually usable through
the admin-configurable notification system, matching the precedent set
by 0006_add_workflow_cancelled_template.py in the notifications app.

Unlike 'workflow_completed'/'workflow_cancelled' (seeded for every step of
every workflow template, since every workflow eventually completes or can
be cancelled), 'processing_completed' only applies to the two modules
that actually have a distinct post-approval admin processing step -
Transport ("Transport Request Approval Workflow", vehicle assignment) and
Visa ("Visa Application Approval Workflow", visa clerk processing). TRF
and Accommodation have no equivalent complete() action, so seeding this
config on their templates would create a notification that can never
fire. Configs are attached to each template's last step, mirroring where
'workflow_completed' configs already live.
"""

from django.db import migrations

SUBJECT = "Your {{requestType}} Request #{{entityId}} Has Been Completed"
BODY = """Hi {{requestorName}},

Your **{{requestType}}** request (ID: **#{{entityId}}**) has finished processing and is now marked as completed.

**Summary:**
*   **Completed By:** {{processorName}}
*   **Completion Date:** {{completionDate}}
*   **Details:** {{completionDetails}}

[View Request Details]({{actionUrl}})

Thank you,
The TMS Team"""
VARIABLES_AVAILABLE = [
    "requestorName",
    "requestType",
    "entityId",
    "processorName",
    "completionDate",
    "completionDetails",
    "actionUrl",
]

TARGET_TEMPLATES = [
    "Transport Request Approval Workflow",
    "Visa Application Approval Workflow",
]


def seed_processing_completed(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")
    WorkflowTemplate = apps.get_model("workflows", "WorkflowTemplate")
    WorkflowStepNotificationConfig = apps.get_model(
        "workflows", "WorkflowStepNotificationConfig"
    )

    event_type = NotificationEventType.objects.filter(name="WORKFLOW_UPDATED").first()

    template, _ = NotificationTemplate.objects.update_or_create(
        name="processing_completed",
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

    for template_name in TARGET_TEMPLATES:
        workflow_template = WorkflowTemplate.objects.filter(name=template_name).first()
        if not workflow_template:
            continue

        last_step = workflow_template.steps.order_by("-step_order").first()
        if not last_step:
            continue

        WorkflowStepNotificationConfig.objects.get_or_create(
            workflow_step=last_step,
            event_type="processing_completed",
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


def remove_processing_completed(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    WorkflowStepNotificationConfig = apps.get_model(
        "workflows", "WorkflowStepNotificationConfig"
    )

    WorkflowStepNotificationConfig.objects.filter(
        event_type="processing_completed"
    ).delete()
    NotificationTemplate.objects.filter(name="processing_completed").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0021_add_processing_completed_event_type"),
        ("notifications", "0009_fix_stale_action_urls"),
    ]

    operations = [
        migrations.RunPython(seed_processing_completed, remove_processing_completed),
    ]
