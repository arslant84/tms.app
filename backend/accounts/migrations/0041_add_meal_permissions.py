# Migration to add Meal Admin permissions and role
# Meal provisions are captured on TSRs (Domestic/External Parties) but had no
# dedicated admin queue to arrange them. See docs/MEAL_ADMIN_MODULE_ROADMAP.md.

from django.db import migrations


def add_meal_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    MEAL_PERMISSIONS = {
        "view_admin_meal": "Access Meal Admin panel",
        "process_meal": "Process (arrange/complete) requested meals",
        "manage_meal": "Manage requested meals",
        "view_all_meal": "View all TSR meal provisions",
    }

    permissions_by_name = {}
    for name, description in MEAL_PERMISSIONS.items():
        permission, _ = Permission.objects.get_or_create(
            name=name, defaults={"description": description}
        )
        permissions_by_name[name] = permission

    role, _ = Role.objects.get_or_create(
        name="Meal Admin",
        defaults={
            "description": "Arranges meals requested on Travel Service Requests."
        },
    )

    for permission in permissions_by_name.values():
        RolePermission.objects.get_or_create(role=role, permission=permission)


def reverse_migration(apps, schema_editor):
    """Don't delete permissions/role in reverse - they may be in use"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0040_alter_adminactionlog_action_type"),
    ]

    operations = [
        migrations.RunPython(add_meal_permissions, reverse_migration),
    ]
