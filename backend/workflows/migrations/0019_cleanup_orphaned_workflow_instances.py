"""
One-time cleanup of WorkflowInstance/UserNotification rows left orphaned by
entity deletions that predate the cascade-cleanup signals added alongside
this migration (see workflows/signals.py). Deleting a TravelRequest,
TransportRequest, VisaApplication, or AccommodationRequest never cleaned up
its WorkflowInstance (linked via GenericForeignKey, which Django can't
cascade automatically), leaving step executions/delegations/audit logs
behind too, plus UserNotification rows whose action_url pointed at a
now-deleted entity. Found via audit: 153 orphaned WorkflowInstance rows
across transportrequest/travelrequest/visaapplication content types.
"""

from django.db import migrations

MODEL_LOOKUP = {
    "travelrequest": ("trf", "TravelRequest"),
    "transportrequest": ("transport", "TransportRequest"),
    "visaapplication": ("visa", "VisaApplication"),
    "accommodationrequest": ("accommodation", "AccommodationRequest"),
}


def cleanup_orphans(apps, schema_editor):
    WorkflowInstance = apps.get_model("workflows", "WorkflowInstance")
    UserNotification = apps.get_model("notifications", "UserNotification")
    ContentType = apps.get_model("contenttypes", "ContentType")

    deleted_instances = 0
    deleted_notifications = 0

    for model_name, (app_label, real_model_name) in MODEL_LOOKUP.items():
        try:
            content_type = ContentType.objects.get(
                app_label=app_label, model=model_name
            )
        except ContentType.DoesNotExist:
            continue

        RealModel = apps.get_model(app_label, real_model_name)
        existing_ids = set(RealModel.objects.values_list("pk", flat=True))

        orphaned_instances = WorkflowInstance.objects.filter(
            content_type=content_type
        ).exclude(object_id__in=existing_ids)
        count, _ = orphaned_instances.delete()
        deleted_instances += count

        orphaned_notifications = UserNotification.objects.filter(
            content_type=content_type
        ).exclude(object_id__in=existing_ids)
        count, _ = orphaned_notifications.delete()
        deleted_notifications += count

    if deleted_instances or deleted_notifications:
        print(
            f"Cleaned up {deleted_instances} orphaned WorkflowInstance(s) and "
            f"{deleted_notifications} orphaned UserNotification(s)"
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    # These four cross-app deps used to be ("<app>", "__latest__") - resolved
    # fresh against whatever each app's newest migration is *at graph-build
    # time*, not frozen to what "latest" meant when this migration was
    # written. That caused a production deploy to fail outright: a later,
    # unrelated trf migration (0015, a harmless help_text change) got pulled
    # in as this migration's dependency and had never been applied, so
    # Django refused to run `migrate` for any app with InconsistentMigrationHistory.
    # Pinned to the migrations that were actually current for each app when
    # this one was authored (2026-08-23) / applied in production (2026-08-24).
    dependencies = [
        ("workflows", "0018_remove_sla_tracking"),
        ("notifications", "0009_fix_stale_action_urls"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("trf", "0014_travelrequest_department_focal_notified"),
        ("transport", "0008_delete_transportsegment"),
        ("visa", "0004_add_passport_file_to_visa"),
        ("accommodation", "0009_remove_accommodationrequest_created_by"),
    ]

    operations = [
        migrations.RunPython(cleanup_orphans, noop_reverse),
    ]
