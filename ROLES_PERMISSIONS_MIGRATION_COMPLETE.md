# Roles and Permissions Migration - Complete

## Summary

Successfully replicated all roles, permissions, and role-permission mappings from the source database (syntra) to the new TMS application database.

## What Was Accomplished

### 1. Database Analysis
- Connected to source PostgreSQL database `syntra` (username: postgres, password: 221202)
- Analyzed 10 roles, 59 permissions, and 193 role-permission mappings
- Documented complete RBAC (Role-Based Access Control) implementation

### 2. Backend Model Updates
**File**: `backend/accounts/models.py`
- Updated `Role` model to use UUID primary key instead of auto-incrementing integer
- Updated `Permission` model to use UUID primary key instead of auto-incrementing integer
- Added `import uuid` statement
- Changed ID field definition:
  ```python
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  ```

### 3. Database Migrations Created

#### Migration 0007: `0007_recreate_roles_permissions_with_uuid.py`
- Drops existing role and permission tables
- Recreates tables with UUID primary keys
- Converts `accounts_user.role_id` from bigint to UUID
- Re-establishes foreign key constraints

#### Migration 0008: `0008_populate_roles_permissions.py`
- Populates all 10 roles from source system
- Populates all 59 permissions from source system
- Creates 47 role-permission mappings for System Administrator
- Uses raw SQL for data insertion to avoid Django ORM UUID conversion issues

#### Additional SQL Insert
- Inserted remaining 146 role-permission mappings for the other 9 roles
- Total: 193 role-permission mappings successfully migrated

## Roles Replicated (10 Total)

| Role Name | ID | Description | Permissions Count |
|-----------|-----|-------------|-------------------|
| System Administrator | 0ec80c3e-dc8d-4c72-bc81-7a8262c94b94 | Has full access to all system features and settings. | 47 |
| Transport Admin | 1680236d-074e-4fe0-ad1c-19bb5581938b | Manages transport and vehicle booking requests. | 15 |
| Ticketing Admin | 3b11263f-bd35-4209-a049-80b00fedfd8b | Processes flight bookings for approved TRFs. | 13 |
| Visa Clerk | 5f5c6f19-583c-45a9-8008-4a0a69a4f54b | Processes visa applications. | 17 |
| Line Manager | 6028425e-c3ad-47bf-9d6a-ead9be8e9b6b | Approves requests from their direct reports. | 20 |
| Requestor | b2fa0f65-8cca-4341-8941-2f067edc7631 | Can submit requests (TRF, Claims, Visa). | 9 |
| Accommodation Admin | c00facac-3e85-434c-956b-44885e71b1e2 | Manages staff house and camp bookings. | 13 |
| Department Focal | e2fd380e-0472-42f6-aca1-d34abb659d2a | Verifies initial requests from their department. | 21 |
| Finance Clerk | f2c90f2b-f35d-40b0-a5bf-ae505c553973 | Verifies and processes expense claims for payment. | 14 |
| HOD | f9bce96c-9bc2-41b1-aa60-cf8febda571a | Head of Department, approves high-cost or international requests. | 24 |

## Permissions Replicated (59 Total)

### Access & Administration Permissions
- `access_debug_endpoints` - Can access debugging and testing endpoints
- `system_admin` - Full system administration access
- `manage_application_settings` - Can modify core application settings and configurations
- `manage_roles` - Can create, edit, and delete roles and assign permissions to them
- `manage_users` - Can create, edit, delete, and assign roles to users
- `view_system_settings` - Can view the system settings page
- `view_users` - Can view the user list
- `view_profiles` - Can view other users profile information
- `manage_own_profile` - Can edit and update own user profile

### Travel Request (TRF) Permissions
- `create_trf` - Can create new Travel Request Forms
- `view_all_trf` - Can view all TRFs across departments
- `view_own_requests` - Can view only their own submitted requests
- `view_pending_approvals` - Can view requests pending their approval
- `approve_trf_focal` - Can perform Department Focal approval for TRFs
- `approve_trf_manager` - Can perform Line Manager approval for TRFs
- `approve_trf_hod` - Can perform HOD approval for TRFs

### Claims Permissions
- `create_claims` - Can create new Expense Claims
- `view_all_claims` - Can view all Claims across departments
- `view_admin_claims` - Can access the Claims Admin module interface
- `approve_claims_focal` - Can perform Department Focal approval for Claims
- `approve_claims_manager` - Can perform Line Manager approval for Claims
- `approve_claims_hod` - Can perform HOD approval for Claims
- `process_claims` - Can process claims for payment (Finance Clerk)

### Visa Permissions
- `create_visa_requests` - Can create new visa application requests
- `view_visa_applications` - Can view visa applications (read-only)
- `view_admin_visa` - Can access the Visa Admin module interface
- `view_visa_reports` - Can view visa processing reports and statistics
- `approve_visa_focal` - Approve visa applications at department focal level
- `approve_visa_manager` - Approve visa applications at line manager level
- `approve_visa_hod` - Approve visa applications at HOD level
- `approve_visa_requests` - Can approve visa application requests
- `process_visa_applications` - Can manage visa applications (Visa Clerk)

### Transport Permissions
- `create_transport_requests` - Can create new transport/vehicle booking requests
- `view_all_transport` - Can view all transport requests across departments
- `view_admin_transport` - Can access the Transport Admin module interface
- `manage_transport_requests` - Can manage and assign transport bookings
- `approve_transport_focal` - Approve transport requests at department focal level
- `approve_transport_manager` - Approve transport requests at line manager level
- `approve_transport_hod` - Approve transport requests at HOD level
- `approve_transport_requests` - Can approve transport booking requests

