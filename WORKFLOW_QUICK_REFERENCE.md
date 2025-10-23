# Workflow System - Quick Reference

## 🚀 Quick Start

### For Users

1. **Submit a request** → Workflow starts automatically
2. **View detail page** → See workflow timeline
3. **If assigned to you** → Action buttons appear
4. **Click Approve/Reject** → Workflow advances

### For Developers

**Integrate a new module in 3 steps:**

```typescript
// 1. Import and add to component
import { WorkflowService } from '../../../../core/services/workflow.service';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { ApprovalActionsComponent } from '../../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../../../core/models/workflow.models';

@Component({
  imports: [CommonModule, WorkflowStatusComponent, ApprovalActionsComponent]
})
export class YourDetailComponent {
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;
  currentStepExecution: WorkflowStepExecution | null = null;

  constructor(public workflowService: WorkflowService) {}
}

// 2. Add loadWorkflow() method - see WORKFLOW_INTEGRATION_GUIDE.md

// 3. Add to template
<app-workflow-status [workflowInstance]="workflow"></app-workflow-status>
<app-approval-actions
  [stepExecution]="currentStepExecution"
  (approved)="onWorkflowApproved()">
</app-approval-actions>
```

---

## 📖 Entity Types

| Module | Entity Type String | Model Name |
|--------|-------------------|------------|
| Transport | `transportrequest` | TransportRequest |
| Claims | `expenseclaim` | ExpenseClaim |
| TRF | `travelrequest` | TravelRequest |
| Accommodation | `accommodationrequest` | AccommodationRequest |
| Visa | `visarequest` | VisaRequest |

---

## 🔧 Common Tasks

### View Pending Workflows
```python
python manage.py shell
>>> from workflows.models import WorkflowInstance
>>> WorkflowInstance.objects.filter(status='in_progress')
```

### Create Workflow Template
```bash
python manage.py create_default_workflows
```

### Manually Start Workflow
```python
from workflows.engine import WorkflowEngine
WorkflowEngine.start_workflow(entity=request, initiated_by=user, module_name='transport')
```

### Approve Step
```python
from workflows.engine import WorkflowEngine
WorkflowEngine.process_action(step_execution_id=123, action='approve', actioned_by=user, comments="LGTM")
```

---

## 🎨 Component Usage

### Workflow Timeline
```html
<app-workflow-status [workflowInstance]="workflow"></app-workflow-status>
<app-workflow-status [workflowInstanceId]="workflowId"></app-workflow-status>
<app-workflow-status [workflowInstanceId]="id" [compact]="true"></app-workflow-status>
```

### Action Buttons
```html
<app-approval-actions
  [stepExecution]="currentStepExecution"
  [compact]="false"
  (approved)="onApproved()"
  (rejected)="onRejected()"
  (delegated)="onDelegated()"
  (skipped)="onSkipped()">
</app-approval-actions>
```

---

## 🐛 Troubleshooting

### Workflow Not Starting?
1. Check signal registered in apps.py
2. Verify status = "Submitted" exactly
3. Check Django console logs
4. Verify workflow template exists for module

### Timeline Not Showing?
1. Check browser console for errors
2. Verify entity_type matches exactly
3. Check Network tab for API calls
4. Verify workflow instance exists in DB

### No Action Buttons?
1. Check if user is assigned to current step
2. Verify `can_action === true`
3. Check step status is 'pending'
4. Console log `currentStepExecution`

---

## 📚 Documentation

- **Integration Guide:** `WORKFLOW_INTEGRATION_GUIDE.md`
- **Complete Overview:** `WORKFLOW_IMPLEMENTATION_FINAL.md`
- **Backend Reference:** `BACKEND_WORKFLOW_COMPLETE.md`
- **Frontend Guide:** `FRONTEND_WORKFLOW_PROGRESS.md`
- **Session Summary:** `SESSION_SUMMARY.md`

---

## 🔗 Key Files

### Backend
- Engine: `backend/workflows/engine.py`
- Models: `backend/workflows/models.py`
- Signals: `backend/{module}/signals.py`

### Frontend
- Service: `frontend/src/app/core/services/workflow.service.ts`
- Models: `frontend/src/app/core/models/workflow.models.ts`
- Components: `frontend/src/app/shared/components/`

### Examples
- Transport: `frontend/src/app/features/transport/components/transport-detail/`
- Claims: `frontend/src/app/features/expense-claims/components/expense-detail/`
- TRF: `frontend/src/app/features/trf-management/components/trf-detail/`

---

## 💡 Pro Tips

1. **Always use entity_type exactly as shown in table above** (case-sensitive)
2. **Check Transport module** for the most complete reference implementation
3. **Use browser DevTools** to debug workflow loading issues
4. **Check Django logs** when workflows don't auto-start
5. **Read WORKFLOW_INTEGRATION_GUIDE.md** for step-by-step instructions

---

**Quick Links:**
- [Integration Guide](WORKFLOW_INTEGRATION_GUIDE.md)
- [Complete Documentation](WORKFLOW_IMPLEMENTATION_FINAL.md)
- [Backend API](BACKEND_WORKFLOW_COMPLETE.md)

