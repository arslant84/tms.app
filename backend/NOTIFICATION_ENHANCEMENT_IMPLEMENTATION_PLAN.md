# Enhanced Notification System - Implementation Plan
## NON-BREAKING, ADDITIVE APPROACH

## Core Principle: Backward Compatibility

✅ **Current system continues to work exactly as it does now**
✅ **New configuration is OPTIONAL**
✅ **No changes to existing workflow models**
✅ **No changes to existing workflow instances**
✅ **Gradual migration at your own pace**

## How It Works

### Fallback Logic

```python
def send_notification(step_execution, trigger_event):
    # 1. Check if notification config exists for this step
    configs = get_notification_configs(step_execution.workflow_step, trigger_event)

    if configs.exists():
        # Use new configurable system
        send_configured_notifications(configs, step_execution)
    else:
        # Fall back to current default behavior (existing code)
        send_default_notifications(step_execution, trigger_event)
```

### What This Means

1. **Existing workflows** - Continue working with current notification logic
2. **New configured steps** - Use enhanced notification settings
3. **Mix and match** - Some steps can use new config, others use defaults
4. **Zero downtime** - No interruption to current operations

## Database Changes (Additive Only)

### New Tables (No modifications to existing tables)

```sql
-- New table - does not affect existing tables
CREATE TABLE workflow_step_notification_configs (
    id UUID PRIMARY KEY,
    workflow_step_id UUID REFERENCES workflow_steps(id),
    trigger_event VARCHAR(50),
    notification_template_id UUID REFERENCES notification_templates(id),
    recipient_type VARCHAR(50),
    cc_requestor BOOLEAN DEFAULT FALSE,
    cc_previous_approvers BOOLEAN DEFAULT FALSE,
    send_in_app BOOLEAN DEFAULT TRUE,
    send_email BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Junction tables for many-to-many relationships
CREATE TABLE notification_config_recipient_roles (
    config_id UUID REFERENCES workflow_step_notification_configs(id),
    role_id UUID REFERENCES roles(id)
);

CREATE TABLE notification_config_recipient_users (
    config_id UUID REFERENCES workflow_step_notification_configs(id),
    user_id UUID REFERENCES users(id)
);

CREATE TABLE notification_config_cc_roles (
    config_id UUID REFERENCES workflow_step_notification_configs(id),
    role_id UUID REFERENCES roles(id)
);

CREATE TABLE notification_config_cc_users (
    config_id UUID REFERENCES workflow_step_notification_configs(id),
    user_id UUID REFERENCES users(id)
);

CREATE TABLE notification_config_bcc_roles (
    config_id UUID REFERENCES workflow_step_notification_configs(id),
    role_id UUID REFERENCES roles(id)
);
```

**ZERO changes to**:
- ✅ workflow_templates
- ✅ workflow_steps
- ✅ workflow_instances
- ✅ workflow_step_executions
- ✅ All other existing tables

## Code Changes (Additive Approach)

### 1. New Model (Separate from existing)

```python
# workflows/models.py - ADD this new model (don't modify existing)

class WorkflowStepNotificationConfig(models.Model):
    """
    OPTIONAL notification configuration for workflow steps.
    If not configured, system uses default behavior.
    """
    # ... full model definition
    pass
```

### 2. Enhanced Notification Service (Wraps existing)

