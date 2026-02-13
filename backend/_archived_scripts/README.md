# Archived Scripts

This directory contains one-time migration and fix scripts that have already been executed and are kept for historical reference only.

## Archived Date: 2026-01-09

### Scripts

1. **audit_all_users_permissions.py**
   - Purpose: One-time audit of all users and roles to find permission inconsistencies
   - Status: Completed
   - Safe to delete after: 2026-03-01

2. **convert_workflows_to_permissions.py** & **convert_workflows_to_permissions_v2.py**
   - Purpose: Migrated workflow approver_role to approver_permission system
   - Status: v2 is the final version, v1 kept for reference
   - Safe to delete after: 2026-03-01

3. **fix_unassigned_workflow_steps.py**
   - Purpose: Fixed workflow steps with unassigned approvers
   - Status: Completed
   - Safe to delete after: 2026-03-01

4. **fix_view_all_permissions.py**
   - Purpose: Fixed "view all" permissions inconsistencies
   - Status: Completed
   - Safe to delete after: 2026-03-01

5. **link_bookings_to_requests.py**
   - Purpose: Linked existing flight/hotel bookings to travel requests
   - Status: Completed
   - Safe to delete after: 2026-03-01

6. **workflowsmodels.py**
   - Purpose: Empty file, possibly created by accident
   - Status: Not used
   - Safe to delete: Immediately

## Important

**DO NOT RUN THESE SCRIPTS AGAIN** - They were designed for one-time fixes and may cause data inconsistencies if run multiple times.

If you need similar functionality in the future, convert the logic to Django management commands in `core/management/commands/`.
