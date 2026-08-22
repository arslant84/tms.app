"""
Repairs UserNotification.action_url for rows created before
workflows/notifications.py's URL-generation bug was fixed (see git log:
"Fix email CTA button centering and broken approval links").

action_url is a snapshot stored once at notification-creation time, not
recomputed on read - the code fix only affects notifications created after
it landed. Existing rows still carry the raw workflow entity_type as the
route segment (e.g. "/transportrequest/78", "/travelrequest_domestic/182")
instead of the actual Angular route ("/transport/78", "/trf/182"), so their
"View" link 404s into the wildcard route and lands on the dashboard instead
of the request - exactly the reported symptom, just for historical rows.
"""

import re

from django.conf import settings
from django.db import migrations

ENTITY_TYPE_ROUTE_SEGMENT = {
    "travelrequest": "trf",
    "transportrequest": "transport",
    "visaapplication": "visa",
    "accommodationrequest": "accommodation",
}

STALE_URL_PATTERN = re.compile(r"^/([a-zA-Z_]+)/(\d+)$")


def fix_stale_action_urls(apps, schema_editor):
    UserNotification = apps.get_model("notifications", "UserNotification")
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:4200").rstrip(
        "/"
    )

    candidates = UserNotification.objects.exclude(action_url__isnull=True).exclude(
        action_url=""
    )

    fixed = 0
    for notification in candidates.iterator():
        url = notification.action_url
        relative = url[len(frontend_url) :] if url.startswith(frontend_url) else url

        match = STALE_URL_PATTERN.match(relative)
        if not match:
            continue

        entity_type, object_id = match.groups()
        base_type = entity_type.split("_", 1)[0]
        route_segment = ENTITY_TYPE_ROUTE_SEGMENT.get(base_type)
        if not route_segment:
            # Not one of the raw entity_type strings the bug produced -
            # already correct (or an unrecognized format), leave it alone.
            continue

        notification.action_url = f"{frontend_url}/{route_segment}/{object_id}"
        notification.save(update_fields=["action_url"])
        fixed += 1

    if fixed:
        print(f"Repaired {fixed} stale UserNotification.action_url value(s).")


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0008_remove_approval_reminder_template"),
    ]

    operations = [
        migrations.RunPython(fix_stale_action_urls, migrations.RunPython.noop),
    ]
