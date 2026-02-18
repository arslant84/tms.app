# Migration to remove approval permissions from module admin roles
# Admin roles should only process requests, not approve them
# Approval is handled by workflow roles (Line Manager, HOD, etc.)

from django.db import migrations


def remove_approval_permissions_from_admins(apps, schema_editor):
    """
    Remove approval permissions from admin roles.
    Admins process already-approved requests, they don't approve.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        print("\n" + "=" * 70)
        print("REMOVING APPROVAL PERMISSIONS FROM ADMIN ROLES")
        print("=" * 70)

        # Admin role IDs
        ADMIN_ROLES = {
            'accommodation_admin': 'c00facac-3e85-434c-956b-44885e71b1e2',
            'transport_admin': '1680236d-074e-4fe0-ad1c-19bb5581938b',
            'visa_clerk': '5f5c6f19-583c-45a9-8008-4a0a69a4f54b',
            'ticketing_admin': '3b11263f-bd35-4209-a049-80b00fedfd8b',
            'ticketing_clerk': '6c175d9c-fed9-4104-8492-352fc60a0efa',
        }

        # Approval permission IDs to remove
        APPROVAL_PERMS = {
            'approve_accommodation': 'a1111111-1111-1111-1111-111111111111',
            'approve_transport': 'a2222222-2222-2222-2222-222222222222',
            'approve_visa': 'a3333333-3333-3333-3333-333333333333',
            'approve_trf': 'a4444444-4444-4444-4444-444444444444',
            'view_pending_approvals': '097e9b18-9c83-4e86-860c-6f0f82140153',
        }

        # Remove approval permissions from each admin role
        role_permission_pairs_to_remove = [
            # Accommodation Admin
            (ADMIN_ROLES['accommodation_admin'], APPROVAL_PERMS['approve_accommodation']),
            (ADMIN_ROLES['accommodation_admin'], APPROVAL_PERMS['view_pending_approvals']),

            # Transport Admin
            (ADMIN_ROLES['transport_admin'], APPROVAL_PERMS['approve_transport']),
            (ADMIN_ROLES['transport_admin'], APPROVAL_PERMS['view_pending_approvals']),

            # Visa Clerk
            (ADMIN_ROLES['visa_clerk'], APPROVAL_PERMS['approve_visa']),
            (ADMIN_ROLES['visa_clerk'], APPROVAL_PERMS['view_pending_approvals']),

            # Ticketing Admin
            (ADMIN_ROLES['ticketing_admin'], APPROVAL_PERMS['approve_trf']),
            (ADMIN_ROLES['ticketing_admin'], APPROVAL_PERMS['view_pending_approvals']),

            # Ticketing Clerk
            (ADMIN_ROLES['ticketing_clerk'], APPROVAL_PERMS['approve_trf']),
            (ADMIN_ROLES['ticketing_clerk'], APPROVAL_PERMS['view_pending_approvals']),
        ]

        print(f"\nRemoving {len(role_permission_pairs_to_remove)} role-permission mappings...")

        for role_id, perm_id in role_permission_pairs_to_remove:
            delete_sql = """
                DELETE FROM accounts_rolepermission
                WHERE role_id = %s AND permission_id = %s;
            """
            cursor.execute(delete_sql, [role_id, perm_id])

        print("\n" + "=" * 70)
        print("APPROVAL PERMISSIONS REMOVED FROM ADMIN ROLES")
        print("=" * 70)
        print("\nAdmin roles now only process requests, not approve:")
        print("  - Accommodation Admin: Can manage bookings only")
        print("  - Transport Admin: Can manage transport only")
        print("  - Visa Clerk: Can process visa applications only")
        print("  - Ticketing Admin: Can manage flights only")
        print("  - Ticketing Clerk: Can manage flights only")
        print("\nApproval remains with:")
        print("  - Line Manager, HOD, Department Focal, Focal")
        print("=" * 70 + "\n")


def reverse_migration(apps, schema_editor):
    """
    Note: This doesn't restore permissions, use Role Management UI to re-add if needed.
    """
    print("Note: Run migration 0021 again to restore approval permissions to admin roles")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_add_missing_approver_permissions'),
    ]

    operations = [
        migrations.RunPython(remove_approval_permissions_from_admins, reverse_migration),
    ]
