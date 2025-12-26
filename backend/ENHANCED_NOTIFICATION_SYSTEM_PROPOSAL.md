# Enhanced Notification Configuration System - Proposal

## Current Issues

### 1. Email Notifications Not Working
**Status**: ✓ FIXED

**Problems Found**:
- Unicode encoding errors from emoji characters (✓ Fixed)
- Incorrect workflow step assignment logic
  - Using `approver_permission` which matched multiple roles
  - Engine selected first user with permission (often the requestor)
  - Should use `approver_role` for specific role assignment

**Solutions Implemented**:
- Removed all emoji characters from code (replaced with ASCII)
- Updated Transport workflow to use `approver_role` instead of `approver_permission`
- Fixed workflow instance #101 to assign HOD (turkzuk@gmail.com)
- Resent notifications to correct recipients

### 2. Lack of Notification Configuration

**Current Limitations**:
- No way to configure WHO receives notifications for each workflow step
- No CC/BCC support
- Cannot select which notification template to use
- Notifications are hardcoded in the workflow engine
- No flexibility for different notification scenarios

## Proposed Enhanced System

### Architecture Overview

```
Workflow Step → Notification Configuration → Recipients + Template → Email Sent
```

### Database Schema Changes

#### 1. New Model: `WorkflowStepNotificationConfig`

Configures notifications for each workflow step.

```python
class WorkflowStepNotificationConfig(models.Model):
    """
    Configuration for notifications sent at each workflow step.
    Allows fine-grained control over who receives what notifications.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    workflow_step = models.ForeignKey(
        'WorkflowStep',
        on_delete=models.CASCADE,
        related_name='notification_configs'
    )

    # Notification trigger
    trigger_event = models.CharField(
        max_length=50,
        choices=[
            ('step_created', 'When Step is Created'),
            ('step_approved', 'When Step is Approved'),
            ('step_rejected', 'When Step is Rejected'),
            ('step_delegated', 'When Step is Delegated'),
            ('step_escalated', 'When Step is Escalated'),
        ],
        help_text="When should this notification be sent?"
    )

    # Template selection
    notification_template = models.ForeignKey(
        'notifications.NotificationTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Email template to use for this notification"
    )

    # Primary recipients (TO)
    recipient_type = models.CharField(
        max_length=50,
        choices=[
            ('approver', 'Step Approver'),
            ('requestor', 'Original Requestor'),
            ('next_approver', 'Next Step Approver'),
            ('role', 'Specific Role'),
            ('user', 'Specific User'),
            ('department_head', 'Department Head'),
        ],
        help_text="Who should receive this notification (TO)"
    )

    # For role-based recipients
    recipient_roles = models.ManyToManyField(
        'accounts.Role',
        blank=True,
        related_name='workflow_notification_recipients',
        help_text="Roles to notify (if recipient_type='role')"
    )

    # For user-based recipients
    recipient_users = models.ManyToManyField(
        'accounts.User',
        blank=True,
        related_name='workflow_notification_recipients',
        help_text="Specific users to notify (if recipient_type='user')"
    )

    # CC recipients
    cc_requestor = models.BooleanField(
        default=False,
        help_text="CC the original requestor"
    )
    cc_previous_approvers = models.BooleanField(
        default=False,
        help_text="CC all previous approvers in the workflow"
    )
    cc_roles = models.ManyToManyField(
        'accounts.Role',
        blank=True,
        related_name='workflow_notification_cc',
        help_text="Additional roles to CC"
    )
    cc_users = models.ManyToManyField(
        'accounts.User',
        blank=True,
        related_name='workflow_notification_cc',
        help_text="Additional users to CC"
    )

    # BCC recipients (for compliance/audit)
    bcc_roles = models.ManyToManyField(
        'accounts.Role',
        blank=True,
        related_name='workflow_notification_bcc',
        help_text="Roles to BCC (for audit/compliance)"
    )

    # Notification settings
    send_in_app = models.BooleanField(
        default=True,
        help_text="Send as in-app notification"
    )
    send_email = models.BooleanField(
        default=True,
        help_text="Send as email"
    )
    send_push = models.BooleanField(
        default=False,
        help_text="Send as push notification (future)"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflow_step_notification_configs'
        ordering = ['workflow_step', 'trigger_event']

    def __str__(self):
        return f"{self.workflow_step.step_name} - {self.trigger_event}"
```

