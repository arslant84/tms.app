# Generated migration for creating default "Registered User" role

from django.db import migrations


def create_registered_user_role(apps, schema_editor):
    """
    Create default role for self-registered users.
    This role has minimal permissions until admin assigns proper role.
    """
    Role = apps.get_model('accounts', 'Role')
    Permission = apps.get_model('accounts', 'Permission')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    # Create role
    role, created = Role.objects.get_or_create(
        name='Registered User',
        defaults={
            'description': 'Default role for self-registered users pending admin approval. Limited permissions.'
        }
    )

    if created:
        # Assign minimal permissions (these should already exist)
        # Users can only view/edit their own profile until admin assigns proper role
        minimal_permissions = [
            'view_own_profile',
            'change_own_password',
            'update_own_profile',
        ]

        for perm_name in minimal_permissions:
            try:
                permission = Permission.objects.get(name=perm_name)
                RolePermission.objects.get_or_create(
                    role=role,
                    permission=permission
                )
            except Permission.DoesNotExist:
                # Permission doesn't exist yet, skip
                pass


def remove_registered_user_role(apps, schema_editor):
    """Reverse migration - remove the Registered User role"""
    Role = apps.get_model('accounts', 'Role')
    Role.objects.filter(name='Registered User').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0025_add_approval_permissions_to_approver_roles'),
    ]

    operations = [
        migrations.RunPython(
            create_registered_user_role,
            remove_registered_user_role
        ),
    ]
