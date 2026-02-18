# Migration to standardize create permission names
# Removes '_requests' suffix from create permissions to match the pattern of 'create_trf'
#
# Before: create_trf, create_transport_requests, create_visa_requests, create_accommodation_requests
# After:  create_trf, create_transport, create_visa, create_accommodation

from django.db import migrations


def standardize_permission_names(apps, schema_editor):
    """
    Rename create permissions to use consistent naming without '_requests' suffix.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        print("\n" + "=" * 70)
        print("STANDARDIZING CREATE PERMISSION NAMES")
        print("=" * 70)

        # Mapping of old names to new names
        renames = [
            ('create_transport_requests', 'create_transport'),
            ('create_visa_requests', 'create_visa'),
            ('create_accommodation_requests', 'create_accommodation'),
        ]

        print("\nRenaming permissions...")
        for old_name, new_name in renames:
            update_sql = """
                UPDATE accounts_permission
                SET name = %s, updated_at = NOW()
                WHERE name = %s;
            """
            cursor.execute(update_sql, [new_name, old_name])
            if cursor.rowcount > 0:
                print(f"   {old_name} -> {new_name}")
            else:
                print(f"   {old_name} (not found, skipping)")

        print("\n" + "=" * 70)
        print("STANDARDIZATION COMPLETED")
        print("=" * 70)
        print("\nNew consistent naming pattern:")
        print("  - create_trf")
        print("  - create_transport")
        print("  - create_visa")
        print("  - create_accommodation")
        print("=" * 70 + "\n")


def reverse_standardize(apps, schema_editor):
    """
    Reverse the renaming if migration is rolled back.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        print("\nReversing permission name standardization...")

        renames = [
            ('create_transport', 'create_transport_requests'),
            ('create_visa', 'create_visa_requests'),
            ('create_accommodation', 'create_accommodation_requests'),
        ]

        for old_name, new_name in renames:
            update_sql = """
                UPDATE accounts_permission
                SET name = %s, updated_at = NOW()
                WHERE name = %s;
            """
            cursor.execute(update_sql, [new_name, old_name])

        print("Reversed permission name standardization")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_remove_legacy_approval_permissions'),
    ]

    operations = [
        migrations.RunPython(standardize_permission_names, reverse_standardize),
    ]
