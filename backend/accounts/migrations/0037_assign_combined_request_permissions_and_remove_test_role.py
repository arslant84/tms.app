"""
Assign the 5 orphaned combined_request permissions to roles, matching the
exact pattern already used for trf/visa/transport/accommodation, and remove
the empty 'Test' role.

Found during the 2026-07-23 permission audit (see
docs/APP_WIDE_GAPS_FIX_ROADMAP.md Fix 6): approve_combined,
manage_combined_requests, process_combined_requests, view_admin_combined,
and view_all_combined all had 0 roles assigned, despite the identical
approve_trf/approve_visa/approve_transport/approve_accommodation permissions
all being assigned to the same 4 roles (Department Focal, Line Manager, HOD,
System Administrator). The other 4 combined_request permissions have no
single natural "combined admin" role the way each other module does
(Ticketing Admin, Transport Admin, Accommodation Admin, Visa Clerk), and
process_combined_requests is specifically documented in
combined_request/views.py as the full-override permission, so all 4 go to
System Administrator only.

The 'Test' role had 0 users assigned (confirmed via direct query) and is
removed as leftover scratch data.
"""

from django.db import migrations

APPROVE_COMBINED_ROLES = [
    "Department Focal",
    "Line Manager",
    "HOD",
    "System Administrator",
]
ADMIN_ONLY_COMBINED_PERMS = [
    "manage_combined_requests",
    "process_combined_requests",
    "view_admin_combined",
    "view_all_combined",
]


def assign_combined_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    try:
        approve_combined = Permission.objects.get(name="approve_combined")
    except Permission.DoesNotExist:
        approve_combined = None

    if approve_combined:
        for role_name in APPROVE_COMBINED_ROLES:
            try:
                role = Role.objects.get(name=role_name)
            except Role.DoesNotExist:
                continue
            RolePermission.objects.get_or_create(role=role, permission=approve_combined)

    try:
        system_admin_role = Role.objects.get(name="System Administrator")
    except Role.DoesNotExist:
        system_admin_role = None

    if system_admin_role:
        for perm_name in ADMIN_ONLY_COMBINED_PERMS:
            try:
                permission = Permission.objects.get(name=perm_name)
            except Permission.DoesNotExist:
                continue
            RolePermission.objects.get_or_create(
                role=system_admin_role, permission=permission
            )


def remove_test_role(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    User = apps.get_model("accounts", "User")

    try:
        test_role = Role.objects.get(name="Test")
    except Role.DoesNotExist:
        return

    if User.objects.filter(role=test_role).exists():
        # Safety net: if a user somehow got assigned to this role between
        # the audit and this migration running, don't silently delete it.
        return

    test_role.delete()


def reverse_noop(apps, schema_editor):
    """Not reversed - these were missing role/permission assignments and a
    leftover empty role, not something to restore."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0036_alter_adminactionlog_action_type"),
    ]

    operations = [
        migrations.RunPython(assign_combined_permissions, reverse_noop),
        migrations.RunPython(remove_test_role, reverse_noop),
    ]
