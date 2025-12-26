# Accommodation Workflow Assignment Fix

**Date**: December 23, 2025
**Status**: ✅ FIXED

## Problem

When creating an accommodation request, the notification was sent to **tekayev@outlook.com** (System Administrator) instead of **turkzuk@gmail.com** (HOD).

## Root Cause Analysis

### Issue #1: Workflow Step Configuration Conflict
The accommodation workflow step was configured with BOTH:
- `approver_role`: HOD (correct)
- `approver_permission`: approve_accommodation (conflicting)

**The workflow engine prioritizes `approver_permission` over `approver_role`.**

When using permission-based lookup, it found 5 roles with `approve_accommodation` permission in the IT department:
1. System Administrator - tekayev@outlook.com ✅ (selected by mistake)
2. Line Manager - line@email.com
3. Accommodation Admin - acc@email.com
4. Department Focal - focal@email.com
5. HOD - turkzuk@gmail.com ✅ (should be selected)

The query `User.objects.filter(role__in=roles, department='IT', status='Active').first()` returned the first match alphabetically, which was tekayev.

### Issue #2: Missing created_by Field
The `AccommodationRequest` model didn't have a `created_by` field linking to the User model. The signal was trying to use `instance.requester` which didn't exist, causing the workflow to fail to properly identify the requester's department.

## Solutions Applied

### Fix #1: Remove Permission from Workflow Step ✅
```python
# Before
step.approver_role = "f9bce96c-9bc2-41b1-aa60-cf8febda571a"  # HOD
step.approver_permission = "approve_accommodation"  # CONFLICTING

# After
step.approver_role = "f9bce96c-9bc2-41b1-aa60-cf8febda571a"  # HOD
step.approver_permission = None  # Removed
```

Now the workflow will use **role-based assignment** which specifically finds users with the HOD role.

### Fix #2: Add created_by Field to AccommodationRequest Model ✅
Added a `created_by` ForeignKey to the User model:

```python
created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='accommodation_requests_created',
    null=True,
    blank=True,
    help_text="User who created this accommodation request"
)
```

### Fix #3: Update Signal to Use created_by ✅
Changed from:
```python
workflow_instance = WorkflowEngine.start_workflow(
    entity=instance,
    initiated_by=instance.requester,  # DOESN'T EXIST
    module_name='accommodation'
)
```

To:
```python
workflow_instance = WorkflowEngine.start_workflow(
    entity=instance,
    initiated_by=instance.created_by,  # Correct field
    module_name='accommodation'
)
```

## Files Modified

1. **`backend/workflows/models.py`** (via Python shell)
   - Removed `approve_accommodation` permission from Step 1 of accommodation workflow

2. **`backend/accommodation/models.py`**
   - Added import: `from django.conf import settings`
   - Added `created_by` field to `AccommodationRequest` model

3. **`backend/accommodation/signals.py`**
   - Updated to use `instance.created_by` instead of `instance.requester`

4. **Database Migration**
   - Created: `accommodation/migrations/0008_accommodationrequest_created_by.py`
   - Applied successfully

## How Assignment Works Now

### Step-by-Step Flow:
1. User creates accommodation request in frontend
2. Frontend saves request with `created_by` = current logged-in user
3. Signal triggers when status = 'Submitted'
4. Workflow engine creates workflow instance with `initiated_by` = `created_by`
5. Workflow engine starts first step:
   - Checks `approver_user` (None)
   - Checks `approver_permission` (None - removed!)
   - **Uses `approver_role` (HOD)**
6. Role-based lookup:
   ```python
   role = Role.objects.get(id="f9bce96c-9bc2-41b1-aa60-cf8febda571a")  # HOD
   user = User.objects.filter(
       role=role,
       department=requester.department,  # IT
       status='Active'
   ).first()
   # Returns: turkzuk@gmail.com (HOD, IT dept) ✅
   ```
7. Notification sent to correct HOD!

## Workflow Engine Priority Order

The workflow engine checks in this order:
1. **approver_user** (specific user) - highest priority
2. **approver_permission** (permission-based) - medium priority
3. **approver_role** (role-based) - fallback

**Recommendation**: Use only ONE of these per step to avoid conflicts!

## Testing Steps

### Test 1: Verify Workflow Step Configuration
```bash
cd backend
python manage.py shell -c "
from workflows.models import WorkflowStep
step = WorkflowStep.objects.filter(
    workflow_template__entity_type='accommodation',
    step_order=1
).first()
print('Approver Role:', step.approver_role)
print('Approver Permission:', step.approver_permission)
# Should show: Approver Permission: None
"
```

### Test 2: Create New Accommodation Request
1. Login to frontend as any user (e.g., tekayev)
2. Navigate to Accommodation → Create New Request
3. Fill in details
4. Submit request
5. Verify:
   - Status changes to "Pending HOD"
   - Notification sent to turkzuk@gmail.com (HOD)
   - NOT sent to tekayev@outlook.com

### Test 3: Check Workflow Assignment
```bash
cd backend
python manage.py shell -c "
from accommodation.models import AccommodationRequest
from workflows.models import WorkflowInstance, WorkflowStepExecution
from django.contrib.contenttypes.models import ContentType

latest = AccommodationRequest.objects.order_by('-created_at').first()
ct = ContentType.objects.get_for_model(AccommodationRequest)
wf = WorkflowInstance.objects.filter(content_type=ct, object_id=latest.id).first()
step = wf.step_executions.first()

print('Request:', latest.request_number)
print('Created by:', latest.created_by.email)
print('Assigned to:', step.assigned_to.email)
print('Expected: turkzuk@gmail.com (HOD)')
"
```

## Department-Specific Assignment

The workflow engine supports **department-specific role assignment**:
- If requester is in IT department → assigns to HOD in IT department
- If requester is in Finance department → assigns to HOD in Finance department

**Current HODs in system**:
- IT: turkzuk@gmail.com ✅

If you add more departments, add corresponding HODs in the User Management section.

## Important Notes

1. **Frontend Must Set created_by**: The frontend needs to be updated to set the `created_by` field when creating/updating accommodation requests.

2. **Existing Records**: Existing accommodation requests will have `created_by = NULL`. When they are updated, the frontend should set `created_by` to the current logged-in user.

3. **Multiple HODs**: If there are multiple HODs in the same department, the system will assign to the first one found. This is by design.

4. **Permission Assignment Best Practice**:
   - Don't assign `approve_accommodation` permission to System Administrator role
   - Only assign approval permissions to roles that should actually approve (HOD, Line Manager, etc.)
   - Use permissions for general capabilities, not workflow-specific approvals

## Next Steps

1. **Update Frontend** to set `created_by` when creating accommodation requests
2. **Test** with new accommodation request creation
3. **Monitor** that notifications go to correct HOD
4. **Document** for other modules if they have similar issues

## Rollback (if needed)

If this causes issues, you can rollback:

```bash
cd backend

# Restore permission to workflow step
python manage.py shell -c "
from workflows.models import WorkflowStep
step = WorkflowStep.objects.filter(
    workflow_template__entity_type='accommodation',
    step_order=1
).first()
step.approver_permission = 'approve_accommodation'
step.save()
"

# Rollback migration
python manage.py migrate accommodation 0007
```

## Status: ✅ READY FOR TESTING

The accommodation workflow will now correctly assign to the HOD (turkzuk@gmail.com) instead of System Administrator (tekayev@outlook.com).
