# Generated manually on 2026-09-17

from django.db import migrations

# Each pair is assigned to the exact same roles everywhere (verified against
# prod data) and accounts.utils.can_manage() only ever checks them together
# via has_any_permission([process_X, manage_X]) - never individually, unlike
# every other module in that helper (manage_workflows, manage_users, etc.),
# which already use a single permission name. Same "paper permission"
# pattern as the 5 duplicates removed in 0038_consolidate_paper_permissions;
# these 6 pairs were missed in that pass. Keep manage_X (matches the
# can_manage() function name and the single-name convention used
# everywhere else in that helper); delete process_X - RolePermission rows
# cascade, so no role loses access.
REDUNDANT_PROCESS_PERMISSIONS = [
    "process_transport",
    "process_trf",
    "process_visa",
    "process_accommodation",
    "process_bookings",
    "process_meal",
]


def remove_redundant_process_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(name__in=REDUNDANT_PROCESS_PERMISSIONS).delete()


def noop_reverse(apps, schema_editor):
    """Irreversible: these rows were exact duplicates, not worth restoring."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0052_remove_orphaned_application_settings"),
    ]

    operations = [
        migrations.RunPython(remove_redundant_process_permissions, noop_reverse),
    ]
