# Migration to refactor permissions: remove role-specific names, add generic module-based permissions

from django.db import migrations
import uuid


def refactor_permissions(apps, schema_editor):
    """
    Refactor permission structure:
    1. Remove role-specific approval permissions (approve_*_focal, approve_*_hod, approve_*_manager)
    2. Add generic module-based approval permissions
    3. Update role-permission mappings
    """
    from django.db import connection

    with connection.cursor() as cursor:
        print("\n" + "="*80)
        print("PERMISSION REFACTORING MIGRATION")
        print("="*80)

        # ============================================================================
        # STEP 1: Add new generic permissions
        # ============================================================================
        print("\n[1/4] Adding new generic permissions...")

        new_permissions_sql = """
            INSERT INTO accounts_permission (id, name, description, created_at, updated_at) VALUES
            ('a1111111-1111-1111-1111-111111111111', 'approve_accommodation', 'Can approve accommodation requests via workflow', NOW(), NOW()),
            ('a2222222-2222-2222-2222-222222222222', 'approve_transport', 'Can approve transport requests via workflow', NOW(), NOW()),
            ('a3333333-3333-3333-3333-333333333333', 'approve_visa', 'Can approve visa requests via workflow', NOW(), NOW()),
            ('a4444444-4444-4444-4444-444444444444', 'approve_trf', 'Can approve TRF requests via workflow', NOW(), NOW()),
            ('a5555555-5555-5555-5555-555555555555', 'approve_claims', 'Can approve claim requests via workflow', NOW(), NOW()),
            ('a6666666-6666-6666-6666-666666666666', 'create_accommodation_requests', 'Can create accommodation booking requests', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING;
        """
        cursor.execute(new_permissions_sql)
        print("   ✓ Added 6 new generic permissions")

        # ============================================================================
        # STEP 2: Update role-permission mappings to use new permissions
        # ============================================================================
        print("\n[2/4] Updating role-permission mappings...")

        # Map old permissions to new permissions for each role
        role_permission_updates = [
            # System Administrator - add all new approval permissions
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'a1111111-1111-1111-1111-111111111111'),  # approve_accommodation
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'a2222222-2222-2222-2222-222222222222'),  # approve_transport
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'a3333333-3333-3333-3333-333333333333'),  # approve_visa
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'a4444444-4444-4444-4444-444444444444'),  # approve_trf
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'a5555555-5555-5555-5555-555555555555'),  # approve_claims
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests

            # Transport Admin - approve_transport + create_accommodation_requests
            ('1680236d-074e-4fe0-ad1c-19bb5581938b', 'a2222222-2222-2222-2222-222222222222'),  # approve_transport
            ('1680236d-074e-4fe0-ad1c-19bb5581938b', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests

            # Ticketing Admin - approve_trf + create_accommodation_requests
            ('3b11263f-bd35-4209-a049-80b00fedfd8b', 'a4444444-4444-4444-4444-444444444444'),  # approve_trf
            ('3b11263f-bd35-4209-a049-80b00fedfd8b', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests

            # Visa Clerk - approve_visa + create_accommodation_requests
            ('5f5c6f19-583c-45a9-8008-4a0a69a4f54b', 'a3333333-3333-3333-3333-333333333333'),  # approve_visa
            ('5f5c6f19-583c-45a9-8008-4a0a69a4f54b', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests

            # Line Manager - all approval permissions + create_accommodation_requests
            ('6028425e-c3ad-47bf-9d6a-ead9be8e9b6b', 'a1111111-1111-1111-1111-111111111111'),  # approve_accommodation
            ('6028425e-c3ad-47bf-9d6a-ead9be8e9b6b', 'a2222222-2222-2222-2222-222222222222'),  # approve_transport
            ('6028425e-c3ad-47bf-9d6a-ead9be8e9b6b', 'a3333333-3333-3333-3333-333333333333'),  # approve_visa
            ('6028425e-c3ad-47bf-9d6a-ead9be8e9b6b', 'a4444444-4444-4444-4444-444444444444'),  # approve_trf
            ('6028425e-c3ad-47bf-9d6a-ead9be8e9b6b', 'a5555555-5555-5555-5555-555555555555'),  # approve_claims
            ('6028425e-c3ad-47bf-9d6a-ead9be8e9b6b', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests

            # Requestor - create_accommodation_requests
            ('b2fa0f65-8cca-4341-8941-2f067edc7631', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests

            # Accommodation Admin - approve_accommodation + create_accommodation_requests
            ('c00facac-3e85-434c-956b-44885e71b1e2', 'a1111111-1111-1111-1111-111111111111'),  # approve_accommodation
            ('c00facac-3e85-434c-956b-44885e71b1e2', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests

            # Department Focal - all approval permissions + create_accommodation_requests
            ('e2fd380e-0472-42f6-aca1-d34abb659d2a', 'a1111111-1111-1111-1111-111111111111'),  # approve_accommodation
            ('e2fd380e-0472-42f6-aca1-d34abb659d2a', 'a2222222-2222-2222-2222-222222222222'),  # approve_transport
            ('e2fd380e-0472-42f6-aca1-d34abb659d2a', 'a3333333-3333-3333-3333-333333333333'),  # approve_visa
            ('e2fd380e-0472-42f6-aca1-d34abb659d2a', 'a4444444-4444-4444-4444-444444444444'),  # approve_trf
            ('e2fd380e-0472-42f6-aca1-d34abb659d2a', 'a5555555-5555-5555-5555-555555555555'),  # approve_claims
            ('e2fd380e-0472-42f6-aca1-d34abb659d2a', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests

            # Finance Clerk - approve_claims + create_accommodation_requests
            ('f2c90f2b-f35d-40b0-a5bf-ae505c553973', 'a5555555-5555-5555-5555-555555555555'),  # approve_claims
            ('f2c90f2b-f35d-40b0-a5bf-ae505c553973', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests

            # HOD - all approval permissions + create_accommodation_requests
            ('f9bce96c-9bc2-41b1-aa60-cf8febda571a', 'a1111111-1111-1111-1111-111111111111'),  # approve_accommodation
            ('f9bce96c-9bc2-41b1-aa60-cf8febda571a', 'a2222222-2222-2222-2222-222222222222'),  # approve_transport
            ('f9bce96c-9bc2-41b1-aa60-cf8febda571a', 'a3333333-3333-3333-3333-333333333333'),  # approve_visa
            ('f9bce96c-9bc2-41b1-aa60-cf8febda571a', 'a4444444-4444-4444-4444-444444444444'),  # approve_trf
            ('f9bce96c-9bc2-41b1-aa60-cf8febda571a', 'a5555555-5555-5555-5555-555555555555'),  # approve_claims
            ('f9bce96c-9bc2-41b1-aa60-cf8febda571a', 'a6666666-6666-6666-6666-666666666666'),  # create_accommodation_requests
        ]

        # Insert new role-permission mappings in batches
        for i in range(0, len(role_permission_updates), 50):
            batch = role_permission_updates[i:i+50]
            placeholders = ','.join(['(%s, %s, NOW())'] * len(batch))
            params = [item for pair in batch for item in pair]
            rp_sql = f"""
                INSERT INTO accounts_rolepermission (role_id, permission_id, created_at)
                VALUES {placeholders}
                ON CONFLICT (role_id, permission_id) DO NOTHING;
            """
            cursor.execute(rp_sql, params)

        print(f"   ✓ Added {len(role_permission_updates)} new role-permission mappings")

        # ============================================================================
        # STEP 3: Remove old role-specific permission mappings
        # ============================================================================
        print("\n[3/4] Removing old role-specific permission mappings...")

        old_permission_ids = [
            '3b1fff1e-729d-441c-ab52-4717fa882801',  # approve_accommodation_focal
            '78c83997-6f7d-4f28-9ecb-4c1c48e4659a',  # approve_accommodation_hod
            'e1f2316f-ea36-4fd0-88ce-2fb0c272ebd2',  # approve_accommodation_manager
            '3937477e-e944-4082-88fc-44238bd7e278',  # approve_transport_focal
            'bda24201-39be-49af-ae76-fd9c66cb54e8',  # approve_transport_hod
            'dc6e8b5e-8470-402e-a616-9edeb1a85613',  # approve_transport_manager
            '8537cfa5-ea7b-47c6-956c-3b86ff2db8a7',  # approve_trf_focal
            '06693339-4e83-4170-9da6-e120f4848156',  # approve_trf_hod
            '93c925bb-1d67-48e3-8f96-7805acdc1d84',  # approve_trf_manager
            '85429a67-3c16-4625-b633-fc94635a56c9',  # approve_claims_focal
            '7bdd8708-3792-4fb7-a8a9-01851dcf8d16',  # approve_claims_hod
            '70faef6f-4642-4ea0-b2c4-6946c4fe9198',  # approve_claims_manager
            'f1bb2dd1-9993-4f91-8b96-597a0f3f34db',  # approve_visa_focal
            'aef57921-f0c4-4b28-bfe5-9eda97d55f0e',  # approve_visa_hod
            'f9709012-8825-428d-aca6-2f39519dd88e',  # approve_visa_manager
        ]

        placeholders = ','.join(['%s'] * len(old_permission_ids))
        delete_mappings_sql = f"""
            DELETE FROM accounts_rolepermission
            WHERE permission_id IN ({placeholders});
        """
        cursor.execute(delete_mappings_sql, old_permission_ids)
        deleted_mappings = cursor.rowcount
        print(f"   ✓ Removed {deleted_mappings} old role-permission mappings")

        # ============================================================================
        # STEP 4: Delete old role-specific permissions
        # ============================================================================
        print("\n[4/4] Deleting old role-specific permissions...")

        delete_permissions_sql = f"""
            DELETE FROM accounts_permission
            WHERE id IN ({placeholders});
        """
        cursor.execute(delete_permissions_sql, old_permission_ids)
        deleted_perms = cursor.rowcount
        print(f"   ✓ Deleted {deleted_perms} old permissions")

        print("\n" + "="*80)
        print("✓ PERMISSION REFACTORING COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nSummary:")
        print(f"  • Added 6 new generic permissions")
        print(f"  • Added {len(role_permission_updates)} new role-permission mappings")
        print(f"  • Removed {deleted_mappings} old role-permission mappings")
        print(f"  • Deleted {deleted_perms} old role-specific permissions")
        print("\nNew generic permissions:")
        print("  • approve_accommodation")
        print("  • approve_transport")
        print("  • approve_visa")
        print("  • approve_trf")
        print("  • approve_claims")
        print("  • create_accommodation_requests")
        print("="*80 + "\n")


def reverse_refactor(apps, schema_editor):
    """Reverse the refactoring (restore old permissions)"""
    from django.db import connection

    with connection.cursor() as cursor:
        print("\nReversing permission refactoring...")

        # Delete new permissions
        new_permission_ids = [
            'a1111111-1111-1111-1111-111111111111',
            'a2222222-2222-2222-2222-222222222222',
            'a3333333-3333-3333-3333-333333333333',
            'a4444444-4444-4444-4444-444444444444',
            'a5555555-5555-5555-5555-555555555555',
            'a6666666-6666-6666-6666-666666666666',
        ]

        placeholders = ','.join(['%s'] * len(new_permission_ids))
        cursor.execute(f"DELETE FROM accounts_permission WHERE id IN ({placeholders});", new_permission_ids)

        # Re-run the original populate_roles_permissions migration to restore old permissions
        print("✓ Reversed permission refactoring")
        print("NOTE: You may need to re-run migration 0008 to restore old permissions completely")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_adminactionlog'),
    ]

    operations = [
        migrations.RunPython(refactor_permissions, reverse_refactor),
    ]
