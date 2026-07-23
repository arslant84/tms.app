"""
Resolve the ~14 "paper" permissions found during the 2026-07-23 permission
audit (see docs/APP_WIDE_GAPS_FIX_ROADMAP.md Fix 9): permissions that exist
in the DB, are assigned to roles, but have zero enforcement anywhere in the
backend.

This migration handles the three categories that need a data fix:

1. Five of them (manage_flights, process_flights, process_visa_applications,
   manage_transport_requests, manage_accommodation_bookings) turned out to
   be exact or near-exact duplicates of permissions that are already
   enforced via accounts.utils.can_manage() under different names
   (manage_bookings/process_bookings, process_visa, manage_transport,
   manage_accommodation). manage_flights/process_flights additionally
   granted Ticketing Clerk, which the enforced manage_bookings/
   process_bookings did not - that's a real gap, not paper. Fix: fold
   Ticketing Clerk into manage_bookings/process_bookings, then delete all
   5 duplicate permission rows (RolePermission rows cascade).

2. create_combined was inverted: only 'Registered User' had it, while the
   10 real roles that have create_trf/create_visa/create_transport/
   create_accommodation did not. Fix: reassign to match the create_trf
   role set exactly, matching the pattern already used for the
   combined_request permissions in migration 0037.

3. access_debug_endpoints and manage_document_templates correspond to no
   endpoint or feature anywhere in the codebase (confirmed: Django Debug
   Toolbar is dev-only middleware with no API surface; the only template
   management endpoint, NotificationTemplateViewSet, is already gated by
   manage_notifications/view_system_settings, not manage_document_templates).
   Fix: delete both as dead permissions.

The remaining paper permissions (create_trf, create_visa, create_transport,
create_accommodation, manage_own_profile, export_data) needed no data fix -
just enforcement wiring in application code, done alongside this migration.
"""

from django.db import migrations

DUPLICATE_PERMISSIONS_TO_DELETE = [
    "manage_flights",
    "process_flights",
    "process_visa_applications",
    "manage_transport_requests",
    "manage_accommodation_bookings",
]

CREATE_COMBINED_ROLES = [
    "Accommodation Admin",
    "Department Focal",
    "Employee",
    "HOD",
    "Line Manager",
    "System Administrator",
    "Ticketing Admin",
    "Ticketing Clerk",
    "Transport Admin",
    "Visa Clerk",
]

DEAD_PERMISSIONS_TO_DELETE = [
    "access_debug_endpoints",
    "manage_document_templates",
]


def consolidate_booking_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    try:
        ticketing_clerk = Role.objects.get(name="Ticketing Clerk")
    except Role.DoesNotExist:
        ticketing_clerk = None

    if ticketing_clerk:
        for perm_name in ("manage_bookings", "process_bookings"):
            try:
                permission = Permission.objects.get(name=perm_name)
            except Permission.DoesNotExist:
                continue
            RolePermission.objects.get_or_create(
                role=ticketing_clerk, permission=permission
            )

    Permission.objects.filter(name__in=DUPLICATE_PERMISSIONS_TO_DELETE).delete()


def fix_create_combined_assignment(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    try:
        create_combined = Permission.objects.get(name="create_combined")
    except Permission.DoesNotExist:
        return

    RolePermission.objects.filter(permission=create_combined).exclude(
        role__name__in=CREATE_COMBINED_ROLES
    ).delete()

    for role_name in CREATE_COMBINED_ROLES:
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            continue
        RolePermission.objects.get_or_create(role=role, permission=create_combined)


def delete_dead_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(name__in=DEAD_PERMISSIONS_TO_DELETE).delete()


def reverse_noop(apps, schema_editor):
    """Not reversed - these were duplicate/dead/misassigned permission rows,
    not something to restore."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0037_assign_combined_request_permissions_and_remove_test_role"),
    ]

    operations = [
        migrations.RunPython(consolidate_booking_permissions, reverse_noop),
        migrations.RunPython(fix_create_combined_assignment, reverse_noop),
        migrations.RunPython(delete_dead_permissions, reverse_noop),
    ]
