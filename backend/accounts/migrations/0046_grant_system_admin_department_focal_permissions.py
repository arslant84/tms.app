# Migration for docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 9.
#
# CustomUser.is_admin used to bypass RBAC entirely in permission.guard.ts
# and accounts/settings_views.py - a second, non-RBAC authority channel.
# Per an explicit decision (2026-09-08), access should be governed solely
# by a role's actually-assigned permissions, the same as any other role,
# not by a hardcoded flag. Before removing the is_admin bypass, an audit
# found "System Administrator" (the role every current is_admin=True user
# already holds) was missing 2 of the 56 permissions that exist in the
# system - both added by migration 0045 to "Department Focal" only, never
# to "System Administrator". This migration grants them so no existing
# user loses access once the bypass is removed.

from django.db import migrations


def grant_missing_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    role = Role.objects.filter(name="System Administrator").first()
    if not role:
        return

    for permission_name in ("view_admin_department_focal", "view_department_requests"):
        permission = Permission.objects.filter(name=permission_name).first()
        if permission:
            RolePermission.objects.get_or_create(role=role, permission=permission)


def reverse_migration(apps, schema_editor):
    """Don't remove permissions in reverse - System Administrator having
    extra permissions is never harmful, and removing them could strand a
    real admin mid-session."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0045_add_department_focal_queue_permission"),
    ]

    operations = [
        migrations.RunPython(grant_missing_permissions, reverse_migration),
    ]
