# 📧 Notification Templates Documentation

**Last Updated:** 2026-01-06
**Version:** 2.0 (Improved Templates)

---

## Overview

The TMS application uses a template-based notification system for sending professional email notifications to users. All templates support HTML formatting and variable substitution using `{{variableName}}` syntax.

### Key Features:
- ✅ 10 Professional email templates
- ✅ HTML email support with plain text fallback
- ✅ Async background email sending
- ✅ Variable substitution with context data
- ✅ Backward compatibility with legacy variable names

---

## Template List

| Template Name | Event Type | Recipients | Purpose |
|--------------|------------|------------|---------|
| `workflow_started_requestor` | WORKFLOW_STARTED | Requestor | Confirms workflow submission |
| `approval_required` | APPROVAL_REQUESTED | Approver | Requests approval action |
| `step_assigned` | STEP_ASSIGNED | Processor | Task assignment notification |
| `approval_reminder` | APPROVAL_REMINDER | Approver | Reminder for pending approvals |
| `escalation_required` | ESCALATION | Manager | Escalation alert for delays |
| `request_resubmitted` | REQUEST_RESUBMITTED | Approver | Resubmission notification |
| `workflow_rejected` | WORKFLOW_REJECTED | Requestor | Rejection notification |
| `workflow_completed` | WORKFLOW_APPROVED | Requestor | Approval confirmation |
| `new_comment_added` | COMMENT_ADDED | Mentioned users | Comment notification |
| `delegation_confirmed` | APPROVAL_DELEGATED | Delegate | Delegation confirmation |

---

## Template Variables Reference

### 1. workflow_started_requestor

**Purpose:** Confirm to requester that their workflow has been submitted

**Variables:**
- `requestorName` - Full name of the person who submitted the request
- `requestType` - Type of request (e.g., "Visa Request", "Accommodation")
- `entityId` - Unique identifier for the request
- `approverName` - Name of the first approver
- `actionUrl` - URL to view the request

**Example Usage:**
```python
NotificationService.create_notification(
    user=workflow_instance.initiated_by,
    title="Workflow Started",
    message="Your request has been submitted",
    event_type=event_type,
    additional_data={
        'requestorName': workflow_instance.initiated_by.get_full_name(),
        'requestType': 'Visa Request',
        'entityId': 'VISA-2026-001',
        'approverName': 'Jane Smith',
        'actionUrl': '/visa/123',
    },
    send_email=True
)
```

---

### 2. approval_required

**Purpose:** Notify approver that their action is required

**Variables:**
- `approverName` - Full name of the approver
- `requestType` - Type of request
- `entityId` - Request identifier
- `requestorName` - Person who submitted the request
- `dueDate` - Formatted due date (e.g., "January 10, 2026 at 05:00 PM")
- `urgencyHint` - Priority indicator (e.g., "High priority")
- `actionUrl` - URL to review and approve

**Example Usage:**
```python
NotificationService.create_notification(
    user=approver,
    title="Approval Required",
    message="Please review the request",
    event_type=event_type,
    additional_data={
        'approverName': approver.get_full_name(),
        'requestType': 'Accommodation',
        'entityId': 'ACCOM-2026-001',
        'requestorName': 'John Doe',
        'dueDate': 'January 10, 2026 at 05:00 PM',
        'urgencyHint': 'High priority',
        'actionUrl': '/accommodation/456',
    },
    send_email=True
)
```

---

### 3. step_assigned

**Purpose:** Notify user of task assignment

**Variables:**
- `approverName` - Name of assigned person
- `requestType` - Type of request
- `entityId` - Request identifier
- `requestorName` - Original requestor
- `processorHint` - Task description
- `actionUrl` - URL to view task

---

### 4. approval_reminder

**Purpose:** Remind approver of pending approval

**Variables:**
- `approverName` - Name of approver
- `reminderType` - Type of reminder (e.g., "Gentle Reminder", "Urgent Reminder")
- `requestType` - Type of request
- `entityId` - Request identifier
- `reminderMessage` - Custom reminder message
- `statusMessage` - Current status (e.g., "has been waiting for 2 days")
- `actionUrl` - URL to take action

