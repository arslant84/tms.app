# Migration to add Combined Request permissions
# This adds all permissions needed for the Combined Request module

from django.db import migrations


def add_combined_request_permissions(apps, schema_editor):
    """
    Add permissions required for the Combined Request module.
    """
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    # Combined Request Permissions
    COMBINED_PERMISSIONS = {
        # Module Access (Admin)
        'view_admin_combined': 'Access Combined Request admin panel',
        'manage_combined_requests': 'Manage all Combined Requests',
        'process_combined_requests': 'Process approved Combined Requests',

        # Request Creation
        'create_combined': 'Create Combined Requests',

        # Approval
        'approve_combined': 'Approve Combined Requests',

        # View
        'view_all_combined': 'View all Combined Requests',
    }

    created_permissions = []
    for name, description in COMBINED_PERMISSIONS.items():
        permission, created = Permission.objects.get_or_create(
            name=name,
            defaults={'description': description}
        )
        if created:
            print(f"  Created permission: {name}")
            created_permissions.append(permission)
        else:
            print(f"  Permission already exists: {name}")

    # Assign create_combined to Registered User role (basic users)
    try:
        registered_user_role = Role.objects.get(name='Registered User')
        create_combined_perm = Permission.objects.get(name='create_combined')
        RolePermission.objects.get_or_create(
            role=registered_user_role,
            permission=create_combined_perm
        )
        print("  Assigned create_combined to Registered User role")
    except Role.DoesNotExist:
        print("  Note: Registered User role not found, skipping permission assignment")
    except Permission.DoesNotExist:
        pass

    # Assign admin permissions to Admin role
    try:
        admin_role = Role.objects.get(name='Admin')
        admin_permissions = [
            'view_admin_combined',
            'manage_combined_requests',
            'process_combined_requests',
            'view_all_combined',
        ]
        for perm_name in admin_permissions:
            try:
                perm = Permission.objects.get(name=perm_name)
                RolePermission.objects.get_or_create(
                    role=admin_role,
                    permission=perm
                )
            except Permission.DoesNotExist:
                pass
        print("  Assigned admin permissions to Admin role")
    except Role.DoesNotExist:
        print("  Note: Admin role not found, skipping permission assignment")

    # Assign approve_combined to Approver roles
    approver_role_names = ['Approver', 'HOD Approver', 'Line Manager Approver', 'Finance Approver']
    try:
        approve_perm = Permission.objects.get(name='approve_combined')
        for role_name in approver_role_names:
            try:
                role = Role.objects.get(name=role_name)
                RolePermission.objects.get_or_create(
                    role=role,
                    permission=approve_perm
                )
                print(f"  Assigned approve_combined to {role_name} role")
            except Role.DoesNotExist:
                pass
    except Permission.DoesNotExist:
        pass

    print(f"\nCombined Request permissions migration complete")


def reverse_migration(apps, schema_editor):
    """
    Don't delete permissions in reverse - they may be in use
    """
    print("Note: Permissions are not removed in reverse migration")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0028_add_view_all_trf_to_ticketing_admin'),
    ]

    operations = [
        migrations.RunPython(add_combined_request_permissions, reverse_migration),
    ]
