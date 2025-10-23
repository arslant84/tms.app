# Workflow System Implementation Status

## ✅ Completed Work

### 1. Analysis & Design (Completed)
- ✅ Analyzed React source project's approval workflow system
- ✅ Compared with current Django implementation
- ✅ Identified gaps and designed unified approach
- ✅ Created comprehensive migration plan (`WORKFLOW_MIGRATION_PLAN.md`)

### 2. Backend Infrastructure (Completed)
- ✅ **Workflow Models Already Exist!** (`backend/workflows/models.py`)
  - `WorkflowTemplate` - Configurable workflow definitions
  - `WorkflowStep` - Steps within workflows
  - `WorkflowCondition` - Conditional logic for steps
  - `WorkflowInstance` - Active workflow executions
  - `WorkflowStepExecution` - Individual step tracking
  - `WorkflowDelegation` - Delegation support
  - `WorkflowAuditLog` - Complete audit trail

- ✅ **WorkflowEngine Service Created!** (`backend/workflows/engine.py`)
  - `start_workflow()` - Initiate workflow for any entity
  - `process_action()` - Handle approve/reject/skip actions
  - `delegate_step()` - Delegate approvals to other users
  - `get_pending_approvals()` - Get user's pending tasks
  - `cancel_workflow()` - Cancel active workflows
  - `check_and_escalate_overdue_steps()` - Background job for escalations

## 🔄 Next Steps (In Priority Order)

### Phase 1: Backend API (High Priority)

#### 1.1 Create Serializers (`backend/workflows/serializers.py`)
```python
# Needed serializers:
- WorkflowTemplateSerializer
- WorkflowStepSerializer
- WorkflowInstanceSerializer (with nested steps)
- WorkflowStepExecutionSerializer
- PendingApprovalSerializer (for user dashboard)
```

#### 1.2 Create ViewSets (`backend/workflows/views.py`)
```python
# Needed endpoints:
- WorkflowTemplateViewSet (CRUD for admins)
- WorkflowInstanceViewSet (read-only for users)
- ApprovalActionViewSet (approve/reject/delegate)
- PendingApprovalsView (GET /api/workflows/my-pending/)
```

#### 1.3 Register URLs (`backend/workflows/urls.py`)
```python
# URL patterns:
- /api/workflows/templates/
- /api/workflows/instances/<id>/
- /api/workflows/instances/<id>/approve/
- /api/workflows/instances/<id>/reject/
- /api/workflows/instances/<id>/delegate/
- /api/workflows/my-pending/
```

#### 1.4 Register App in Settings
Add `'workflows'` to `INSTALLED_APPS` in `backend/tms_project/settings.py`

#### 1.5 Create Migrations
```bash
python manage.py makemigrations workflows
python manage.py migrate workflows
```

### Phase 2: Module Integration (High Priority)

#### 2.1 Create Django Signals
Add signal handlers to auto-start workflows when requests are submitted:

**File:** `backend/workflows/signals.py`
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from expenses.models import ExpenseClaim
from trf.models import TravelRequest
from visa.models import VisaApplication
from transport.models import TransportRequest
from .engine import WorkflowEngine

@receiver(post_save, sender=ExpenseClaim)
def start_claim_workflow(sender, instance, created, **kwargs):
    if created and instance.status == 'SUBMITTED':
        WorkflowEngine.start_workflow(instance, instance.user, 'claims')

# Similar handlers for TRF, Visa, Transport, Accommodation
```

#### 2.2 Update Module Serializers
Add workflow status to entity serializers:

**Example:** `backend/expenses/serializers.py`
```python
class ExpenseClaimSerializer(serializers.ModelSerializer):
    workflow_status = serializers.SerializerMethodField()

    def get_workflow_status(self, obj):
        # Return workflow instance data if exists
        pass
