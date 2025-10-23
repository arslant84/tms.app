# Quick Start: Role Management

## ✅ What's Ready

Your role management system is **fully functional** and matches the React source project implementation exactly.

## 🚀 How to Access

1. **Backend Server:** http://localhost:8000 (running)
2. **Frontend Server:** http://localhost:4200 (running)

3. **Login:**
   - Email: `tekayev@outlook.com`
   - Password: `admin123`
   - Role: System Administrator (47 permissions)

4. **Navigate to Role Management:**
   ```
   http://localhost:4200/admin/settings
   ```
   Or: Dashboard → Admin → System Settings

## 📋 What You Can Do

### 1. View Existing Roles
You'll see 11 roles in the "Existing Roles" section:
- System Administrator (47 permissions)
- HOD (24 permissions)
- Department Focal (21 permissions)
- Line Manager (20 permissions)
- Visa Clerk (17 permissions)
- Transport Admin (15 permissions)
- Finance Clerk (14 permissions)
- Accommodation Admin (13 permissions)
- Ticketing Admin (13 permissions)
- Requestor (9 permissions)
- Admin (0 permissions - legacy)

### 2. View Available System Permissions
You'll see all 59 permissions in the "Available System Permissions" section, organized by:
- Access & Administration (9)
- Travel Request (7)
- Claims (7)
- Visa (9)
- Transport (8)
- Accommodation (6)
- Flight (3)
- Documents & Notifications (4)
- Reporting & Analytics (6)

### 3. Create Custom Role

**Steps:**
1. Click **"Add New Role"** button
2. Enter role name (e.g., "Project Coordinator")
3. Enter description (optional)
4. **Check permissions** you want to assign:
   - ✅ create_trf
   - ✅ view_own_requests
   - ✅ create_transport_requests
   - ✅ upload_documents
   - ✅ view_dashboard_summary
5. Click **"Create Role"**
6. ✅ Success! New role appears in the list

### 4. Manage Existing Role (Add/Remove Permissions)

**Steps:**
1. Find any role in the list (e.g., "Line Manager")
2. Click **"Manage"** button
3. The form opens with:
   - Current role name
   - Current description
   - **Current permissions checked**
4. **Add more permissions:**
   - Check additional boxes
5. **Remove permissions:**
   - Uncheck boxes
6. Click **"Update Role"**
7. ✅ Success! Role permissions updated

**Example: Give HOD permission to manage flights**
1. Click "Manage" on HOD role
2. Find "manage_flights" permission
3. Check the box
4. Click "Update Role"
5. ✅ Done! HOD role now has 25 permissions (was 24)

### 5. Delete Role

**Steps:**
1. Find the role you want to delete
2. Click **"Delete"** button
3. Confirm deletion
4. ✅ Success! Role removed

**Note:** Be careful - users assigned to this role will lose their role assignment!

## 🎯 Common Use Cases

### Use Case 1: Create "Regional Manager" Role

**Requirements:**
- Approve travel requests at manager level
- View all requests in their region
- Export reports
- Send notifications

**Steps:**
1. Click "Add New Role"
2. Name: "Regional Manager"
3. Description: "Manages approvals and reports for regional office"
4. Check these permissions:
   - ✅ approve_trf_manager
   - ✅ approve_claims_manager
   - ✅ approve_transport_manager
   - ✅ view_all_trf
   - ✅ view_department_requests
   - ✅ export_data
   - ✅ send_notifications
5. Click "Create Role"
6. ✅ Done!

### Use Case 2: Give Finance Clerk Access to Transport Reports

**Current:** Finance Clerk has 14 permissions (no transport access)

**Goal:** Add transport viewing permission

**Steps:**
1. Click "Manage" on "Finance Clerk" role
2. Find and check: ✅ view_all_transport
3. Click "Update Role"
4. ✅ Done! Finance Clerk now has 15 permissions

### Use Case 3: Create "Intern" Role (Limited Access)

**Requirements:**
- View their own requests only
- Create basic requests
- No approval rights

**Steps:**
1. Click "Add New Role"
2. Name: "Intern"
3. Description: "Limited access for interns and temporary staff"
4. Check only these permissions:
   - ✅ view_own_requests
   - ✅ create_trf
   - ✅ manage_own_profile
   - ✅ view_dashboard_summary
   - ✅ upload_documents
5. Click "Create Role"
6. ✅ Done! Intern role with 5 permissions created