---

### 5. escalation_required

**Purpose:** Notify manager of escalated request

**Variables:**
- `managerName` - Name of manager
- `requestType` - Type of request
- `entityId` - Request identifier
- `requestorName` - Original requestor
- `approverName` - Current approver who has delay
- `assignedDate` - When request was assigned
- `hoursNoAction` - Hours without action
- `actionUrl` - URL to intervene

---

### 6. request_resubmitted

**Purpose:** Notify approver of updated/resubmitted request

**Variables:**
- `approverName` - Name of approver
- `entityId` - Request identifier
- `requestorName` - Person who resubmitted
- `changesSummary` - Summary of changes made
- `actionUrl` - URL to review changes

---

### 7. workflow_rejected

**Purpose:** Notify requestor of rejection

**Variables:**
- `requestorName` - Name of requestor
- `requestType` - Type of request
- `entityId` - Request identifier
- `approverName` - Person who rejected
- `rejectionReason` - Reason for rejection
- `actionUrl` - URL to revise request

---

### 8. workflow_completed

**Purpose:** Notify requestor of successful approval

**Variables:**
- `requestorName` - Name of requestor
- `requestType` - Type of request
- `entityId` - Request identifier
- `processorName` - Person who finalized
- `completionDate` - Formatted completion date
- `completionDetails` - Summary of completion
- `actionUrl` - URL to view details

---

### 9. new_comment_added

**Purpose:** Notify users of new comments

**Variables:**
- `userName` - Name of recipient
- `entityId` - Request identifier
- `commenterName` - Person who commented
- `commentPreview` - Preview of comment text
- `mentionMessage` - Message if user was mentioned
- `mentionTag` - Tag text (e.g., " (@John)") - optional
- `actionUrl` - URL to view comment

---

### 10. delegation_confirmed

**Purpose:** Notify delegate of new assignment

**Variables:**
- `approverName` - Name of new approver (delegate)
- `delegatorName` - Person who delegated
- `requestType` - Type of request
- `entityId` - Request identifier
- `actionUrl` - URL to review request

---

## How to Use Templates in Code

### Method 1: Using WorkflowNotifications Helper

The recommended way is to use the `WorkflowNotifications` helper class:

```python
from workflows.notifications import WorkflowNotifications

# When workflow starts
WorkflowNotifications.notify_workflow_started(workflow_instance)

# When step is approved
WorkflowNotifications.notify_step_approved(step_execution)

# When step is rejected
WorkflowNotifications.notify_step_rejected(step_execution)

# When step is delegated
WorkflowNotifications.notify_step_delegated(step_execution, new_assignee)

# When workflow completes
WorkflowNotifications.notify_workflow_completed(workflow_instance)
```

### Method 2: Direct NotificationService Usage

For custom notifications:

```python
from notifications.services import NotificationService
from notifications.models import NotificationEventType

# Get event type
event_type = NotificationEventType.objects.get(name='APPROVAL_REQUESTED')

# Create notification with template variables
NotificationService.create_notification(
    user=target_user,
    title="Custom Title",  # Overridden by template subject if template exists
    message="Custom Message",  # Overridden by template body if template exists
    event_type=event_type,
    priority='high',
    action_url='/path/to/resource',
    additional_data={
        'approverName': 'John Doe',
        'requestType': 'Visa Request',
        'entityId': 'VISA-123',
        # ... all required variables for the template
    },
    send_email=True
)
```

### Method 3: Using Configured Notifications

For workflow step notifications with configuration:

```python
from workflows.notifications import WorkflowNotifications

# This method reads WorkflowStepNotificationConfig and sends
# notifications based on configuration
WorkflowNotifications.trigger_configured_notifications(
    step_execution,
    event_type='approval'  # or 'rejection', 'assignment', 'workflow_completed', etc.
)
```

---

## Context Builder

The `_build_notification_context()` method in `WorkflowNotifications` automatically builds context with all required variables:

```python
context = WorkflowNotifications._build_notification_context(step_execution)

# Returns dictionary with:
# - requestorName, approverName, processorName, userName
# - requestType, entityId
# - dueDate, completionDate (formatted nicely)
# - urgencyHint, processorHint, completionDetails, rejectionReason
# - Legacy variables for backward compatibility
```

