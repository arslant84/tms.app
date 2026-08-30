# Migration to add the Department Focal arrangements-queue permission.
# Department Focal already existed as an approval-step role, but had no way
# to see when their department's travel arrangements (flight/meal/transport/
# accommodation) were fully completed after approval.

from django.db import migrations


def add_department_focal_permission(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    permission, _ = Permission.objects.get_or_create(
        name="view_admin_department_focal",
        defaults={
            "description": (
                "View the Department Focal queue of fully-arranged travel "
                "requests for their department"
            )
        },
    )

    role = Role.objects.filter(name="Department Focal").first()
    if role:
        RolePermission.objects.get_or_create(role=role, permission=permission)


def reverse_migration(apps, schema_editor):
    """Don't delete permissions/role in reverse - they may be in use"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0044_remove_combined_request_permissions"),
    ]

    operations = [
        migrations.RunPython(add_department_focal_permission, reverse_migration),
    ]
