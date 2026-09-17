# Generated manually on 2026-09-17

from django.db import migrations

DEAD_EVENT_TYPES = [
    # Never dispatched by workflows/engine.py, notifications.py, or
    # notification_dispatch.py - the actual assignment notification uses
    # APPROVAL_REQUESTED, and resubmission re-enters through
    # notify_workflow_started() (WORKFLOW_STARTED), not these. Toggling
    # them on /notifications/preferences never had any effect.
    "STEP_ASSIGNED",
    "REQUEST_RESUBMITTED",
]


def remove_unwired_event_types(apps, schema_editor):
    NotificationEventType = apps.get_model("notifications", "NotificationEventType")
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")

    event_types = NotificationEventType.objects.filter(name__in=DEAD_EVENT_TYPES)
    NotificationTemplate.objects.filter(event_type__in=event_types).delete()
    event_types.delete()


def noop_reverse(apps, schema_editor):
    """Irreversible: these rows were dead weight, not worth restoring."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0017_remove_dead_push_digest_quiet_hours_fields"),
    ]

    operations = [
        migrations.RunPython(remove_unwired_event_types, noop_reverse),
    ]
