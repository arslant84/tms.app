# Generated migration to add view_all_trf permission to Ticketing Admin role

from django.db import migrations


def add_view_all_trf_to_ticketing_admin(apps, schema_editor):
    """Add view_all_trf permission to Ticketing Admin role"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Add view_all_trf permission to Ticketing Admin role
        sql = """
            INSERT INTO accounts_rolepermission (role_id, permission_id, created_at)
            VALUES ('3b11263f-bd35-4209-a049-80b00fedfd8b', '2386d8ac-f7ac-42dc-952a-21939e5dd890', NOW())
            ON CONFLICT (role_id, permission_id) DO NOTHING;
        """
        cursor.execute(sql)
        print("Added view_all_trf permission to Ticketing Admin role")


def remove_view_all_trf_from_ticketing_admin(apps, schema_editor):
    """Remove view_all_trf permission from Ticketing Admin role"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        sql = """
            DELETE FROM accounts_rolepermission
            WHERE role_id = '3b11263f-bd35-4209-a049-80b00fedfd8b'
            AND permission_id = '2386d8ac-f7ac-42dc-952a-21939e5dd890';
        """
        cursor.execute(sql)
        print("Removed view_all_trf permission from Ticketing Admin role")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0027_assign_permissions_to_registered_user'),
    ]

    operations = [
        migrations.RunPython(add_view_all_trf_to_ticketing_admin, remove_view_all_trf_from_ticketing_admin),
    ]