### Frontend Configuration UI

#### Workflow Step Editor

```
┌─────────────────────────────────────────────────────────────────┐
│ Workflow: Transport Request Approval                            │
│                                                                  │
│ Step 1: HOD Approval                                            │
│ ├─ Approver: Role: HOD                                          │
│ │                                                                │
│ └─ Notifications:                                               │
│    ┌───────────────────────────────────────────────────────────┐│
│    │ ✉️ When Step is Created (Approval Request)               ││
│    │                                                            ││
│    │ Template: [Transport Approval Request Template ▼]         ││
│    │                                                            ││
│    │ Send To (Primary Recipients):                             ││
│    │ ☑️ Step Approver (HOD)                                    ││
│    │                                                            ││
│    │ CC (Carbon Copy):                                          ││
│    │ ☑️ Original Requestor                                     ││
│    │ ☑️ Roles: [Department Focal ▼] [Line Manager ▼]          ││
│    │ ☐ Specific Users: [Select users...]                       ││
│    │                                                            ││
│    │ BCC (Audit Trail):                                         ││
│    │ ☑️ Roles: [Transport Admin ▼]                             ││
│    │                                                            ││
│    │ Delivery:                                                  ││
│    │ ☑️ Email  ☑️ In-App  ☐ Push                               ││
│    │                                                            ││
│    │ Status: ✓ Active                                           ││
│    └───────────────────────────────────────────────────────────┘│
│    ┌───────────────────────────────────────────────────────────┐│
│    │ ✉️ When Step is Approved                                 ││
│    │                                                            ││
│    │ Template: [Transport Step Approved Template ▼]            ││
│    │                                                            ││
│    │ Send To:                                                   ││
│    │ ☑️ Original Requestor                                     ││
│    │ ☑️ Next Step Approver                                     ││
│    │                                                            ││
│    │ CC:                                                        ││
│    │ ☑️ Previous Approvers                                     ││
│    │ ...                                                        ││
│    └───────────────────────────────────────────────────────────┘│
│    [+ Add Notification Configuration]                           │
└─────────────────────────────────────────────────────────────────┘
```

### API Endpoints

#### 1. Workflow Step Notification Configs

```python
# List/Create notification configs for a workflow step
GET    /api/workflows/steps/{step_id}/notification-configs/
POST   /api/workflows/steps/{step_id}/notification-configs/

# Update/Delete specific config
PUT    /api/workflows/steps/{step_id}/notification-configs/{config_id}/
PATCH  /api/workflows/steps/{step_id}/notification-configs/{config_id}/
DELETE /api/workflows/steps/{step_id}/notification-configs/{config_id}/

# Test notification (preview before saving)
POST   /api/workflows/steps/{step_id}/notification-configs/test/
```

#### Example Request Body

```json
{
  "trigger_event": "step_created",
  "notification_template": "uuid-of-template",
  "recipient_type": "approver",
  "recipient_roles": [],
  "recipient_users": [],
  "cc_requestor": true,
  "cc_previous_approvers": false,
  "cc_roles": ["uuid-dept-focal", "uuid-line-manager"],
  "cc_users": [],
  "bcc_roles": ["uuid-transport-admin"],
  "send_in_app": true,
  "send_email": true,
  "send_push": false,
  "is_active": true
}
```

### Updated Workflow Engine

The workflow engine will be updated to use notification configs:

