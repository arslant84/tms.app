# Migration to remove redundant legacy approval permissions
# These permissions duplicate the newer generic approval permissions:
# - approve_accommodation_requests -> approve_accommodation (used in views)
# - approve_transport_requests -> approve_transport (used in workflows)
# - approve_visa_requests -> approve_visa (used in views)

from django.db import migrations


def remove_legacy_permissions(apps, schema_editor):
    """
    Remove legacy approval permissions that are duplicates of the newer generic ones.
    The generic permissions (approve_accommodation, approve_transport, approve_visa)
    are actively used in the codebase, while the *_requests variants are unused.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        print("\n" + "=" * 70)
        print("REMOVING LEGACY APPROVAL PERMISSIONS")
        print("=" * 70)

        # Legacy permission names to remove
        legacy_permissions = [
            'approve_accommodation_requests',
            'approve_transport_requests',
            'approve_visa_requests',
        ]

        # First, remove any role-permission mappings for these permissions
        print("\n[1/2] Removing role-permission mappings...")
        placeholders = ','.join(['%s'] * len(legacy_permissions))

        delete_mappings_sql = f"""
            DELETE FROM accounts_rolepermission
            WHERE permission_id IN (
                SELECT id FROM accounts_permission WHERE name IN ({placeholders})
            );
        """
        cursor.execute(delete_mappings_sql, legacy_permissions)
        deleted_mappings = cursor.rowcount
        print(f"   Removed {deleted_mappings} role-permission mappings")

        # Then, delete the permissions themselves
        print("\n[2/2] Deleting legacy permissions...")
        delete_permissions_sql = f"""
            DELETE FROM accounts_permission
            WHERE name IN ({placeholders});
        """
        cursor.execute(delete_permissions_sql, legacy_permissions)
        deleted_perms = cursor.rowcount
        print(f"   Deleted {deleted_perms} permissions")

        print("\n" + "=" * 70)
        print("CLEANUP COMPLETED")
        print("=" * 70)
        print("\nRemoved legacy permissions:")
        for perm in legacy_permissions:
            print(f"  - {perm}")
        print("\nThese are replaced by:")
        print("  - approve_accommodation")
        print("  - approve_transport")
        print("  - approve_visa")
        print("=" * 70 + "\n")


def restore_legacy_permissions(apps, schema_editor):
    """
    Restore the legacy permissions if migration is reversed.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        print("\nRestoring legacy approval permissions...")

        restore_sql = """
            INSERT INTO accounts_permission (id, name, description, created_at, updated_at) VALUES
            ('19617c29-4c76-44d0-957d-2f2b82bb7518', 'approve_accommodation_requests', 'Can approve accommodation booking requests', NOW(), NOW()),
            ('e9e2f485-436d-4ef3-b999-73a4a5842b04', 'approve_transport_requests', 'Can approve transport booking requests.', NOW(), NOW()),
            ('e0bf0f10-aca5-4de4-836a-de5054f22fa3', 'approve_visa_requests', 'Can approve visa application requests', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING;
        """
        cursor.execute(restore_sql)
        print("Restored legacy permissions")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_add_department_model'),
    ]

    operations = [
        migrations.RunPython(remove_legacy_permissions, restore_legacy_permissions),
    ]