```python
# workflows/notifications.py - UPDATE to add configuration support

class WorkflowNotifications:
    @staticmethod
    def notify_workflow_started(workflow_instance):
        """Send notification when workflow starts."""
        # Get first step
        first_step = workflow_instance.step_executions.first()

        if first_step:
            # Try to use configured notifications
            configs = WorkflowStepNotificationConfig.objects.filter(
                workflow_step=first_step.workflow_step,
                trigger_event='step_created',
                is_active=True
            )

            if configs.exists():
                # NEW: Use configured notifications
                WorkflowNotifications._send_configured_notifications(
                    configs, first_step, workflow_instance
                )
            else:
                # EXISTING: Fall back to current default behavior
                WorkflowNotifications._send_default_workflow_started_notification(
                    workflow_instance
                )

    @staticmethod
    def _send_default_workflow_started_notification(workflow_instance):
        """
        EXISTING notification logic - unchanged.
        This is the current code that works now.
        """
        # Notify the person who initiated the workflow
        NotificationService.create_notification(
            user=workflow_instance.initiated_by,
            title=f"Workflow Started: {workflow_instance.workflow_template.name}",
            message=f"Your {workflow_instance.workflow_template.entity_type} request has been submitted...",
            event_type=_get_event_type('WORKFLOW_STARTED'),
            priority='normal',
            action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
            send_email=True
        )

        # Notify first approver
        if workflow_instance.step_executions.exists():
            first_step = workflow_instance.step_executions.filter(
                workflow_step__step_order=1,
                status='pending'
            ).first()

            if first_step and first_step.assigned_to:
                NotificationService.create_notification(
                    user=first_step.assigned_to,
                    title=f"New Approval Required: {workflow_instance.workflow_template.name}",
                    message=f"You have been assigned to approve...",
                    event_type=_get_event_type('APPROVAL_REQUESTED'),
                    priority='high',
                    action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                    send_email=True
                )

    @staticmethod
    def _send_configured_notifications(configs, step_execution, workflow_instance):
        """
        NEW: Send notifications based on configuration.
        Only called if configuration exists.
        """
        for config in configs:
            # Get recipients based on config
            recipients = WorkflowNotifications._resolve_recipients(config, step_execution)
            cc_recipients = WorkflowNotifications._resolve_cc_recipients(config, step_execution)
            bcc_recipients = WorkflowNotifications._resolve_bcc_recipients(config, step_execution)

            # Get template or use default
            template = config.notification_template

            # Send to each recipient
            for recipient in recipients:
                if config.send_email or config.send_in_app:
                    NotificationService.create_notification(
                        user=recipient,
                        title=template.subject if template else f"Workflow Notification",
                        message=template.body if template else "You have a workflow notification",
                        event_type=_get_event_type(config.trigger_event.upper()),
                        priority='high' if config.trigger_event == 'step_created' else 'normal',
                        action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                        send_email=config.send_email
                    )
```

## Migration Strategy (Safe & Gradual)

### Phase 1: Deploy New System (Week 1)
- Deploy new models and code
- **No existing workflows are affected**
- System continues using current notification logic
- New tables are created but empty

### Phase 2: Enable Configuration UI (Week 2)
- Deploy frontend UI for notification configuration
- **Still no changes to existing workflows**
- Users can start configuring notifications for NEW workflows
- Existing workflows still use default behavior

### Phase 3: Gradual Migration (Week 3-4+)
- Users configure notifications at their own pace
- **Per workflow, per step basis**
- Example:
  - Week 3: Configure Transport workflow only
  - Week 4: Configure TRF workflow
  - Week 5: Configure Visa workflow
  - etc.

### Phase 4: Monitoring (Ongoing)
- Monitor both systems running in parallel
- Fix any issues without affecting existing workflows
- Eventually, all workflows can be configured (but not required)

## Frontend Integration (Non-Breaking)

### Workflow Step Editor

```javascript
// EXISTING workflow step form - NO CHANGES
<FormGroup>
  <Label>Approver Role</Label>
  <Select name="approver_role" ... />
</FormGroup>

<FormGroup>
  <Label>Approver Permission</Label>
  <Select name="approver_permission" ... />
</FormGroup>

// NEW: Optional notification configuration section
<Accordion>
  <AccordionItem title="📧 Notification Configuration (Optional)">
    <p>Configure who receives notifications for this step. If not configured, default notifications will be sent.</p>

    <Button onClick={addNotificationConfig}>
      + Add Notification Configuration
    </Button>

    {notificationConfigs.map(config => (
      <NotificationConfigForm
        config={config}
        onSave={saveConfig}
        onDelete={deleteConfig}
      />
    ))}
  </AccordionItem>
</Accordion>
```

### User Experience

**Existing Workflows:**
- No visible changes
- Works exactly as before
- Can optionally add notification configuration later

**New Workflows:**
- Can choose to configure notifications
- Can skip and use defaults
- Can add configuration later

## Example: Transport Workflow Enhancement

### Before (Current - Still Works)
```
Transport Workflow
└─ Step 1: HOD Approval
   - Approver: HOD Role
   - [No notification config]

Result: Uses default notification logic
- Sends to HOD
- Sends confirmation to requestor
```

### After Configuration (Optional Enhancement)
```
Transport Workflow
└─ Step 1: HOD Approval
   - Approver: HOD Role
   - Notifications: ✓ Configured

     When Step Created:
     ├─ To: HOD
     ├─ CC: Department Focal, Line Manager
     ├─ BCC: Transport Admin
     └─ Template: Transport Approval Request

     When Step Approved:
     ├─ To: Requestor
     ├─ CC: HOD, Next Approver
     └─ Template: Transport Step Approved

     When Step Rejected:
     ├─ To: Requestor
     ├─ CC: HOD, Line Manager
     └─ Template: Transport Step Rejected

Result: Uses configured notification settings
- More people are informed (CC/BCC)
- Uses custom templates
- More control over who gets what
```