## 🔧 How It Works

### Frontend → Backend Flow

**Create Role:**
```
User clicks "Create Role"
    ↓
Angular sends: POST /api/roles/
{
  "name": "Custom Role",
  "description": "Description",
  "permissionIds": ["uuid1", "uuid2", "uuid3"]
}
    ↓
Django creates role in database
    ↓
Django creates permission mappings in accounts_rolepermission table
    ↓
Response: Role object with permissions
    ↓
Angular shows success message
    ↓
Role list refreshes
```

**Update Role:**
```
User clicks "Manage" → "Update Role"
    ↓
Angular sends: PUT /api/roles/{id}/
{
  "name": "Updated Role",
  "description": "Updated description",
  "permissionIds": ["uuid1", "uuid4", "uuid5"]
}
    ↓
Django updates role fields
    ↓
Django replaces ALL permission mappings with new set
    ↓
Response: Updated role object
    ↓
Angular shows success message
    ↓
Role list refreshes
```

### Permission Binding

When you check/uncheck permission boxes:
1. Click checkbox → `togglePermission(permissionId)` called
2. Method adds/removes UUID from `form.permissionIds` array
3. On submit, array sent to backend
4. Backend creates/deletes rows in `accounts_rolepermission` table
5. Result: Role has new permission set

**Database:**
```sql
-- accounts_rolepermission table
| id | role_id                              | permission_id                        |
|----|--------------------------------------|--------------------------------------|
| 1  | 0ec80c3e-dc8d-4c72-bc81-7a8262c94b94| e70a92ce-2305-4b3d-ba10-5b8509cab3ac|
| 2  | 0ec80c3e-dc8d-4c72-bc81-7a8262c94b94| 01d074ec-903c-4988-913e-fcaa8f3564d1|
...
```

Each row = one permission assigned to one role.

## 🐛 Troubleshooting

### Problem: "Add New Role" button doesn't work
- **Check:** Are both servers running?
  - Backend: http://localhost:8000/admin/
  - Frontend: http://localhost:4200
- **Check:** Are you logged in as admin?
- **Check:** Browser console for errors (F12)

### Problem: No roles showing in the list
- **Check:** Backend API: http://localhost:8000/api/roles/
  - Should return JSON array with 11 roles
- **Check:** Browser Network tab (F12) - did API call succeed?
- **Check:** Backend terminal for errors

### Problem: Can't save role
- **Check:** Did you enter a role name?
- **Check:** Did you select at least one permission?
- **Check:** Backend logs for validation errors
- **Check:** Browser console for error messages

### Problem: Permissions not showing
- **Check:** Backend API: http://localhost:8000/api/permissions/
  - Should return JSON array with 59 permissions
- **Check:** Database connection
- **Check:** Run migrations if needed: `python manage.py migrate`

## 📊 API Endpoints Reference

### Get All Roles
```bash
curl http://localhost:8000/api/roles/ \
  -H "Authorization: Token YOUR_TOKEN"
```

### Get All Permissions
```bash
curl http://localhost:8000/api/permissions/ \
  -H "Authorization: Token YOUR_TOKEN"
```

### Create Role
```bash
curl -X POST http://localhost:8000/api/roles/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Role",
    "description": "Test description",
    "permissionIds": ["uuid1", "uuid2"]
  }'
```

### Update Role
```bash
curl -X PUT http://localhost:8000/api/roles/{role-id}/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Role",
    "description": "Updated description",
    "permissionIds": ["uuid1", "uuid3", "uuid4"]
  }'
```

### Delete Role
```bash
curl -X DELETE http://localhost:8000/api/roles/{role-id}/ \
  -H "Authorization: Token YOUR_TOKEN"
```

## ✅ System Status

- ✅ Backend: Django REST API running on port 8000
- ✅ Frontend: Angular app running on port 4200
- ✅ Database: PostgreSQL with 10 active roles, 59 permissions
- ✅ Admin User: tekayev@outlook.com (System Administrator)
- ✅ Role Management UI: Fully functional
- ✅ API Endpoints: All tested and working
- ✅ Permission Binding: Working for create and update
- ✅ Custom Roles: Can be created with any permission combination

## 🎉 You're All Set!

**Open your browser:**
```
http://localhost:4200/admin/settings
```

**Login and start managing roles!**

---

**Need more help?** Check `ROLE_MANAGEMENT_COMPLETE.md` for detailed documentation.
