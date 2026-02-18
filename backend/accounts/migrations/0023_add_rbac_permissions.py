# Migration to add missing RBAC permissions for role-based access control
# This ensures all permissions referenced in accounts/utils.py exist

from django.db import migrations
import uuid


def add_rbac_permissions(apps, schema_editor):
    """
    Add permissions required for the new RBAC system.
    These replace hardcoded is_staff checks throughout the codebase.
    """
    Permission = apps.get_model('accounts', 'Permission')

    # Permissions to ensure exist (name: description)
    REQUIRED_PERMISSIONS = {
        # View all (for admin dashboards)
        'view_all_trf': 'View all Travel Service Requests',
        'view_all_accommodation': 'View all Accommodation Requests',
        'view_all_transport': 'View all Transport Requests',
        'view_all_visa': 'View all Visa Applications',
        'view_all_bookings': 'View all Flight and Hotel Bookings',

        # Process/Manage (for admin actions)
        'process_trf': 'Process Travel Service Requests',
        'manage_trf': 'Manage Travel Service Requests',
        'process_accommodation': 'Process Accommodation Requests',
        'manage_accommodation': 'Manage Accommodation Requests',
        'process_transport': 'Process Transport Requests',
        'manage_transport': 'Manage Transport Requests',
        'process_visa': 'Process Visa Applications',
        'manage_visa': 'Manage Visa Applications',
        'process_bookings': 'Process Flight and Hotel Bookings',
        'manage_bookings': 'Manage Flight and Hotel Bookings',

        # Approval permissions
        'approve_trf': 'Approve Travel Service Requests',
        'approve_accommodation': 'Approve Accommodation Requests',
        'approve_transport': 'Approve Transport Requests',
        'approve_visa': 'Approve Visa Applications',
        'view_pending_approvals': 'View Pending Approvals Queue',
        'manage_approvals': 'Manage Approval Workflows',

        # Admin management
        'manage_users': 'Manage Users',
        'manage_roles': 'Manage Roles',
        'manage_departments': 'Manage Departments',
        'manage_workflows': 'Manage Workflow Templates',
        'manage_notifications': 'Manage Notifications',
        'send_notifications': 'Send Notifications',

        # System settings
        'view_system_settings': 'View System Settings',
        'manage_application_settings': 'Manage Application Settings',
    }

    created_count = 0
    existing_count = 0

    for name, description in REQUIRED_PERMISSIONS.items():
        permission, created = Permission.objects.get_or_create(
            name=name,
            defaults={
                'description': description,
            }
        )
        if created:
            created_count += 1
            print(f"  Created permission: {name}")
        else:
            existing_count += 1

    print(f"\nPermissions: {created_count} created, {existing_count} already existed")


def reverse_migration(apps, schema_editor):
    """
    Don't delete permissions in reverse - they may be in use
    """
    print("Note: Permissions are not removed in reverse migration")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_remove_approval_permissions_from_admins'),
    ]

    operations = [
        migrations.RunPython(add_rbac_permissions, reverse_migration),
    ]
