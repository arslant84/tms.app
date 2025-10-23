# Approval Workflow Migration Plan

## Overview
Migrating from the current "signatories" approval approach to a proper workflow-based approval system matching the React source project.

## Current State Analysis

### Current Implementation (Django)

Each module has its own `ApprovalStep` model:
- **ExpenseClaim** → `ClaimsApprovalStep`
- **TravelRequest (TRF)** → `TrfApprovalStep`
- **TransportRequest** → `TransportApprovalStep`
- **VisaApplication** → `VisaApprovalStep`

**Current ApprovalStep Structure:**
```python
class XxxApprovalStep(models.Model):
    xxx = models.ForeignKey(...)  # Reference to parent entity
    step_role = models.CharField(max_length=255)
    step_name = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    step_date = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
```

**Problems with Current Approach:**
1. ❌ **Hardcoded workflow** - Each request type creates approval steps manually
2. ❌ **No workflow templates** - Can't configure workflows per module
3. ❌ **No role-based assignment** - No automatic assignment to users by role
4. ❌ **No escalation** - No timeout or escalation mechanisms
5. ❌ **No delegation** - Cannot delegate approvals to other users
6. ❌ **Inconsistent** - Each module implements approval differently

### React Source Implementation (Target)

**Database Schema:**
1. **`workflow_templates`** - Configurable workflow definitions per module
2. **`workflow_steps`** - Steps within a workflow template
3. **`workflow_instances`** (or `workflow_executions`) - Active workflow runs
4. **`workflow_step_executions`** (or `step_executions`) - Individual step executions

**Key Features:**
1. ✅ **Configurable workflows** - Admin can define workflows per module
2. ✅ **Role-based assignment** - Auto-assign to users by role
3. ✅ **Timeout & escalation** - Steps can timeout and escalate to higher role
4. ✅ **Delegation support** - Approvers can delegate to others
5. ✅ **Workflow engine** - Centralized logic for all approvals
6. ✅ **Notification integration** - Auto-notify assignees
7. ✅ **Audit trail** - Complete history of workflow execution

## Target Architecture

### Database Models

#### 1. WorkflowTemplate (Workflow Configuration)
```python
class WorkflowTemplate(models.Model):
    """Defines a workflow for a specific module"""
    id = UUIDField(primary_key=True)
    name = CharField(max_length=255)  # e.g., "TRF Approval Workflow"
    description = TextField(blank=True, null=True)
    module = CharField(max_length=50)  # 'trf', 'claims', 'visa', 'transport', 'accommodation'
    is_active = BooleanField(default=True)
    created_by = ForeignKey(User)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

#### 2. WorkflowStep (Workflow Step Definition)
```python
class WorkflowStep(models.Model):
    """Defines a step within a workflow template"""
    id = UUIDField(primary_key=True)
    workflow_template = ForeignKey(WorkflowTemplate, on_delete=CASCADE)
    step_number = IntegerField()  # Order of execution (1, 2, 3...)
    step_name = CharField(max_length=255)  # e.g., "Line Manager Approval"
    required_role = CharField(max_length=100)  # e.g., "Line Manager", "HOD", "Department Focal"
    description = TextField(blank=True, null=True)
    is_mandatory = BooleanField(default=True)
    can_delegate = BooleanField(default=True)
    timeout_days = IntegerField(null=True, blank=True)  # Auto-escalate after X days
    escalation_role = CharField(max_length=100, null=True, blank=True)  # Role to escalate to
    conditions = JSONField(null=True, blank=True)  # Conditional logic for step
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('workflow_template', 'step_number')
        ordering = ['step_number']