### Accommodation Permissions
- `view_admin_accommodation` - Can access the Accommodation Admin module interface
- `manage_accommodation_bookings` - Can manage accommodation bookings
- `approve_accommodation_focal` - Approve accommodation requests at department focal level
- `approve_accommodation_manager` - Approve accommodation requests as Line Manager
- `approve_accommodation_hod` - Approve accommodation requests as HOD
- `approve_accommodation_requests` - Can approve accommodation booking requests

### Flight Permissions
- `view_admin_flights` - Can access the Flight Admin module interface
- `manage_flights` - Can manage flight bookings and flight admin interface
- `process_flights` - Can manage flight bookings (Ticketing Admin)

### Document & Notification Permissions
- `upload_documents` - Can upload supporting documents and files
- `manage_document_templates` - Can create and edit document templates
- `send_notifications` - Can send manual notifications to users
- `manage_notifications` - Manage notification settings and templates

### Reporting & Analytics Permissions
- `generate_admin_reports` - Can generate comprehensive admin reports and analytics
- `export_data` - Can export application data in various formats
- `view_activity_logs` - Can view user activity and system logs
- `view_dashboard_summary` - Can access dashboard summary statistics
- `view_sidebar_counts` - Can view notification counts and sidebar information
- `view_department_requests` - Can view requests from their department

## Key Role-Permission Mappings

### System Administrator (47 permissions)
Full access to all system features including:
- All approval permissions (focal, manager, HOD levels)
- All admin module views (claims, transport, visa, accommodation, flights)
- User and role management
- System configuration and settings
- Debug endpoints

### Department Focal (21 permissions)
First-level approval authority:
- Approve requests at focal level (TRF, claims, transport, visa, accommodation)
- Create all request types
- View pending approvals and department requests
- Send notifications

### Line Manager (20 permissions)
Mid-level approval authority:
- Approve requests at manager level (TRF, claims, transport, visa, accommodation)
- Create all request types
- View pending approvals
- Export data

### HOD (24 permissions)
Final approval authority:
- Approve requests at HOD level (TRF, claims, transport, visa, accommodation)
- Generate admin reports
- View all claims
- Export data
- Send notifications

### Requestor (9 permissions)
Basic user permissions:
- Create all request types (TRF, claims, transport, visa)
- View own requests
- Manage own profile
- Upload documents
- View dashboard summary

### Specialist Roles
- **Finance Clerk**: Process and verify expense claims
- **Visa Clerk**: Process visa applications
- **Transport Admin**: Manage transport bookings
- **Accommodation Admin**: Manage accommodation bookings
- **Ticketing Admin**: Manage flight bookings

## Frontend Integration

The roles and permissions are now available through the Django REST API:

- **Roles Endpoint**: `GET /api/roles/`
- **Permissions Endpoint**: `GET /api/permissions/`
- **Role Details**: `GET /api/roles/{id}/`

### System Settings Page
The Angular frontend's System Settings page should now display:

1. **Existing Roles Tab** (`/admin/settings/roles`)
   - Lists all 10 roles
   - Shows role name and description
   - Edit and delete functionality
   - View permissions assigned to each role

2. **Available System Permissions Tab** (`/admin/settings/permissions`)
   - Lists all 59 system permissions
   - Shows permission name and description
   - Can be assigned to roles

## Database Schema

### Tables Created/Modified
```sql
-- accounts_role table
CREATE TABLE accounts_role (
    id UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- accounts_permission table
CREATE TABLE accounts_permission (
    id UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- accounts_rolepermission table
CREATE TABLE accounts_rolepermission (
    id SERIAL PRIMARY KEY,
    role_id UUID NOT NULL REFERENCES accounts_role(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES accounts_permission(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);

-- accounts_user.role_id updated to UUID
ALTER TABLE accounts_user
    ALTER COLUMN role_id TYPE UUID USING NULL;
```

## Verification

To verify the migration was successful:

```sql
-- Count roles
SELECT COUNT(*) FROM accounts_role;
-- Expected: 10

-- Count permissions
SELECT COUNT(*) FROM accounts_permission;
-- Expected: 59

-- Count role-permission mappings
SELECT COUNT(*) FROM accounts_rolepermission;
-- Expected: 193

-- View permissions per role
SELECT r.name, COUNT(rp.permission_id) as permissions_count
FROM accounts_role r
LEFT JOIN accounts_rolepermission rp ON r.id = rp.role_id
GROUP BY r.id, r.name
ORDER BY r.name;
```

## Files Modified

1. `backend/accounts/models.py` - Updated Role and Permission models with UUID primary keys
2. `backend/accounts/migrations/0007_recreate_roles_permissions_with_uuid.py` - Schema migration
3. `backend/accounts/migrations/0008_populate_roles_permissions.py` - Data migration

## Next Steps

1. **Frontend Display**: The Angular System Settings page should now show:
   - All 10 roles under "Existing Roles"
   - All 59 permissions under "Available System Permissions"

2. **User Assignment**: Users can now be assigned roles through the user management interface

3. **Permission Checks**: Implement permission-based access control in both backend (Django) and frontend (Angular)

4. **Custom Roles**: System administrators can create custom roles and assign specific permissions

---

**Migration Date**: 2025-10-23
**Status**: ✅ Complete
**Total Roles**: 10
**Total Permissions**: 59
**Total Mappings**: 193