---

## Date Formatting

Dates are automatically formatted in a user-friendly way:

```python
# Instead of: "2026-01-10 17:00:00"
# Use: "January 10, 2026 at 05:00 PM"

from django.utils import timezone
due_date = sla_due_date.strftime('%B %d, %Y at %I:%M %p')
```

---

## Testing Templates

### Template Rendering Test

```bash
cd backend
python test_notification_templates.py
```

This tests:
- All 10 templates render correctly
- No unreplaced variables ({{var}})
- All expected variables are present

### Integration Test

```bash
cd backend
python test_workflow_notifications_integration.py
```

This tests:
- Context builder includes all variables
- Notification methods pass correct data
- Template-code variable mapping is correct

---

## Troubleshooting

### Issue: Variables showing as {{variableName}} in email

**Cause:** Variable not passed in `additional_data`

**Solution:** Ensure all required variables are included:

```python
# ❌ WRONG - missing variables
NotificationService.create_notification(
    user=user,
    additional_data={'entityId': '123'},  # Missing other variables!
    send_email=True
)

# ✅ CORRECT - all variables included
NotificationService.create_notification(
    user=user,
    additional_data={
        'requestorName': 'John Doe',
        'requestType': 'Visa Request',
        'entityId': '123',
        'approverName': 'Jane Smith',
        'actionUrl': '/visa/123',
    },
    send_email=True
)
```

### Issue: Email not sent

**Possible causes:**
1. User has email notifications disabled in preferences
2. User has no email address
3. SMTP configuration issue
4. Email notifications disabled globally

**Check:**
```python
# Check user preferences
user.notification_preferences.email_notifications_enabled

# Check global setting
from accounts.models import ApplicationSetting
ApplicationSetting.get_setting('enable_email_notifications', True)

# Check notification error
notification.email_error  # Contains error message if email failed
```

### Issue: Wrong template used

**Cause:** Event type mismatch

**Solution:** Ensure correct event type:

```python
# Get the correct event type
event_type = NotificationEventType.objects.get(name='APPROVAL_REQUESTED')

# Event type determines which template is used
# Each template is linked to a specific event type
```

---

## Migration History

- **0002_setup_notification_templates.py** - Initial templates (brief, informal)
- **0003_cleanup_unused_event_types.py** - Cleanup unused event types
- **0004_update_notification_templates.py** - Improved professional templates ✅ (Current)

---

## Best Practices

### 1. Always Pass All Required Variables

```python
# Check template.variables_available to see what's needed
template = NotificationTemplate.objects.get(name='approval_required')
print(template.variables_available)
# Output: ['approverName', 'requestType', 'entityId', ...]
```

### 2. Use Formatted Dates

```python
# ✅ GOOD - User-friendly
'dueDate': due_date.strftime('%B %d, %Y at %I:%M %p')

# ❌ BAD - Machine format
'dueDate': str(due_date)
```

### 3. Use Helper Methods

```python
# ✅ GOOD - Uses helper with all variables included
WorkflowNotifications.notify_workflow_started(workflow_instance)

# ❌ BAD - Manual notification creation, error-prone
NotificationService.create_notification(...)
```

### 4. Test Before Deploying

Always run the test suite after making changes:

```bash
python test_notification_templates.py
python test_workflow_notifications_integration.py
```

---

## Backward Compatibility

The system maintains backward compatibility with legacy variable names:

| New Variable | Legacy Alternatives |
|--------------|-------------------|
| `requestorName` | `requester`, `requesterName` |
| `approverName` | `assigned_to`, `assignedTo` |
| `requestType` | `request_type`, `entity_type` |
| `entityId` | `entity_id` |
| `dueDate` | `sla_due_date`, `slaDueDate` |

Both new and legacy names are available in the context, so existing code continues to work.

---

## Support

For questions or issues:
1. Check this documentation
2. Review test files for examples
3. Check migration files for template content
4. Review `backend/workflows/notifications.py` for implementation

---

**Documentation maintained by:** TMS Development Team
**Last reviewed:** 2026-01-06