```

#### 3. WorkflowInstance (Workflow Execution)
```python
class WorkflowInstance(models.Model):
    """An active workflow execution for a specific request"""
    id = UUIDField(primary_key=True)
    workflow_template = ForeignKey(WorkflowTemplate, on_delete=CASCADE)

    # Generic foreign key to any request type
    content_type = ForeignKey(ContentType, on_delete=CASCADE)
    object_id = UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    current_step = ForeignKey(WorkflowStep, null=True, on_delete=SET_NULL, related_name='current_instances')
    status = CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected')
    ], default='active')

    initiated_by = ForeignKey(User, on_delete=CASCADE, related_name='initiated_workflows')
    initiated_at = DateTimeField(auto_now_add=True)
    completed_at = DateTimeField(null=True, blank=True)
    metadata = JSONField(default=dict, blank=True)  # Store additional context

    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

#### 4. WorkflowStepExecution (Step Execution)
```python
class WorkflowStepExecution(models.Model):
    """Execution of a specific step in a workflow instance"""
    id = UUIDField(primary_key=True)
    workflow_instance = ForeignKey(WorkflowInstance, on_delete=CASCADE, related_name='step_executions')
    workflow_step = ForeignKey(WorkflowStep, on_delete=CASCADE)

    assigned_to_role = CharField(max_length=100)
    assigned_to_user = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL, related_name='assigned_steps')

    status = CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
        ('escalated', 'Escalated'),
        ('delegated', 'Delegated')
    ], default='pending')

    action_taken_by = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL, related_name='actions_taken')
    action_taken_at = DateTimeField(null=True, blank=True)
    comments = TextField(blank=True, null=True)
    attachments = JSONField(default=dict, blank=True)

    delegated_to = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL, related_name='delegated_steps')
    escalated_from = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL, related_name='escalated_from_steps')

    due_date = DateTimeField(null=True, blank=True)
    started_at = DateTimeField(auto_now_add=True)
    completed_at = DateTimeField(null=True, blank=True)

    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('workflow_instance', 'workflow_step')
        ordering = ['workflow_step__step_number']
```

### Workflow Engine Service

```python
class WorkflowEngine:
    """Core workflow execution engine"""

    @staticmethod
    def start_workflow(request_object, initiated_by):
        """
        Start a new workflow for a request
        1. Get active workflow template for the module
        2. Create WorkflowInstance
        3. Create first step execution
        4. Assign to user with required role
        5. Send notification
        """

    @staticmethod
    def process_step_action(step_execution_id, action, user, comments=None):
        """
        Process approval/rejection action
        - approve: Move to next step or complete workflow
        - reject: Cancel workflow and reject request
        - delegate: Reassign to another user
        """

    @staticmethod
    def auto_assign_to_role(role, department=None):
        """
        Find and assign to user with specified role
        - For HOD/CEO: Department-agnostic
        - For Focal/Line Manager: Department-specific
        """

    @staticmethod
    def handle_timeout_escalation():
        """
        Background job to process step timeouts
        - Find steps past due date
        - Escalate to escalation role
        - Or auto-approve if no escalation defined
        """
```

## Migration Strategy

### Phase 1: Database Schema Migration
1. Create new workflow models
2. Keep existing ApprovalStep models (for backward compatibility)
3. Create migration scripts to convert existing data

### Phase 2: Backend Implementation
1. Implement WorkflowEngine service
2. Create API endpoints for workflow management:
   - `GET /api/workflows/templates/` - List templates
   - `POST /api/workflows/templates/` - Create template
   - `GET /api/workflows/instances/{id}/` - Get workflow status
   - `POST /api/workflows/instances/{id}/approve/` - Approve step
   - `POST /api/workflows/instances/{id}/reject/` - Reject step
   - `POST /api/workflows/instances/{id}/delegate/` - Delegate step
3. Update module views to use WorkflowEngine
4. Update serializers to include workflow data

### Phase 3: Frontend Implementation
1. Create Angular WorkflowService
2. Create workflow status component (visual tracker)
3. Create approval action component
4. Update detail pages to show workflow status
5. Update list pages to filter by workflow status
6. Create admin UI for workflow configuration

### Phase 4: Data Migration
1. Create default workflow templates for each module
2. Migrate existing ApprovalStep data to new system
3. Test thoroughly

