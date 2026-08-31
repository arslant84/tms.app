"""
Adds the 'fully_arranged' NotificationTemplate.

trf/services.py::notify_department_focal_if_ready() previously built its
notification's title/message as inline Python f-strings, bypassing the
template system entirely - unlike every other notification in the app, an
admin had no way to see or change that wording, or to add/remove
recipients, without editing code. This template, plus the new
'fully_arranged' event type (see workflows/0029) and 'department_focal'
recipient type (workflows/notification_dispatch.py), replace that with the
same admin-configurable path everything else in the Notification Config
screen already uses.

Content mirrors the previous hardcoded wording as closely as the shared
template variable set allows.
"""

from django.db import migrations

SUBJECT = "Travel Arrangements Completed — {{entityId}}"
BODY = """Hi Team,

All travel arrangements for **{{requestorName}}**'s **{{requestType}}** \
request (ID: **#{{entityId}}**) are now complete.

[View Request Details]({{actionUrl}})

Thank you,
The TMS Team"""
VARIABLES_AVAILABLE = [
    "requestorName",
    "requestType",
    "entityId",
    "actionUrl",
]


def create_fully_arranged_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")

    event_type = NotificationEventType.objects.filter(name="WORKFLOW_UPDATED").first()

    NotificationTemplate.objects.update_or_create(
        name="fully_arranged",
        defaults={
            "event_type": event_type,
            "subject": SUBJECT,
            "body": BODY,
            "notification_type": "both",
            "recipient_type": "both",
            "variables_available": VARIABLES_AVAILABLE,
            "is_active": True,
        },
    )


def remove_fully_arranged_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    NotificationTemplate.objects.filter(name="fully_arranged").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0012_add_step_approved_template"),
    ]

    operations = [
        migrations.RunPython(
            create_fully_arranged_template, remove_fully_arranged_template
        ),
    ]
