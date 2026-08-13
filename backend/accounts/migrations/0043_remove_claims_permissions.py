# Migration to remove the Expense Claims permissions.
# These were seeded ahead of an "Expense Claims" module (0008/0012) that was
# never actually built - no backend app, no frontend feature, only an
# always-zero "pending_expense_claims" dashboard placeholder. Removing the
# dead permissions so they stop showing up in the admin permission list.

from django.db import migrations

CLAIMS_PERMISSIONS = [
    "approve_claims",
    "create_claims",
    "process_claims",
    "view_admin_claims",
    "view_all_claims",
]


def remove_claims_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    permissions = Permission.objects.filter(name__in=CLAIMS_PERMISSIONS)
    RolePermission.objects.filter(permission__in=permissions).delete()
    permissions.delete()


def restore_claims_permissions(apps, schema_editor):
    """Best-effort reverse: recreate the permissions (role links are not
    restored - they weren't recorded before deletion)."""
    Permission = apps.get_model("accounts", "Permission")

    descriptions = {
        "approve_claims": "Can approve claim requests via workflow",
        "create_claims": "Can create new Expense Claims.",
        "process_claims": "Can process claims for payment (Finance Clerk).",
        "view_admin_claims": "Can access the Claims Admin module interface",
        "view_all_claims": "Can view all Claims across departments.",
    }
    for name, description in descriptions.items():
        Permission.objects.get_or_create(
            name=name, defaults={"description": description}
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0042_bulk_import_job"),
    ]

    operations = [
        migrations.RunPython(remove_claims_permissions, restore_claims_permissions),
    ]
