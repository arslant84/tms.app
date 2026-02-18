# Migration to assign RBAC permissions to admin roles
# This ensures admin roles have the view_all_* and manage_* permissions they need

from django.db import migrations


def assign_rbac_permissions(apps, schema_editor):
    """
    Assign view_all_* and manage_* permissions to admin roles.
    This enables the RBAC system to work without is_staff checks.
    """
    Role = apps.get_model('accounts', 'Role')
    Permission = apps.get_model('accounts', 'Permission')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    print("\nAssigning RBAC permissions to admin roles...")

    # Define which permissions each admin role should have
    ROLE_PERMISSIONS = {
        'Ticketing Admin': [
            'view_all_trf',
            'view_all_bookings',
            'process_trf',
            'manage_trf',
            'process_bookings',
            'manage_bookings',
        ],
        'Accommodation Admin': [
            'view_all_accommodation',
            'process_accommodation',
            'manage_accommodation',
        ],
        'Transport Admin': [
            'view_all_transport',
            'process_transport',
            'manage_transport',
        ],
        'Visa Clerk': [
            'view_all_visa',
            'process_visa',
            'manage_visa',
        ],
        'System Administrator': [
            # All view_all permissions
            'view_all_trf',
            'view_all_accommodation',
            'view_all_transport',
            'view_all_visa',
            'view_all_bookings',
            # All manage permissions
            'process_trf',
            'manage_trf',
            'process_accommodation',
            'manage_accommodation',
            'process_transport',
            'manage_transport',
            'process_visa',
            'manage_visa',
            'process_bookings',
            'manage_bookings',
            # All admin permissions
            'manage_users',
            'manage_roles',
            'manage_departments',
            'manage_workflows',
            'manage_notifications',
            'send_notifications',
            'manage_approvals',
            'view_system_settings',
            'manage_application_settings',
        ],
        'HOD': [
            # HOD can view all but not necessarily manage
            'view_all_trf',
            'view_all_accommodation',
            'view_all_transport',
            'view_all_visa',
        ],
    }

    total_assigned = 0

    for role_name, permission_names in ROLE_PERMISSIONS.items():
        try:
            role = Role.objects.get(name=role_name)
            print(f"\n  Assigning permissions to {role_name}...")

            for perm_name in permission_names:
                try:
                    permission = Permission.objects.get(name=perm_name)
                    _, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission
                    )
                    if created:
                        total_assigned += 1
                        print(f"    + {perm_name}")
                except Permission.DoesNotExist:
                    print(f"    ! Permission not found: {perm_name}")

        except Role.DoesNotExist:
            print(f"\n  ! Role not found: {role_name}")

    print(f"\n  Total permissions assigned: {total_assigned}")


def reverse_migration(apps, schema_editor):
    """
    Don't remove permissions in reverse - use Role Management UI
    """
    print("Note: Permission assignments are not removed in reverse migration")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_add_rbac_permissions'),
    ]

    operations = [
        migrations.RunPython(assign_rbac_permissions, reverse_migration),
    ]