## API Backward Compatibility

### All existing API endpoints unchanged

```python
# EXISTING - Works exactly as before
GET  /api/workflows/templates/
POST /api/workflows/templates/
GET  /api/workflows/steps/
POST /api/workflows/steps/
...all other existing endpoints...
```

### New optional API endpoints

```python
# NEW - Only for notification configuration
GET    /api/workflows/steps/{id}/notification-configs/
POST   /api/workflows/steps/{id}/notification-configs/
PUT    /api/workflows/steps/{id}/notification-configs/{config_id}/
DELETE /api/workflows/steps/{id}/notification-configs/{config_id}/
```

## Testing Strategy

### 1. Existing Workflows Continue Working
- Run all existing tests
- Verify transport requests still work
- Verify TRF requests still work
- Verify all modules continue as-is

### 2. New Configuration Works
- Test notification configuration CRUD
- Test configured notifications are sent
- Test fallback to defaults when not configured

### 3. No Cross-Contamination
- Configured workflows don't affect non-configured
- Non-configured workflows work independently
- Both can coexist

## Rollback Plan (If Needed)

Because this is additive and non-breaking:

### Option 1: Disable New Feature
```python
# Add feature flag in settings
ENABLE_NOTIFICATION_CONFIGURATION = False

# In notification code
if settings.ENABLE_NOTIFICATION_CONFIGURATION:
    # Try configured notifications
    ...
else:
    # Always use default behavior
    send_default_notifications()
```

### Option 2: Database Cleanup
If we need to completely remove:
```sql
-- Just drop new tables, existing system unaffected
DROP TABLE notification_config_bcc_roles;
DROP TABLE notification_config_cc_users;
DROP TABLE notification_config_cc_roles;
DROP TABLE notification_config_recipient_users;
DROP TABLE notification_config_recipient_roles;
DROP TABLE workflow_step_notification_configs;

-- Existing system works exactly as before
```

## Implementation Checklist

### Backend
- [ ] Create new models (no modifications to existing)
- [ ] Add fallback logic to notifications
- [ ] Create new API endpoints (separate from existing)
- [ ] Write tests for new functionality
- [ ] Add feature flag for safety
- [ ] Deploy to staging

### Frontend
- [ ] Create notification config UI components
- [ ] Add to workflow step editor (as optional section)
- [ ] Create recipient selector
- [ ] Create template selector
- [ ] Add CC/BCC configuration
- [ ] Test with existing workflows (should see no changes)
- [ ] Test with new configurations

### Testing
- [ ] Verify existing workflows unchanged
- [ ] Test notification configuration
- [ ] Test fallback behavior
- [ ] User acceptance testing
- [ ] Performance testing

### Documentation
- [ ] API documentation for new endpoints
- [ ] User guide for notification configuration
- [ ] Migration guide (optional)
- [ ] Video tutorial for users

## Timeline

**Week 1: Backend Implementation**
- Day 1-2: Models and migrations
- Day 3-4: API endpoints and logic
- Day 5: Testing and fixes

**Week 2: Frontend Implementation**
- Day 1-2: UI components
- Day 3-4: Integration with workflow editor
- Day 5: Testing and refinement

**Week 3: Testing & Deployment**
- Day 1-2: Comprehensive testing
- Day 3: Deploy to staging
- Day 4: User acceptance testing
- Day 5: Deploy to production

**Week 4: Gradual Rollout**
- Configure one workflow as pilot
- Monitor and fix any issues
- Train users
- Gradual adoption across all workflows

## Success Criteria

✅ **No disruption**: All existing workflows continue working unchanged
✅ **Optional adoption**: Users can configure at their own pace
✅ **Flexibility**: Support all requested notification scenarios
✅ **Backward compatible**: Can roll back without data loss
✅ **User-friendly**: Business users can configure without developer help

---

## Summary

This implementation is **100% safe** because:

1. ✅ **No changes to existing database tables** - only adds new ones
2. ✅ **No changes to existing workflow logic** - only adds optional enhancement
3. ✅ **Fallback to current behavior** - if no config, works like before
4. ✅ **Gradual migration** - configure workflows one at a time
5. ✅ **Easy rollback** - just drop new tables or disable feature flag
6. ✅ **Zero downtime** - can deploy without interruption

**Your current system will keep working exactly as it does now, and you can gradually add notification configuration when you're ready.**
