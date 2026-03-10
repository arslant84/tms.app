# Migration to assign minimal permissions to "Registered User" role
# These are existing permissions that provide basic functionality for self-registered users

from django.db import migrations


def assign_permissions_to_registered_user(apps, schema_editor):
    """
    Assign minimal permissions to the "Registered User" role.

    This role is for self-registered users who need admin approval
    before being assigned a full role (like Requestor).

    Permissions assigned:
    - manage_own_profile: Can view/edit their own profile
    - view_own_requests: Can view their own submitted requests
    - view_dashboard_summary: Can see basic dashboard
    - upload_documents: Can upload profile photo and documents

    Note: Password change is hardcoded (no permission needed) as it's
    a basic security function all authenticated users must have.
    """
    Role = apps.get_model('accounts', 'Role')
    Permission = apps.get_model('accounts', 'Permission')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    # Get the Registered User role
    try:
        registered_user_role = Role.objects.get(name='Registered User')
    except Role.DoesNotExist:
        print("WARNING: 'Registered User' role not found. Skipping permission assignment.")
        return

    # Permissions to assign (these already exist in the system)
    permissions_to_assign = [
        'manage_own_profile',      # Can edit and update own user profile
        'view_own_requests',       # Can view only their own submitted requests
        'view_dashboard_summary',  # Can access dashboard summary statistics
        'upload_documents',        # Can upload supporting documents and files
    ]

    assigned_count = 0
    for perm_name in permissions_to_assign:
        try:
            permission = Permission.objects.get(name=perm_name)
            # Create the role-permission mapping if it doesn't exist
            _, created = RolePermission.objects.get_or_create(
                role=registered_user_role,
                permission=permission
            )
            if created:
                assigned_count += 1
                print(f"  + Assigned '{perm_name}' to Registered User role")
            else:
                print(f"  ~ '{perm_name}' already assigned to Registered User role")
        except Permission.DoesNotExist:
            print(f"  ! WARNING: Permission '{perm_name}' not found in database")

    print(f"\nAssigned {assigned_count} new permissions to 'Registered User' role")


def remove_permissions_from_registered_user(apps, schema_editor):
    """
    Reverse migration - remove the assigned permissions from Registered User role.
    """
    Role = apps.get_model('accounts', 'Role')
    Permission = apps.get_model('accounts', 'Permission')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    try:
        registered_user_role = Role.objects.get(name='Registered User')
    except Role.DoesNotExist:
        return

    permissions_to_remove = [
        'manage_own_profile',
        'view_own_requests',
        'view_dashboard_summary',
        'upload_documents',
    ]

    for perm_name in permissions_to_remove:
        try:
            permission = Permission.objects.get(name=perm_name)
            RolePermission.objects.filter(
                role=registered_user_role,
                permission=permission
            ).delete()
        except Permission.DoesNotExist:
            pass

    print("Removed permissions from 'Registered User' role")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0026_create_registered_user_role'),
    ]

    operations = [
        migrations.RunPython(
            assign_permissions_to_registered_user,
            remove_permissions_from_registered_user
        ),
    ]
