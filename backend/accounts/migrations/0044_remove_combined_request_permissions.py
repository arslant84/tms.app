# Migration to remove the Combined Request permissions.
# The Combined Request module (unified TSR + Transport + Accommodation + Visa
# request, its own admin panel and workflow) has been fully deleted per user
# request - see docs/COMBINED_REQUEST_MODULE_REMOVAL_ROADMAP.md. Removing the
# now-dead permissions so they stop showing up in the admin permission list.

from django.db import migrations

COMBINED_REQUEST_PERMISSIONS = [
    "view_admin_combined",
    "manage_combined_requests",
    "process_combined_requests",
    "create_combined",
    "approve_combined",
    "view_all_combined",
]


def remove_combined_request_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    permissions = Permission.objects.filter(name__in=COMBINED_REQUEST_PERMISSIONS)
    RolePermission.objects.filter(permission__in=permissions).delete()
    permissions.delete()


def restore_combined_request_permissions(apps, schema_editor):
    """Best-effort reverse: recreate the permissions (role links are not
    restored - they weren't recorded before deletion)."""
    Permission = apps.get_model("accounts", "Permission")

    descriptions = {
        "view_admin_combined": "Can access combined requests admin panel",
        "manage_combined_requests": "Can manage all combined requests",
        "process_combined_requests": "Can process approved combined requests",
        "create_combined": "Can create combined requests",
        "approve_combined": "Can approve combined requests",
        "view_all_combined": "Can view all combined requests across departments",
    }
    for name, description in descriptions.items():
        Permission.objects.get_or_create(
            name=name, defaults={"description": description}
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0043_remove_claims_permissions"),
    ]

    operations = [
        migrations.RunPython(
            remove_combined_request_permissions, restore_combined_request_permissions
        ),
    ]