### Phase 5: Deprecation
1. Remove old ApprovalStep models
2. Clean up old code
3. Update documentation

## Default Workflow Templates

### TRF Workflow
```
Step 1: Department Focal → Status: "Pending Department Focal"
Step 2: Line Manager → Status: "Pending Line Manager"
Step 3: HOD → Status: "Pending HOD"
Step 4: Travel Desk (auto) → Status: "Approved"
```

### Claims Workflow
```
Step 1: Department Focal → Status: "Pending Department Focal"
Step 2: Line Manager → Status: "Pending Line Manager"
Step 3: Finance (auto) → Status: "Approved"
```

### Visa Workflow
```
Step 1: Department Focal → Status: "Pending Department Focal"
Step 2: Line Manager → Status: "Pending Line Manager"
Step 3: HOD → Status: "Pending HOD"
Step 4: Visa Admin → Status: "Processing with Visa Admin"
Step 5: Complete → Status: "Processed"
```

### Transport Workflow
```
Step 1: Department Focal → Status: "Pending Department Focal"
Step 2: Line Manager → Status: "Pending Line Manager"
Step 3: HOD → Status: "Pending HOD"
Step 4: Transport Admin → Status: "Processing with Transport Admin"
Step 5: Complete → Status: "Completed"
```

### Accommodation Workflow
```
Step 1: Department Focal → Status: "Pending Department Focal"
Step 2: Line Manager → Status: "Pending Line Manager"
Step 3: HOD → Status: "Pending HOD"
Step 4: Accommodation Admin → Status: "Processing"
Step 5: Complete → Status: "Approved"
```

## Key Differences from React Source

1. **Django uses ContentTypes** - For generic foreign keys instead of separate entity_type/entity_id
2. **Django uses CharField for status** - Instead of enum types
3. **Django Signal Hooks** - For auto-creating workflows on request submission
4. **DRF Serializers** - For API responses with nested workflow data
5. **Celery Tasks** - For timeout processing (instead of cron jobs)

## Benefits of New System

1. ✅ **Flexibility** - Admins can modify workflows without code changes
2. ✅ **Consistency** - All modules use same workflow engine
3. ✅ **Scalability** - Easy to add new modules
4. ✅ **Auditability** - Complete history of all approval actions
5. ✅ **User Experience** - Clear visual workflow tracking
6. ✅ **Automation** - Auto-assignment, escalation, notifications
7. ✅ **Delegation** - Approvers can delegate when unavailable
8. ✅ **Timeout Management** - Automatic escalation of stalled requests

## Implementation Checklist

### Backend
- [ ] Create workflow models (WorkflowTemplate, WorkflowStep, WorkflowInstance, WorkflowStepExecution)
- [ ] Implement WorkflowEngine service
- [ ] Create workflow serializers
- [ ] Create workflow viewsets and API endpoints
- [ ] Update request creation signals to start workflows
- [ ] Create Celery task for timeout processing
- [ ] Create default workflow templates (data migration)
- [ ] Update module serializers to include workflow data
- [ ] Add workflow filtering to list views

### Frontend
- [ ] Create WorkflowService (Angular)
- [ ] Create WorkflowStatusComponent (visual tracker with steps)
- [ ] Create ApprovalActionComponent (approve/reject/delegate buttons)
- [ ] Update detail pages to show workflow status
- [ ] Update list pages to filter by workflow status
- [ ] Create admin workflow management page
- [ ] Add workflow delegation dialog
- [ ] Add workflow history view

### Testing
- [ ] Unit tests for WorkflowEngine
- [ ] Integration tests for workflow execution
- [ ] E2E tests for approval flows
- [ ] Test timeout escalation
- [ ] Test delegation
- [ ] Test concurrent approvals
- [ ] Test workflow modification impact

### Documentation
- [ ] API documentation for workflow endpoints
- [ ] User guide for approvers
- [ ] Admin guide for workflow configuration
- [ ] Developer guide for adding new modules