```

### Phase 3: Frontend Implementation (Medium Priority)

#### 3.1 Create Angular Workflow Service
**File:** `frontend/src/app/core/services/workflow.service.ts`
```typescript
@Injectable({ providedIn: 'root' })
export class WorkflowService {
  getPendingApprovals(): Observable<PendingApproval[]>
  approveStep(instanceId: string, stepId: string, comments?: string): Observable<any>
  rejectStep(instanceId: string, stepId: string, comments: string): Observable<any>
  delegateStep(instanceId: string, stepId: string, delegateTo: string): Observable<any>
  getWorkflowStatus(instanceId: string): Observable<WorkflowInstance>
}
```

#### 3.2 Create Workflow Status Component
**File:** `frontend/src/app/shared/components/workflow-status/workflow-status.component.ts`
Visual timeline showing workflow progress with steps:
- Completed steps (green checkmark)
- Current step (yellow/orange, pulsing)
- Pending steps (gray)
- Rejected steps (red X)

#### 3.3 Create Approval Action Component
**File:** `frontend/src/app/shared/components/approval-actions/approval-actions.component.ts`
Action buttons for approvers:
- Approve button (green)
- Reject button (red) with comment dialog
- Delegate button (blue) with user selector

#### 3.4 Update Detail Pages
Add workflow status widget to all detail pages:
- `expense-detail.component.html`
- `trf-detail.component.html`
- `visa-detail.component.html`
- `transport-detail.component.html`
- `accommodation-detail.component.html`

#### 3.5 Create Pending Approvals Dashboard
**File:** `frontend/src/app/features/approvals/pending-approvals/`
Centralized dashboard showing all pending approvals across modules.

### Phase 4: Data Migration (Medium Priority)

#### 4.1 Create Default Workflow Templates
**File:** `backend/workflows/management/commands/create_default_workflows.py`
Django management command to create default workflows:
- TRF Workflow (Department Focal → Line Manager → HOD → Travel Desk)
- Claims Workflow (Department Focal → Line Manager → Finance)
- Visa Workflow (Department Focal → Line Manager → HOD → Visa Admin)
- Transport Workflow (Department Focal → Line Manager → HOD → Transport Admin)
- Accommodation Workflow (Department Focal → Line Manager → HOD → Admin)

#### 4.2 Migrate Existing Approval Data (Optional)
If there are existing requests with old ApprovalStep data:
```python
# Convert ClaimsApprovalStep → WorkflowStepExecution
# Convert TrfApprovalStep → WorkflowStepExecution
# etc.
```

### Phase 5: Admin UI (Low Priority)

#### 5.1 Django Admin Configuration
**File:** `backend/workflows/admin.py`
Register models with admin interface for workflow management.

#### 5.2 Angular Admin Workflow Management (Future)
**File:** `frontend/src/app/features/admin/workflow-management/`
UI for admins to create/edit workflows without code changes.

### Phase 6: Background Jobs (Medium Priority)

#### 6.1 Setup Celery for Escalation
**File:** `backend/workflows/tasks.py`
```python
from celery import shared_task
from .engine import WorkflowEngine

@shared_task
def check_escalations():
    """Run every hour to check for overdue steps"""
    return WorkflowEngine.check_and_escalate_overdue_steps()
```

#### 6.2 Configure Celery Beat Schedule
Add to `settings.py`:
```python
CELERY_BEAT_SCHEDULE = {
    'check-workflow-escalations': {
        'task': 'workflows.tasks.check_escalations',
        'schedule': crontab(minute=0),  # Every hour
    },
}
```

## 📊 Implementation Progress

| Phase | Status | Priority | Estimated Effort |
|-------|--------|----------|------------------|
| Analysis & Design | ✅ Completed | - | - |
| Backend Models | ✅ Already Exists | - | - |
| WorkflowEngine Service | ✅ Completed | - | - |
| Backend API (Serializers/Views) | ⏳ Pending | High | 4-6 hours |
| Module Integration (Signals) | ⏳ Pending | High | 2-3 hours |
| Data Migration (Default Workflows) | ⏳ Pending | High | 2-3 hours |
| Frontend Service | ⏳ Pending | Medium | 3-4 hours |
| Frontend Components | ⏳ Pending | Medium | 6-8 hours |
| Admin UI | ⏳ Pending | Low | 4-6 hours |
| Background Jobs (Celery) | ⏳ Pending | Medium | 2-3 hours |

**Total Remaining Effort:** ~23-33 hours

## 🎯 Recommended Immediate Next Steps

1. **Create Backend API** (serializers, views, URLs) - ~4-6 hours
2. **Run migrations** and test WorkflowEngine - ~1 hour
3. **Create default workflows** via management command - ~2-3 hours
4. **Add signals** to auto-start workflows - ~2-3 hours
5. **Test end-to-end** with one module (e.g., Claims) - ~2 hours

After completing these steps, the basic workflow system will be functional for testing.

## 📝 Alternative Approach: Incremental Migration

Instead of implementing everything at once, you could:

1. **Keep existing ApprovalStep models** for now
2. **Run workflows in parallel** (dual-write to both systems)
3. **Gradually migrate** one module at a time
4. **Deprecate old system** once all modules are migrated

This approach reduces risk but adds temporary complexity.

## ⚠️ Important Notes

1. **User Roles Required**: The workflow system depends on users having roles (Line Manager, HOD, Department Focal, etc.). Ensure the `accounts.Role` model is properly set up.

2. **Department Assignment**: For department-specific approvals, users must have a `department` field.

3. **Status Mapping**: Current module statuses (e.g., "Pending", "Approved") need to align with workflow statuses.

4. **Notification Integration**: The workflow engine has hooks for notifications but actual notification sending needs to be implemented.

5. **Testing**: Comprehensive tests are needed for the WorkflowEngine to ensure correct behavior.

## 🔗 Related Files

- `WORKFLOW_MIGRATION_PLAN.md` - Detailed migration plan
- `CONFIRMATION_MIGRATION_STATUS.md` - Alert/confirm replacement status
- `ROADMAP.md` - Overall project status
- `backend/workflows/models.py` - Workflow models
- `backend/workflows/engine.py` - Workflow business logic

## 🤝 Questions to Answer Before Proceeding

1. **Should we implement incrementally or all at once?**
   - Incremental = safer, slower
   - All at once = faster, higher risk

2. **Which module should be the pilot?**
   - Recommendation: Start with Transport (simpler workflow)

3. **Do we need to preserve existing ApprovalStep data?**
   - If yes, need migration scripts
   - If no, can start fresh

4. **Timeline expectations?**
   - Full implementation: ~3-4 days
   - Pilot module: ~1-2 days

5. **Resource availability?**
   - Frontend developer available?
   - Backend developer available?
   - Can work in parallel?
