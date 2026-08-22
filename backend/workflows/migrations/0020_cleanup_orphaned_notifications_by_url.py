"""
Follow-up to 0019: that migration only removed orphaned UserNotification
rows whose content_type/object_id pointed straight at the deleted entity.
In practice NotificationService.create_notification() is usually called
with content_object=<the WorkflowInstance> (not the entity) or with no
content_object at all, so content_type/object_id on UserNotification
almost never actually references the entity - only action_url does (see
workflows/notifications.py's _get_action_url). Matching by content_type/
object_id alone left 520 stale notifications behind, still 404ing when
clicked (e.g. GET /api/transport/requests/85/ for a TransportRequest
deleted the day before). This migration matches by the action_url's
trailing /<route-segment>/<id> instead.
"""

import re

from django.db import migrations

ROUTE_SEGMENTS = {
    "trf": ("trf", "TravelRequest"),
    "transport": ("transport", "TransportRequest"),
    "visa": ("visa", "VisaApplication"),
    "accommodation": ("accommodation", "AccommodationRequest"),
}

URL_PATTERN = re.compile(r"/(trf|transport|visa|accommodation)/(\d+)$")


def cleanup_orphans(apps, schema_editor):
    UserNotification = apps.get_model("notifications", "UserNotification")

    existing_ids = {}
    for segment, (app_label, model_name) in ROUTE_SEGMENTS.items():
        Model = apps.get_model(app_label, model_name)
        existing_ids[segment] = set(Model.objects.values_list("pk", flat=True))

    orphaned_ids = []
    qs = UserNotification.objects.exclude(action_url__isnull=True).exclude(
        action_url=""
    )
    for notification in qs.only("id", "action_url"):
        match = URL_PATTERN.search(notification.action_url)
        if not match:
            continue
        segment, object_id = match.group(1), int(match.group(2))
        if object_id not in existing_ids[segment]:
            orphaned_ids.append(notification.id)

    if orphaned_ids:
        count, _ = UserNotification.objects.filter(id__in=orphaned_ids).delete()
        print(f"Cleaned up {count} orphaned UserNotification(s) matched by action_url")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0019_cleanup_orphaned_workflow_instances"),
        ("trf", "__latest__"),
        ("transport", "__latest__"),
        ("visa", "__latest__"),
        ("accommodation", "__latest__"),
    ]

    operations = [
        migrations.RunPython(cleanup_orphans, noop_reverse),
    ]
