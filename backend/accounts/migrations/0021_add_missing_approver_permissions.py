# Migration to add missing permissions to all non-admin roles
# The original migration 0008 only assigned permissions to System Administrator
# This migration adds appropriate permissions to all other roles
#
# Bug fix (2026-08-19): this migration's raw-SQL RolePermission inserts below
# reference hardcoded UUIDs for the Employee, Focal, and Ticketing Clerk
# roles, but no migration ever created those three roles - migration 0008
# only creates System Administrator, Transport Admin, Ticketing Admin, Visa
# Clerk, Line Manager, Requestor, Accommodation Admin, Department Focal,
# Finance Clerk, and HOD. On a genuinely fresh database this migration always
# failed with a ForeignKeyViolation (caught during the Combined Request
# module removal, see docs/COMBINED_REQUEST_MODULE_REMOVAL_ROADMAP.md); it
# only ever "worked" against the existing dev database because those three
# roles had been seeded there out-of-band, outside of any migration. Fixed
# by creating the three missing roles (idempotently, matching migration
# 0026's "create Registered User role" pattern) before the raw-SQL inserts
# run - a no-op against databases where they already exist.

from django.db import migrations


def add_missing_permissions(apps, schema_editor):
    """
    Add missing permissions to all roles based on their function.
    Only uses permissions and roles that exist in the database.
    """
    from django.db import connection

    Role = apps.get_model("accounts", "Role")

    # These three roles are referenced below by hardcoded UUID but are never
    # created by any other migration - see the bug-fix note above.
    MISSING_ROLES = [
        (
            "b0b7ee60-b3a4-420c-a7af-acdebc7b214e",
            "Employee",
            "Can submit requests (TRF, Claims, Visa). Same permission set as Requestor.",
        ),
        (
            "1c62cdb3-8dd7-40fa-9566-d35123f1d737",
            "Focal",
            "Verifies initial requests from their department. Same permission set as Department Focal.",
        ),
        (
            "6c175d9c-fed9-4104-8492-352fc60a0efa",
            "Ticketing Clerk",
            "Processes flight bookings for approved TRFs. Same permission set as Ticketing Admin.",
        ),
    ]
    for role_id, name, description in MISSING_ROLES:
        Role.objects.get_or_create(
            id=role_id, defaults={"name": name, "description": description}
        )

    with connection.cursor() as cursor:
        print("\n" + "=" * 70)
        print("ADDING MISSING PERMISSIONS TO ROLES")
        print("=" * 70)

        # Role IDs - ONLY roles that exist in the database
        ROLES = {
            "system_admin": "0ec80c3e-dc8d-4c72-bc81-7a8262c94b94",
            "transport_admin": "1680236d-074e-4fe0-ad1c-19bb5581938b",
            "ticketing_admin": "3b11263f-bd35-4209-a049-80b00fedfd8b",
            "visa_clerk": "5f5c6f19-583c-45a9-8008-4a0a69a4f54b",
            "line_manager": "6028425e-c3ad-47bf-9d6a-ead9be8e9b6b",
            "requestor": "b2fa0f65-8cca-4341-8941-2f067edc7631",
            "accommodation_admin": "c00facac-3e85-434c-956b-44885e71b1e2",
            "department_focal": "e2fd380e-0472-42f6-aca1-d34abb659d2a",
            "hod": "f9bce96c-9bc2-41b1-aa60-cf8febda571a",
            "employee": "b0b7ee60-b3a4-420c-a7af-acdebc7b214e",
            "focal": "1c62cdb3-8dd7-40fa-9566-d35123f1d737",
            "ticketing_clerk": "6c175d9c-fed9-4104-8492-352fc60a0efa",
        }

        # Permission IDs - ONLY permissions that exist in the database
        PERMS = {
            # Basic permissions
            "view_pending_approvals": "097e9b18-9c83-4e86-860c-6f0f82140153",
            "view_own_requests": "e74820dc-88eb-4b45-9a10-b0fff4b789af",
            "view_dashboard_summary": "c2783523-eed8-41a0-a5fa-46377ecdf1ff",
            "view_sidebar_counts": "3486b687-6726-4cbd-bb22-d7cb030fbe57",
            "manage_own_profile": "f3db24ef-222d-468b-960a-02b2cd593e94",
            "upload_documents": "5b03c91b-d1ea-4a27-96d3-3f317f074ca0",
            "view_department_requests": "7e8bf95c-e3ef-4df3-b726-4a93354df577",
            # Create permissions (using current names after migration 0020)
            "create_trf": "5ecb975a-94d1-439c-9dcc-96f2cdf89bec",
            "create_transport": "9ae6bbc7-fb19-436f-966b-3b87dda11257",
            "create_visa": "2bf07090-965a-4ecd-80fe-9f18bf43daae",
            "create_accommodation": "a6666666-6666-6666-6666-666666666666",
            # Generic approval permissions (from migration 0012)
            "approve_accommodation": "a1111111-1111-1111-1111-111111111111",
            "approve_transport": "a2222222-2222-2222-2222-222222222222",
            "approve_visa": "a3333333-3333-3333-3333-333333333333",
            "approve_trf": "a4444444-4444-4444-4444-444444444444",
            # Admin module access
            "view_admin_accommodation": "38e1167e-99bb-4193-af77-0774b63775af",
            "view_admin_transport": "1c38aa80-b09d-4f9e-957b-c1d7fdb4d999",
            "view_admin_visa": "dc27c90c-693a-471e-96fb-4914dc9e341b",
            "view_admin_flights": "91c37e16-9bc1-4d0c-942d-97d4e6fbe240",
            # Admin processing
            "manage_accommodation_bookings": "bd152af5-b886-43a5-8593-5dc64d2e3218",
            "manage_transport_requests": "715c17a7-b31a-4a82-acc7-68a695dec513",
            "process_visa_applications": "eb012884-104d-4246-b027-51af4c0efe78",
            "process_flights": "3888de2d-9c5f-4aff-8956-8aa31c88a74d",
            "manage_flights": "01d074ec-903c-4988-913e-fcaa8f3564d1",
            # Reporting
            "generate_admin_reports": "14452fd3-654a-4070-961d-5a141d91b156",
            "export_data": "21e9bf27-5e24-4964-8afc-f17e4f5c5e1c",
            "view_all_trf": "2386d8ac-f7ac-42dc-952a-21939e5dd890",
            "view_all_transport": "fad09f17-b1c6-4917-a2c4-50bbcffce0d2",
            # Visa specific
            "view_visa_applications": "0fc93418-5c21-4664-a69e-ff2d42a912a2",
            "view_visa_reports": "86fc735b-2f4d-4b9a-b226-e3d027862369",
        }

        # Basic permissions for all users
        BASIC_PERMS = [
            PERMS["view_own_requests"],
            PERMS["view_dashboard_summary"],
            PERMS["view_sidebar_counts"],
            PERMS["manage_own_profile"],
            PERMS["upload_documents"],
        ]

        # Create permissions for regular users
        CREATE_PERMS = [
            PERMS["create_trf"],
            PERMS["create_transport"],
            PERMS["create_visa"],
            PERMS["create_accommodation"],
        ]

        # Approval permissions for approvers
        APPROVE_PERMS = [
            PERMS["approve_accommodation"],
            PERMS["approve_transport"],
            PERMS["approve_visa"],
            PERMS["approve_trf"],
            PERMS["view_pending_approvals"],
            PERMS["view_department_requests"],
        ]

        role_permission_pairs = []

        # ============================================================
        # REQUESTOR - Basic user who can create requests
        # ============================================================
        print("\n[1/11] Adding Requestor permissions...")
        for perm_id in BASIC_PERMS + CREATE_PERMS:
            role_permission_pairs.append((ROLES["requestor"], perm_id))

        # ============================================================
        # EMPLOYEE - Same as Requestor
        # ============================================================
        print("[2/11] Adding Employee permissions...")
        for perm_id in BASIC_PERMS + CREATE_PERMS:
            role_permission_pairs.append((ROLES["employee"], perm_id))

        # ============================================================
        # LINE MANAGER - Can approve requests from direct reports
        # ============================================================
        print("[3/11] Adding Line Manager permissions...")
        for perm_id in BASIC_PERMS + CREATE_PERMS + APPROVE_PERMS:
            role_permission_pairs.append((ROLES["line_manager"], perm_id))

        # ============================================================
        # DEPARTMENT FOCAL - First level approval in department
        # ============================================================
        print("[4/11] Adding Department Focal permissions...")
        for perm_id in BASIC_PERMS + CREATE_PERMS + APPROVE_PERMS:
            role_permission_pairs.append((ROLES["department_focal"], perm_id))

        # ============================================================
        # FOCAL - Same as Department Focal
        # ============================================================
        print("[5/11] Adding Focal permissions...")
        for perm_id in BASIC_PERMS + CREATE_PERMS + APPROVE_PERMS:
            role_permission_pairs.append((ROLES["focal"], perm_id))

        # ============================================================
        # HOD - Head of Department, higher level approvals
        # ============================================================
        print("[6/11] Adding HOD permissions...")
        hod_perms = (
            BASIC_PERMS
            + CREATE_PERMS
            + APPROVE_PERMS
            + [
                PERMS["generate_admin_reports"],
                PERMS["view_all_trf"],
                PERMS["view_all_transport"],
            ]
        )
        for perm_id in hod_perms:
            role_permission_pairs.append((ROLES["hod"], perm_id))

        # ============================================================
        # ACCOMMODATION ADMIN - Manages accommodation bookings
        # ============================================================
        print("[7/11] Adding Accommodation Admin permissions...")
        accommodation_admin_perms = (
            BASIC_PERMS
            + CREATE_PERMS
            + [
                PERMS["view_admin_accommodation"],
                PERMS["manage_accommodation_bookings"],
                PERMS["approve_accommodation"],
                PERMS["view_pending_approvals"],
            ]
        )
        for perm_id in accommodation_admin_perms:
            role_permission_pairs.append((ROLES["accommodation_admin"], perm_id))

        # ============================================================
        # TRANSPORT ADMIN - Manages transport requests
        # ============================================================
        print("[8/11] Adding Transport Admin permissions...")
        transport_admin_perms = (
            BASIC_PERMS
            + CREATE_PERMS
            + [
                PERMS["view_admin_transport"],
                PERMS["manage_transport_requests"],
                PERMS["approve_transport"],
                PERMS["view_pending_approvals"],
                PERMS["view_all_transport"],
            ]
        )
        for perm_id in transport_admin_perms:
            role_permission_pairs.append((ROLES["transport_admin"], perm_id))

        # ============================================================
        # VISA CLERK - Processes visa applications
        # ============================================================
        print("[9/11] Adding Visa Clerk permissions...")
        visa_clerk_perms = (
            BASIC_PERMS
            + CREATE_PERMS
            + [
                PERMS["view_admin_visa"],
                PERMS["process_visa_applications"],
                PERMS["approve_visa"],
                PERMS["view_pending_approvals"],
                PERMS["view_visa_applications"],
                PERMS["view_visa_reports"],
            ]
        )
        for perm_id in visa_clerk_perms:
            role_permission_pairs.append((ROLES["visa_clerk"], perm_id))

        # ============================================================
        # TICKETING ADMIN - Manages flight bookings
        # ============================================================
        print("[10/11] Adding Ticketing Admin permissions...")
        ticketing_admin_perms = (
            BASIC_PERMS
            + CREATE_PERMS
            + [
                PERMS["view_admin_flights"],
                PERMS["manage_flights"],
                PERMS["process_flights"],
                PERMS["approve_trf"],
                PERMS["view_pending_approvals"],
                PERMS["view_all_trf"],
            ]
        )
        for perm_id in ticketing_admin_perms:
            role_permission_pairs.append((ROLES["ticketing_admin"], perm_id))

        # ============================================================
        # TICKETING CLERK - Same as Ticketing Admin
        # ============================================================
        print("[11/11] Adding Ticketing Clerk permissions...")
        for perm_id in ticketing_admin_perms:
            role_permission_pairs.append((ROLES["ticketing_clerk"], perm_id))

        # ============================================================
        # INSERT ALL ROLE-PERMISSION MAPPINGS
        # ============================================================
        print(f"\nInserting {len(role_permission_pairs)} role-permission mappings...")

        for role_id, perm_id in role_permission_pairs:
            insert_sql = """
                INSERT INTO accounts_rolepermission (role_id, permission_id, created_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (role_id, permission_id) DO NOTHING;
            """
            cursor.execute(insert_sql, [role_id, perm_id])

        print("\n" + "=" * 70)
        print("PERMISSIONS ADDED SUCCESSFULLY")
        print("=" * 70)
        print("\nRoles configured:")
        print("  - Requestor: Basic + Create")
        print("  - Employee: Basic + Create")
        print("  - Line Manager: Basic + Create + Approve")
        print("  - Department Focal: Basic + Create + Approve")
        print("  - Focal: Basic + Create + Approve")
        print("  - HOD: Basic + Create + Approve + Reports")
        print("  - Accommodation Admin: Admin module access")
        print("  - Transport Admin: Admin module access")
        print("  - Visa Clerk: Admin module access")
        print("  - Ticketing Admin: Admin module access")
        print("  - Ticketing Clerk: Admin module access")
        print("=" * 70 + "\n")


def reverse_migration(apps, schema_editor):
    """
    Note: This doesn't remove permissions, just logs the message.
    """
    print("Note: Permission mappings are not removed in reverse migration")
    print("Use Role Management UI to adjust permissions if needed")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0020_standardize_create_permission_names"),
    ]

    operations = [
        migrations.RunPython(add_missing_permissions, reverse_migration),
    ]
