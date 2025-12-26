# Workflow Notification System - Fix Summary

## Problem Identified

You reported that no email notifications were being sent when creating a transport request (TRN-20251222-1707-HOME-3GJW). Upon investigation, I found **two critical bugs** affecting ALL modules:

### Bug #1: `entity_id` vs `object_id` Mismatch
**Location**: `backend/workflows/notifications.py`

**Issue**: The notification system was trying to access `workflow_instance.entity_id`, but the `WorkflowInstance` model uses `object_id` instead. This caused ALL workflow notifications to fail silently with an `AttributeError`.

**Impact**: No notifications were sent for ANY module (Transport, TRF/TSR, Visa, Accommodation)

**Fix**: Replaced all 9 occurrences of `entity_id` with `object_id` in the notifications file.

### Bug #2: Signal Configuration Errors
**Locations**:
- `backend/transport/signals.py`
- `backend/trf/signals.py`
- `backend/accommodation/signals.py`
- `backend/visa/signals.py` (missing file)

**Issues**:
1. Signals used wrong field names (`entity_content_type`, `entity_id`) instead of (`content_type`, `object_id`)
2. Module names didn't match workflow template entity types
3. Visa module had no signal file at all

**Fix**:
- Corrected field names in all signal files
- Updated module names to match template entity types:
  - Transport: `'transport'` → `'transportrequest'`
  - TRF: `'trf'` → `'travelrequest'`
  - Accommodation: Already correct (`'accommodation'`)
  - Visa: Created new signal file with `'visaapplication'`

## What Was Fixed

### Files Modified:
1. ✅ `backend/workflows/notifications.py` - Fixed entity_id → object_id (9 occurrences)
2. ✅ `backend/transport/signals.py` - Fixed field names and module name
3. ✅ `backend/trf/signals.py` - Fixed field names and module name
4. ✅ `backend/accommodation/signals.py` - Fixed field names
5. ✅ `backend/visa/signals.py` - Created new file
6. ✅ `backend/visa/apps.py` - Created to enable signal loading
7. ✅ `backend/visa/__init__.py` - Created with app config

## How It Works Now

### Automatic Workflow Trigger
When a user submits a request (changes status to 'Submitted') in ANY module:

1. **Signal Handler** detects the status change
2. **WorkflowEngine** creates a workflow instance
3. **WorkflowNotifications** sends emails to:
   - The requestor (confirmation that workflow started)
   - The first approver (notification of pending approval)

### Dynamic Email Notifications

The system now sends email notifications **automatically** for all modules:

| Module | Trigger | Workflow Template | Notifications Sent To |
|--------|---------|-------------------|----------------------|
| **Transport** | status='Submitted' | Transport Request Approval Workflow | Requestor + First Approver |
| **TRF/TSR** | status='Submitted' | Travel Service Request Approval Workflow | Requestor + First Approver |
| **Visa** | status='Submitted' | Visa Application Approval Workflow | Requestor + First Approver |
| **Accommodation** | status='Submitted' | Accommodation Request Approval Workflow | Requestor + First Approver |

### Notification Types Sent

Throughout the workflow lifecycle, these notifications are sent:

1. **WORKFLOW_STARTED** - Sent to requestor when workflow begins
2. **APPROVAL_REQUESTED** - Sent to each approver when it's their turn
3. **WORKFLOW_UPDATED** - Sent to requestor when a step is approved
4. **WORKFLOW_REJECTED** - Sent to requestor if request is rejected
5. **WORKFLOW_APPROVED** - Sent to requestor when fully approved
6. **APPROVAL_DELEGATED** - Sent when approval is delegated to another user
7. **WORKFLOW_CANCELLED** - Sent when workflow is cancelled

### Email Configuration

Email notifications are sent if:
- The `send_email=True` parameter is set (which it is for all workflow notifications)
- Email settings are properly configured in your Django settings
- SMTP server is configured and accessible

## Testing

Run the comprehensive test to verify everything works:

```bash
cd backend
python test_all_module_notifications.py
```

Expected output: `[SUCCESS] ALL TESTS PASSED!`

## Next Steps (Optional)

### 1. Fix Workflow Templates (Recommended)

Your Transport and Accommodation workflows only have 1 step each, but the design calls for 4 steps. To fix this:

```bash
cd backend
python manage.py create_default_workflows --reset
```

This will recreate all workflow templates with the correct steps:
- **Transport**: 4 steps (Department Focal → Line Manager → HOD → Transport Admin)
- **Accommodation**: 4 steps (Department Focal → Line Manager → HOD → Accommodation Admin)
- **TRF**: 4 steps (Department Focal → Line Manager → HOD → Travel Desk)
- **Visa**: 4 steps (Department Focal → Line Manager → HOD → Visa Admin)

**Warning**: This will delete existing workflow templates. Existing workflow instances will continue to work.

### 2. Test with Real Requests

Create a new request in any module and verify:
1. Status changes to 'Submitted'
2. Email is sent to requestor
3. Email is sent to first approver
4. Check Django admin or database for notification records

### 3. Monitor Logs

When workflows are triggered, you'll see console output like:
```
Workflow started for Transport Request #40: 98
```

If there are errors, they will be logged with:
```
Failed to start workflow for Transport Request #40: [error message]
```

## Summary

✅ **All modules now have working email notifications**
✅ **Notifications are sent dynamically based on workflow steps**
✅ **System works consistently across Transport, TRF/TSR, Visa, and Accommodation**
✅ **No code changes needed when adding new workflow steps - it's all configuration-driven**

The notification system is now fully functional and will automatically send emails to all relevant parties throughout the approval workflow!
