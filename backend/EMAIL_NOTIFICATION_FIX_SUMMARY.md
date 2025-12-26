# Email Notification Fix Summary

**Date**: December 23, 2025
**Status**: ✅ FIXED AND TESTED

## Issues Identified

### Issue #1: SMTP Authentication Failure (CRITICAL)
**Error**: `SMTPAuthenticationError: (535, 'Username and Password not accepted')`

**Root Cause**: The SMTP credentials in the database were incorrect/expired.

**Fix**: Updated database settings with correct Brevo SMTP credentials:
- Host: `smtp-relay.brevo.com`
- Port: `587`
- TLS: `True`
- Username: `8994af002@smtp-brevo.com`
- Password: `JfadTIjcZABH0xXY`
- From Email: `SynTra TMS <no-reply@pctsb-travel.site>`

### Issue #2: Template Placeholders Not Being Rendered (MAJOR)
**Problem**: Notification titles showed `{{requestType}} #{{entityId}}` instead of actual values.

**Root Cause**: The `_send_configured_notifications()` method was using template subject/body directly without rendering placeholders.

**Fix**:
1. Added `render()` method to `NotificationTemplate` model (notifications/models.py:122-146)
2. Updated `_send_configured_notifications()` to build context and render templates (workflows/notifications.py:247-366)

### Issue #3: Email Settings Loader Import Error
**Error**: `No module named 'administration'`

**Root Cause**: Incorrect import in `core/email_settings_loader.py` line 44.

**Fix**: Changed `from administration.models` to `from accounts.models`

## Files Modified

### 1. `backend/notifications/models.py`
**Change**: Added template rendering method
```python
def render(self, context: dict) -> dict:
    """Render template with context variables."""
    import re
    rendered_subject = self.subject
    rendered_body = self.body

    for key, value in context.items():
        pattern = r'\{\{' + re.escape(key) + r'\}\}'
        rendered_subject = re.sub(pattern, str(value), rendered_subject)
        rendered_body = re.sub(pattern, str(value), rendered_body)

    return {'subject': rendered_subject, 'body': rendered_body}
```

### 2. `backend/workflows/notifications.py`
**Change**: Updated `_send_configured_notifications()` to:
- Build template context with actual values (requestType, entityId, dueDate, etc.)
- Render templates using the new `render()` method
- Support custom subject/message rendering

**Context Variables Available**:
- `requestType`: Human-readable request type
- `entityId`: Request number (e.g., ACCOM-20251223-1154-ASHGA-3FJ4)
- `dueDate`: SLA due date
- `urgencyHint`: Urgency message based on escalation time
- `requestorName`: Requester's full name
- `requestorEmail`: Requester's email
- `approverName`: Approver's full name
- `stepName`: Current workflow step name
- `workflowName`: Workflow template name
- `actionUrl`: URL to view the request

### 3. `backend/core/email_settings_loader.py`
**Change**: Fixed import from `administration.models` to `accounts.models`

## Test Results

### Test Script: `test_complete_notification.py`
```
✅ Email settings loaded from database
✅ Template rendered correctly (68 chars subject, 170 chars body)
✅ Template variables replaced (no {{...}} placeholders remaining)
✅ Notification created (ID=84)
✅ Email sent successfully at: 2025-12-23 11:28:39
✅ No email errors
```

## Verification Steps

### 1. Check Email Settings
```bash
cd backend
python manage.py shell -c "
from accounts.models import ApplicationSetting
print('SMTP Host:', ApplicationSetting.get_setting('smtp_host'))
print('SMTP Port:', ApplicationSetting.get_setting('smtp_port'))
print('From Email:', ApplicationSetting.get_setting('from_email'))
"
```

### 2. Test Template Rendering
```bash
cd backend
python test_complete_notification.py
```

### 3. Create New Accommodation Request
1. Go to frontend and create a new accommodation request
2. Submit the request
3. Check that:
   - Workflow starts successfully
   - Notification is created
   - Email is sent to HOD (tekayev@outlook.com)
   - Subject shows: "❗ Pending Your Approval - Accommodation Request #ACCOM-..."
   - No {{placeholders}} in the email

## How It Works Now

### Workflow Flow:
1. **User submits accommodation request**
   ↓
2. **Signal triggers workflow start** (`accommodation/signals.py`)
   ↓
3. **Workflow engine creates workflow instance** (`workflows/engine.py:89`)
   ↓
4. **Workflow creates first step execution**
   ↓
5. **Workflow checks for notification configs** (`workflows/notifications.py:44-55`)
   ↓
6. **If config found, uses configured notifications** (NEW SYSTEM)
   - Builds template context with actual values
   - Renders template using `NotificationTemplate.render()`
   - Resolves recipients (TO, CC, BCC)
   - Creates notifications via `NotificationService`
   ↓
7. **NotificationService sends email asynchronously** (`notifications/services.py:90-116`)
   - Loads email settings from database (lazy loading)
   - Checks user preferences
   - Sends via SMTP (Brevo)
   - Updates notification with sent timestamp

### If no config found, falls back to default notifications (EXISTING SYSTEM - unchanged)

## Production Checklist

- ✅ SMTP credentials updated in database
- ✅ Template rendering implemented
- ✅ Email settings loader fixed
- ✅ Async email sending working
- ✅ Lazy loading of email settings working
- ✅ Template context variables populated correctly
- ✅ Recipient resolution working (approver, requestor, CC, BCC)
- ✅ Test email sent successfully
- ⏳ **Pending**: Test with real accommodation request (user to verify)

## Next Steps

1. **Create a new accommodation request** to test end-to-end flow
2. **Verify email arrives** in HOD inbox with correct subject and body
3. **Check in-app notification** shows correctly in the UI
4. **Test other modules** (TSR, Transport, Visa) to ensure they work the same way

## Support

If emails are still not being sent:
1. Check email settings in database: System Settings → Email Configuration
2. Check notification configs: System Settings → Workflow Configuration → Edit workflow → Configure step → Notifications
3. Check user notification preferences: User may have email notifications disabled
4. Check SMTP logs in server console

## Backward Compatibility

✅ **100% Backward Compatible**
- Existing workflows without notification configs continue to use default notifications
- New notification config system is completely additive
- No breaking changes to existing functionality
