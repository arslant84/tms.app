"""
Adds the 'step_approved' NotificationTemplate.

The 'approval' event (fires every time any step approves, not just the
last one) has always used the 'workflow_completed' template for every
step - "Great news! Your request has been fully approved and processed."
That's correct wording for the *last* step, but wrong for an intermediate
step (e.g. Line Manager approving a Domestic TSR, which still has HOD
left to go): it tells the requester the request is fully done when it
isn't.

'step_approved' is the intermediate-step counterpart: it says who just
approved and that the request is moving to the next step, without
implying completion. See workflows/0026_seed_approval_stage_notifications
for where this gets wired to each template's non-final steps' 'approval'
event configs.
"""

from django.db import migrations

SUBJECT = "Update on Your {{requestType}} Request #{{entityId}}"
BODY = """Hi {{requestorName}},

Good news — your **{{requestType}}** request (ID: **#{{entityId}}**) has \
been approved by **{{approverName}}** and is now moving to the next approval \
step.

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


def create_step_approved_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")

    event_type = NotificationEventType.objects.filter(name="WORKFLOW_UPDATED").first()

    NotificationTemplate.objects.update_or_create(
        name="step_approved",
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


def remove_step_approved_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplate.objects.filter(name="step_approved").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0011_add_admin_processing_required_template"),
    ]

    operations = [
        migrations.RunPython(
            create_step_approved_template, remove_step_approved_template
        ),
    ]
