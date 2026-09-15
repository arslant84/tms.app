"""
One-time cleanup: UserNotification.is_read=True rows that predate the
mark-as-read-deletes-it behavior change (notifications/views.py's
mark_as_read/mark_all_as_read, notifications/admin.py's mark_as_read action).
Before that change, "read" just flipped is_read=True and left the row in
place - these are the leftovers from that, and under the new policy a read
notification has nothing left to act on, so they're deleted rather than
displayed as stale "read" rows in the notification list.
"""

from django.db import migrations


def delete_read_notifications(apps, schema_editor):
    UserNotification = apps.get_model("notifications", "UserNotification")
    count, _ = UserNotification.objects.filter(is_read=True).delete()
    print(f"Deleted {count} stale read UserNotification(s)")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0015_widen_object_id_to_bigint"),
    ]

    operations = [
        migrations.RunPython(delete_read_notifications, noop_reverse),
    ]
