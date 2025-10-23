# Generated migration to populate roles, permissions, and role-permission mappings from source system

from django.db import migrations


def populate_roles_and_permissions(apps, schema_editor):
    # Use raw SQL to insert data
    from django.db import connection

    with connection.cursor() as cursor:
        # Insert roles
        roles_sql = """
            INSERT INTO accounts_role (id, name, description, created_at, updated_at) VALUES
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'System Administrator', 'Has full access to all system features and settings.', NOW(), NOW()),
            ('1680236d-074e-4fe0-ad1c-19bb5581938b', 'Transport Admin', 'Manages transport and vehicle booking requests.', NOW(), NOW()),
            ('3b11263f-bd35-4209-a049-80b00fedfd8b', 'Ticketing Admin', 'Processes flight bookings for approved TRFs.', NOW(), NOW()),
            ('5f5c6f19-583c-45a9-8008-4a0a69a4f54b', 'Visa Clerk', 'Processes visa applications.', NOW(), NOW()),
            ('6028425e-c3ad-47bf-9d6a-ead9be8e9b6b', 'Line Manager', 'Approves requests from their direct reports.', NOW(), NOW()),
            ('b2fa0f65-8cca-4341-8941-2f067edc7631', 'Requestor', 'Can submit requests (TRF, Claims, Visa).', NOW(), NOW()),
            ('c00facac-3e85-434c-956b-44885e71b1e2', 'Accommodation Admin', 'Manages staff house and camp bookings.', NOW(), NOW()),
            ('e2fd380e-0472-42f6-aca1-d34abb659d2a', 'Department Focal', 'Verifies initial requests from their department.', NOW(), NOW()),
            ('f2c90f2b-f35d-40b0-a5bf-ae505c553973', 'Finance Clerk', 'Verifies and processes expense claims for payment.', NOW(), NOW()),
            ('f9bce96c-9bc2-41b1-aa60-cf8febda571a', 'HOD', 'Head of Department, approves high-cost or international requests.', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING;
        """
        cursor.execute(roles_sql)
        print("✓ Created 10 roles")

        # Insert permissions
        permissions_sql = """
            INSERT INTO accounts_permission (id, name, description, created_at, updated_at) VALUES
            ('01d074ec-903c-4988-913e-fcaa8f3564d1', 'manage_flights', 'Can manage flight bookings and flight admin interface', NOW(), NOW()),
            ('06693339-4e83-4170-9da6-e120f4848156', 'approve_trf_hod', 'Can perform HOD approval for TRFs.', NOW(), NOW()),
            ('067eb066-e964-492f-b375-ca4866c38c4a', 'view_admin_claims', 'Can access the Claims Admin module interface', NOW(), NOW()),
            ('097e9b18-9c83-4e86-860c-6f0f82140153', 'view_pending_approvals', 'Can view requests pending their approval (for approver roles)', NOW(), NOW()),
            ('0fc93418-5c21-4664-a69e-ff2d42a912a2', 'view_visa_applications', 'Can view visa applications (read-only)', NOW(), NOW()),
            ('14452fd3-654a-4070-961d-5a141d91b156', 'generate_admin_reports', 'Can generate comprehensive admin reports and analytics.', NOW(), NOW()),
            ('15b7b7fb-2c7e-45eb-b75f-750a8a687c2f', 'manage_users', 'Can create, edit, delete, and assign roles to users.', NOW(), NOW()),
            ('17ac060b-fe22-41f5-a203-d3daab574711', 'view_users', 'Can view the user list.', NOW(), NOW()),
            ('19617c29-4c76-44d0-957d-2f2b82bb7518', 'approve_accommodation_requests', 'Can approve accommodation booking requests', NOW(), NOW()),
            ('1c38aa80-b09d-4f9e-957b-c1d7fdb4d999', 'view_admin_transport', 'Can access the Transport Admin module interface', NOW(), NOW()),
            ('21e9bf27-5e24-4964-8afc-f17e4f5c5e1c', 'export_data', 'Can export application data in various formats.', NOW(), NOW()),
            ('2386d8ac-f7ac-42dc-952a-21939e5dd890', 'view_all_trf', 'Can view all TRFs across departments.', NOW(), NOW()),
            ('2bf07090-965a-4ecd-80fe-9f18bf43daae', 'create_visa_requests', 'Can create new visa application requests', NOW(), NOW()),
            ('3320e611-04f9-4c88-b9c4-ff1249fb5fff', 'process_claims', 'Can process claims for payment (Finance Clerk).', NOW(), NOW()),
            ('3486b687-6726-4cbd-bb22-d7cb030fbe57', 'view_sidebar_counts', 'Can view notification counts and sidebar information.', NOW(), NOW()),
            ('3888de2d-9c5f-4aff-8956-8aa31c88a74d', 'process_flights', 'Can manage flight bookings (Ticketing Admin).', NOW(), NOW()),
            ('38e1167e-99bb-4193-af77-0774b63775af', 'view_admin_accommodation', 'Can access the Accommodation Admin module interface', NOW(), NOW()),
            ('3937477e-e944-4082-88fc-44238bd7e278', 'approve_transport_focal', 'Approve transport requests at department focal level', NOW(), NOW()),
            ('39767ebb-c3ef-45de-8b6f-4b8e7ef58391', 'system_admin', 'Full system administration access', NOW(), NOW()),
            ('3b1fff1e-729d-441c-ab52-4717fa882801', 'approve_accommodation_focal', 'Approve accommodation requests at department focal level', NOW(), NOW()),
            ('42ec0a34-aa3e-400e-90a2-1e4539f7edca', 'manage_application_settings', 'Can modify core application settings and configurations.', NOW(), NOW()),
            ('5553f911-037e-42c2-a56c-b890f85c321f', 'send_notifications', 'Can send manual notifications to users.', NOW(), NOW()),
            ('5abf6fd1-cd52-4ad2-891b-8770eda8eab0', 'create_claims', 'Can create new Expense Claims.', NOW(), NOW()),
            ('5b03c91b-d1ea-4a27-96d3-3f317f074ca0', 'upload_documents', 'Can upload supporting documents and files.', NOW(), NOW()),
            ('5ecb975a-94d1-439c-9dcc-96f2cdf89bec', 'create_trf', 'Can create new Travel Request Forms.', NOW(), NOW()),
            ('70faef6f-4642-4ea0-b2c4-6946c4fe9198', 'approve_claims_manager', 'Can perform Line Manager approval for Claims.', NOW(), NOW()),
            ('715c17a7-b31a-4a82-acc7-68a695dec513', 'manage_transport_requests', 'Can manage and assign transport bookings.', NOW(), NOW()),
            ('78c83997-6f7d-4f28-9ecb-4c1c48e4659a', 'approve_accommodation_hod', 'Approve accommodation requests as HOD', NOW(), NOW()),
            ('7bdd8708-3792-4fb7-a8a9-01851dcf8d16', 'approve_claims_hod', 'Can perform HOD approval for Claims.', NOW(), NOW()),
            ('7e8bf95c-e3ef-4df3-b726-4a93354df577', 'view_department_requests', 'Can view requests from their department', NOW(), NOW()),
            ('8537cfa5-ea7b-47c6-956c-3b86ff2db8a7', 'approve_trf_focal', 'Can perform Department Focal approval for TRFs.', NOW(), NOW()),
            ('85429a67-3c16-4625-b633-fc94635a56c9', 'approve_claims_focal', 'Can perform Department Focal approval for Claims.', NOW(), NOW()),
            ('86fc735b-2f4d-4b9a-b226-e3d027862369', 'view_visa_reports', 'Can view visa processing reports and statistics.', NOW(), NOW()),
            ('9164866b-4b16-4bd4-92f9-936e9dfa154d', 'manage_roles', 'Can create, edit, and delete roles and assign permissions to them.', NOW(), NOW()),
            ('91c37e16-9bc1-4d0c-942d-97d4e6fbe240', 'view_admin_flights', 'Can access the Flight Admin module interface', NOW(), NOW()),
            ('93c925bb-1d67-48e3-8f96-7805acdc1d84', 'approve_trf_manager', 'Can perform Line Manager approval for TRFs.', NOW(), NOW()),
            ('96d6a6d2-565d-41e0-ba03-6ef25f50edd2', 'manage_notifications', 'Manage notification settings and templates', NOW(), NOW()),
            ('97f7b51a-7a30-45e6-944a-eba390bf36da', 'view_activity_logs', 'Can view user activity and system logs.', NOW(), NOW()),
            ('9ae6bbc7-fb19-436f-966b-3b87dda11257', 'create_transport_requests', 'Can create new transport/vehicle booking requests.', NOW(), NOW()),
            ('aef57921-f0c4-4b28-bfe5-9eda97d55f0e', 'approve_visa_hod', 'Approve visa applications at HOD level', NOW(), NOW()),
            ('bd152af5-b886-43a5-8593-5dc64d2e3218', 'manage_accommodation_bookings', 'Can manage accommodation bookings (Accommodation Admin).', NOW(), NOW()),
            ('bda24201-39be-49af-ae76-fd9c66cb54e8', 'approve_transport_hod', 'Approve transport requests at HOD level', NOW(), NOW()),
            ('c2783523-eed8-41a0-a5fa-46377ecdf1ff', 'view_dashboard_summary', 'Can access dashboard summary statistics.', NOW(), NOW()),
            ('cdfb02c8-6d1d-43fd-a08f-eebddcf31059', 'view_system_settings', 'Can view the system settings page.', NOW(), NOW()),
            ('dc27c90c-693a-471e-96fb-4914dc9e341b', 'view_admin_visa', 'Can access the Visa Admin module interface', NOW(), NOW()),
            ('dc6e8b5e-8470-402e-a616-9edeb1a85613', 'approve_transport_manager', 'Approve transport requests at line manager level', NOW(), NOW()),
            ('dea1f0b7-a0f7-499d-9920-fd09c5e476d6', 'view_profiles', 'Can view other users profile information.', NOW(), NOW()),
            ('e0bf0f10-aca5-4de4-836a-de5054f22fa3', 'approve_visa_requests', 'Can approve visa application requests', NOW(), NOW()),
            ('e1aac93f-e889-4388-a606-2a56370d555a', 'manage_document_templates', 'Can create and edit document templates.', NOW(), NOW()),
            ('e1f2316f-ea36-4fd0-88ce-2fb0c272ebd2', 'approve_accommodation_manager', 'Approve accommodation requests as Line Manager', NOW(), NOW()),
            ('e70a92ce-2305-4b3d-ba10-5b8509cab3ac', 'access_debug_endpoints', 'Can access debugging and testing endpoints.', NOW(), NOW()),
            ('e74820dc-88eb-4b45-9a10-b0fff4b789af', 'view_own_requests', 'Can view only their own submitted requests', NOW(), NOW()),
            ('e9e2f485-436d-4ef3-b999-73a4a5842b04', 'approve_transport_requests', 'Can approve transport booking requests.', NOW(), NOW()),
            ('eb012884-104d-4246-b027-51af4c0efe78', 'process_visa_applications', 'Can manage visa applications (Visa Clerk).', NOW(), NOW()),
            ('f1bb2dd1-9993-4f91-8b96-597a0f3f34db', 'approve_visa_focal', 'Approve visa applications at department focal level', NOW(), NOW()),
            ('f3381af1-5209-424d-8a7e-82de7a74e103', 'view_all_claims', 'Can view all Claims across departments.', NOW(), NOW()),
            ('f3db24ef-222d-468b-960a-02b2cd593e94', 'manage_own_profile', 'Can edit and update own user profile.', NOW(), NOW()),
            ('f9709012-8825-428d-aca6-2f39519dd88e', 'approve_visa_manager', 'Approve visa applications at line manager level', NOW(), NOW()),
            ('fad09f17-b1c6-4917-a2c4-50bbcffce0d2', 'view_all_transport', 'Can view all transport requests across departments.', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING;
        """
        cursor.execute(permissions_sql)
        print("✓ Created 59 permissions")

        # Insert role-permission mappings
        # Due to character limits, this uses a helper function
        role_permission_pairs = [
            # System Administrator (48 permissions)
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'e70a92ce-2305-4b3d-ba10-5b8509cab3ac'),  # access_debug_endpoints
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '19617c29-4c76-44d0-957d-2f2b82bb7518'),  # approve_accommodation_requests
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '85429a67-3c16-4625-b633-fc94635a56c9'),  # approve_claims_focal
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '7bdd8708-3792-4fb7-a8a9-01851dcf8d16'),  # approve_claims_hod
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '70faef6f-4642-4ea0-b2c4-6946c4fe9198'),  # approve_claims_manager
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'e9e2f485-436d-4ef3-b999-73a4a5842b04'),  # approve_transport_requests
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '8537cfa5-ea7b-47c6-956c-3b86ff2db8a7'),  # approve_trf_focal
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '06693339-4e83-4170-9da6-e120f4848156'),  # approve_trf_hod
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '93c925bb-1d67-48e3-8f96-7805acdc1d84'),  # approve_trf_manager
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'e0bf0f10-aca5-4de4-836a-de5054f22fa3'),  # approve_visa_requests
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '5abf6fd1-cd52-4ad2-891b-8770eda8eab0'),  # create_claims
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '9ae6bbc7-fb19-436f-966b-3b87dda11257'),  # create_transport_requests
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '5ecb975a-94d1-439c-9dcc-96f2cdf89bec'),  # create_trf
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '2bf07090-965a-4ecd-80fe-9f18bf43daae'),  # create_visa_requests
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '21e9bf27-5e24-4964-8afc-f17e4f5c5e1c'),  # export_data
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '14452fd3-654a-4070-961d-5a141d91b156'),  # generate_admin_reports
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'bd152af5-b886-43a5-8593-5dc64d2e3218'),  # manage_accommodation_bookings
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '42ec0a34-aa3e-400e-90a2-1e4539f7edca'),  # manage_application_settings
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'e1aac93f-e889-4388-a606-2a56370d555a'),  # manage_document_templates
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '96d6a6d2-565d-41e0-ba03-6ef25f50edd2'),  # manage_notifications
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'f3db24ef-222d-468b-960a-02b2cd593e94'),  # manage_own_profile
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '9164866b-4b16-4bd4-92f9-936e9dfa154d'),  # manage_roles
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '715c17a7-b31a-4a82-acc7-68a695dec513'),  # manage_transport_requests
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '15b7b7fb-2c7e-45eb-b75f-750a8a687c2f'),  # manage_users
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '3320e611-04f9-4c88-b9c4-ff1249fb5fff'),  # process_claims
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '3888de2d-9c5f-4aff-8956-8aa31c88a74d'),  # process_flights
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'eb012884-104d-4246-b027-51af4c0efe78'),  # process_visa_applications
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '5553f911-037e-42c2-a56c-b890f85c321f'),  # send_notifications
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '39767ebb-c3ef-45de-8b6f-4b8e7ef58391'),  # system_admin
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '5b03c91b-d1ea-4a27-96d3-3f317f074ca0'),  # upload_documents
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '97f7b51a-7a30-45e6-944a-eba390bf36da'),  # view_activity_logs
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '38e1167e-99bb-4193-af77-0774b63775af'),  # view_admin_accommodation
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '067eb066-e964-492f-b375-ca4866c38c4a'),  # view_admin_claims
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '91c37e16-9bc1-4d0c-942d-97d4e6fbe240'),  # view_admin_flights
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '1c38aa80-b09d-4f9e-957b-c1d7fdb4d999'),  # view_admin_transport
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'dc27c90c-693a-471e-96fb-4914dc9e341b'),  # view_admin_visa
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'f3381af1-5209-424d-8a7e-82de7a74e103'),  # view_all_claims
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'fad09f17-b1c6-4917-a2c4-50bbcffce0d2'),  # view_all_transport
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '2386d8ac-f7ac-42dc-952a-21939e5dd890'),  # view_all_trf
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'c2783523-eed8-41a0-a5fa-46377ecdf1ff'),  # view_dashboard_summary
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'e74820dc-88eb-4b45-9a10-b0fff4b789af'),  # view_own_requests
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'dea1f0b7-a0f7-499d-9920-fd09c5e476d6'),  # view_profiles
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '3486b687-6726-4cbd-bb22-d7cb030fbe57'),  # view_sidebar_counts
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', 'cdfb02c8-6d1d-43fd-a08f-eebddcf31059'),  # view_system_settings
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '17ac060b-fe22-41f5-a203-d3daab574711'),  # view_users
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '0fc93418-5c21-4664-a69e-ff2d42a912a2'),  # view_visa_applications
            ('0ec80c3e-dc8d-4c72-bc81-7a8262c94b94', '86fc735b-2f4d-4b9a-b226-e3d027862369'),  # view_visa_reports
        ]

        # Insert role-permission pairs in batches
        for i in range(0, len(role_permission_pairs), 50):
            batch = role_permission_pairs[i:i+50]
            values = ','.join([f"('{role_id}', '{perm_id}', NOW())" for role_id, perm_id in batch])
            rp_sql = f"""
                INSERT INTO accounts_rolepermission (role_id, permission_id, created_at)
                VALUES {values}
                ON CONFLICT (role_id, permission_id) DO NOTHING;
            """
            cursor.execute(rp_sql)

        print(f"✓ Created {len(role_permission_pairs)} role-permission mappings")
        print("\n✓ Successfully populated all roles, permissions, and mappings!")


def reverse_populate(apps, schema_editor):
    """Remove all roles and permissions if migration is reversed"""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM accounts_rolepermission;")
        cursor.execute("DELETE FROM accounts_role;")
        cursor.execute("DELETE FROM accounts_permission;")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_recreate_roles_permissions_with_uuid'),
    ]

    operations = [
        migrations.RunPython(populate_roles_and_permissions, reverse_populate),
    ]