```python
class WorkflowNotifications:
    @staticmethod
    def send_step_notifications(step_execution, trigger_event):
        """
        Send notifications based on workflow step notification configs.

        Args:
            step_execution: WorkflowStepExecution instance
            trigger_event: 'step_created', 'step_approved', etc.
        """
        # Get all active notification configs for this step and trigger
        configs = step_execution.workflow_step.notification_configs.filter(
            trigger_event=trigger_event,
            is_active=True
        )

        for config in configs:
            # Determine recipients
            recipients = WorkflowNotifications._get_recipients(
                config, step_execution
            )
            cc_recipients = WorkflowNotifications._get_cc_recipients(
                config, step_execution
            )
            bcc_recipients = WorkflowNotifications._get_bcc_recipients(
                config, step_execution
            )

            # Get notification template or use default
            template = config.notification_template

            # Send notifications
            for recipient in recipients:
                WorkflowNotifications._send_notification(
                    recipient=recipient,
                    cc=cc_recipients,
                    bcc=bcc_recipients,
                    template=template,
                    step_execution=step_execution,
                    config=config
                )
```

### Benefits

#### 1. Flexibility
- Configure different notifications for different workflow events
- Choose who gets notified at each step
- Use different templates for different scenarios

#### 2. Transparency
- Clear visibility of who receives notifications
- Easy to audit notification settings
- Users can see notification configuration in the UI

#### 3. Compliance
- BCC support for audit trail
- All notifications logged in database
- Complete history of who was notified when

#### 4. User Control
- Business users can configure notifications without code changes
- Test notifications before activating
- Enable/disable notifications without deleting configuration

### Implementation Phases

#### Phase 1: Database & Models (Week 1)
- Create migration for `WorkflowStepNotificationConfig`
- Add model with all fields
- Create admin interface for testing

#### Phase 2: Backend API (Week 1-2)
- Create serializers for notification configs
- Implement CRUD API endpoints
- Update workflow engine to use configs
- Add backward compatibility with current system

#### Phase 3: Frontend UI (Week 2-3)
- Design notification configuration UI
- Implement workflow step editor with notification section
- Add template selector with preview
- Add recipient selector (roles, users)
- Add CC/BCC configuration

#### Phase 4: Testing & Migration (Week 3-4)
- Test all notification scenarios
- Create migration script to convert existing workflows
- User acceptance testing
- Documentation

#### Phase 5: Rollout (Week 4)
- Deploy to production
- Train users on new configuration
- Monitor and fix issues

### Migration Strategy

For existing workflows, create default notification configs:

```python
def migrate_existing_workflows():
    """
    Create default notification configs for existing workflow steps.
    """
    for step in WorkflowStep.objects.all():
        # When step is created - notify approver
        WorkflowStepNotificationConfig.objects.create(
            workflow_step=step,
            trigger_event='step_created',
            recipient_type='approver',
            cc_requestor=True,
            send_in_app=True,
            send_email=True
        )

        # When step is approved - notify requestor
        WorkflowStepNotificationConfig.objects.create(
            workflow_step=step,
            trigger_event='step_approved',
            recipient_type='requestor',
            cc_previous_approvers=True,
            send_in_app=True,
            send_email=True
        )

        # When step is rejected - notify requestor
        WorkflowStepNotificationConfig.objects.create(
            workflow_step=step,
            trigger_event='step_rejected',
            recipient_type='requestor',
            send_in_app=True,
            send_email=True
        )
```

### Alternative: Quick Fix for Current System

If the full implementation is too complex, we can do a simpler fix:

1. Add a `notification_roles` ManyToMany field to `WorkflowStep`
2. Add UI to select which roles should be notified
3. Update workflow engine to notify all users in those roles

This provides basic notification control without the full configuration system.

## Summary

### Immediate Fixes (Completed Today)
✓ Fixed Unicode encoding errors
✓ Fixed workflow step assignment logic
✓ Resent notifications to correct recipients
✓ Updated Transport workflow to use role-based assignment

### Proposed Enhancement
- Full notification configuration system
- Frontend UI for managing notifications
- Support for TO, CC, BCC recipients
- Template selection per notification
- Multiple notifications per workflow step
- Complete audit trail

### Next Steps
1. Review this proposal
2. Decide on implementation approach (full system vs. quick fix)
3. Prioritize and schedule development
4. Begin implementation

---

**Status**: Proposal - Awaiting Review and Approval
**Created**: 2025-12-23
**Author**: Claude Code Assistant
