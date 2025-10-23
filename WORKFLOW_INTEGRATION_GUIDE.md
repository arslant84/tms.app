# Workflow Integration Guide

This guide explains how to integrate the workflow approval system into your Angular module detail pages.

## ✅ Completed Example: Transport Module

The Transport module has been fully integrated with the workflow system and serves as a reference implementation.

**Location:** `frontend/src/app/features/transport/components/transport-detail/`

---

## 📋 Step-by-Step Integration Guide

### Step 1: Update Component TypeScript File

**File:** `your-module-detail.component.ts`

#### 1.1 Add Imports

```typescript
// Workflow imports
import { WorkflowService } from '../../../../core/services/workflow.service';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { ApprovalActionsComponent } from '../../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../../../core/models/workflow.models';
```

#### 1.2 Add Components to Imports Array

```typescript
@Component({
  selector: 'app-your-detail',
  standalone: true,
  imports: [
    CommonModule,
    WorkflowStatusComponent,     // Add this
    ApprovalActionsComponent,    // Add this
    // ... other imports
  ],
  templateUrl: './your-detail.component.html',
  styleUrls: ['./your-detail.component.scss']
})
```

#### 1.3 Add Properties

```typescript
export class YourDetailComponent implements OnInit {
  // Existing properties...

  // Workflow properties
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;
  currentStepExecution: WorkflowStepExecution | null = null;

  // ... rest of component
}
```

#### 1.4 Inject WorkflowService

```typescript
constructor(
  private route: ActivatedRoute,
  private router: Router,
  private yourService: YourService,
  private toastService: ToastService,
  private confirmationService: ConfirmationService,
  public workflowService: WorkflowService  // Add this (public for template access)
) {}
```

#### 1.5 Add Workflow Loading Method

```typescript
loadWorkflow(): void {
  this.workflowLoading = true;

  // Replace 'expenseclaim' with your entity type:
  // - 'expenseclaim' for Expense Claims
  // - 'travelrequest' for TRF
  // - 'visarequest' for Visa
  // - 'transportrequest' for Transport
  // - 'accommodationrequest' for Accommodation

  this.workflowService.getInstances({
    entity_type: 'yourEntityType'  // <-- CHANGE THIS
  }).subscribe({
    next: (instances) => {
      // Find workflow instance for this specific entity
      const instance = instances.find((i: any) =>
        i.entity_info?.id === this.yourEntityId
      );

      if (instance && instance.id) {
        // Load full workflow details
        this.workflowService.getInstance(instance.id).subscribe({
          next: (workflow) => {
            this.workflow = workflow;
            this.updateCurrentStepExecution();
            this.workflowLoading = false;
          },
          error: (err) => {
            console.error('Error loading workflow details:', err);
            this.workflowLoading = false;
          }
        });
      } else {
        this.workflowLoading = false;
      }
    },
    error: (err) => {
      console.error('Error loading workflow:', err);
      this.workflowLoading = false;
    }
  });
}

updateCurrentStepExecution(): void {
  if (!this.workflow?.step_executions) {
    this.currentStepExecution = null;
    return;
  }

  // Find the current pending step that the user can action
  this.currentStepExecution = this.workflow.step_executions.find(
    step => step.status === 'pending' &&
            step.workflow_step_detail?.step_order === this.workflow?.current_step_order &&
            step.can_action === true
  ) || null;
}
```

#### 1.6 Add Event Handlers

```typescript
onWorkflowApproved(): void {
  this.toastService.success('Approval successful');
  this.loadRequestDetails();  // Reload your entity data
  this.loadWorkflow();         // Reload workflow
}

onWorkflowRejected(): void {
  this.toastService.success('Request rejected');
  this.loadRequestDetails();  // Reload your entity data
  this.loadWorkflow();         // Reload workflow
}

onWorkflowDelegated(): void {
  this.toastService.success('Successfully delegated');
  this.loadWorkflow();         // Reload workflow
}
```

#### 1.7 Call loadWorkflow in ngOnInit

```typescript
ngOnInit(): void {
  this.route.params.subscribe(params => {
    this.yourEntityId = +params['id'];
    if (this.yourEntityId) {
      this.loadRequestDetails();
      this.loadWorkflow();  // Add this line
    }
  });
}
```

---

### Step 2: Update Component HTML Template

**File:** `your-module-detail.component.html`

Add this section where you want the workflow to appear (typically after the main details):

```html
<!-- Modern Workflow Status -->
<section class="detail-section" *ngIf="workflow || workflowLoading">
  <h3 class="section-title">
    <i class="bi bi-diagram-3"></i>
    Approval Workflow
  </h3>

  <!-- Loading State -->
  <div *ngIf="workflowLoading && !workflow" class="text-center py-3">
    <div class="spinner-border text-primary" role="status">
      <span class="visually-hidden">Loading workflow...</span>
    </div>
    <p class="text-muted mt-2">Loading workflow status...</p>
  </div>

  <!-- Workflow Status Timeline -->
  <app-workflow-status
    *ngIf="workflow && !workflowLoading"
    [workflowInstance]="workflow">
  </app-workflow-status>

  <!-- Approval Action Buttons -->
  <app-approval-actions
    *ngIf="currentStepExecution && !workflowLoading"
    [stepExecution]="currentStepExecution"
    (approved)="onWorkflowApproved()"
    (rejected)="onWorkflowRejected()"
    (delegated)="onWorkflowDelegated()">
  </app-approval-actions>

  <!-- No Workflow Message -->
  <div *ngIf="!workflow && !workflowLoading" class="alert alert-info">
    <i class="bi bi-info-circle"></i>
    No workflow has been initiated for this request yet.
  </div>
</section>
```

---

## 🎯 Quick Reference: Entity Types

When calling `workflowService.getInstances()`, use these entity type strings:

| Module | Entity Type String | Model Name |
|--------|-------------------|------------|
| Expense Claims | `expenseclaim` | ExpenseClaim |
| TRF | `travelrequest` | TravelRequest |
| Visa | `visarequest` | VisaRequest |
| Transport | `transportrequest` | TransportRequest |
| Accommodation | `accommodationrequest` | AccommodationRequest |

**Note:** These strings must match the Django model name (lowercase, no spaces).

---

## 📁 Files to Update for Each Module

### Expense Claims Module

**Files:**
- `frontend/src/app/features/expense-claims/components/claim-detail/claim-detail.component.ts`
- `frontend/src/app/features/expense-claims/components/claim-detail/claim-detail.component.html`

**Entity Type:** `expenseclaim`

### TRF Module

**Files:**
- `frontend/src/app/features/trf-management/components/trf-detail/trf-detail.component.ts`
- `frontend/src/app/features/trf-management/components/trf-detail/trf-detail.component.html`

**Entity Type:** `travelrequest`

### Visa Module

**Files:**
- `frontend/src/app/features/visa/components/visa-detail/visa-detail.component.ts`
- `frontend/src/app/features/visa/components/visa-detail/visa-detail.component.html`

**Entity Type:** `visarequest`

### Accommodation Module

**Files:**
- `frontend/src/app/features/accommodation/components/accommodation-detail/accommodation-detail.component.ts`
- `frontend/src/app/features/accommodation/components/accommodation-detail/accommodation-detail.component.html`

**Entity Type:** `accommodationrequest`

---

## 🔄 Complete Example: Expense Claims

### expense-claim-detail.component.ts

```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ExpenseClaimService, ExpenseClaimDetail } from '../../services/expense-claim.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { ApprovalActionsComponent } from '../../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../../../core/models/workflow.models';

@Component({
  selector: 'app-claim-detail',
  standalone: true,
  imports: [CommonModule, WorkflowStatusComponent, ApprovalActionsComponent],
  templateUrl: './claim-detail.component.html',
  styleUrls: ['./claim-detail.component.scss']
})
export class ClaimDetailComponent implements OnInit {
  claim: ExpenseClaimDetail | null = null;
  loading: boolean = true;
  error: string = '';
  claimId!: number;

  // Workflow properties
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;
  currentStepExecution: WorkflowStepExecution | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private claimService: ExpenseClaimService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.claimId = +params['id'];
      if (this.claimId) {
        this.loadClaimDetails();
        this.loadWorkflow();
      }
    });
  }

  loadClaimDetails(): void {
    this.loading = true;
    this.error = '';

    this.claimService.getClaimById(this.claimId).subscribe({
      next: (data) => {
        this.claim = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load claim: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading claim:', err);
      }
    });
  }

  loadWorkflow(): void {
    this.workflowLoading = true;

    this.workflowService.getInstances({
      entity_type: 'expenseclaim'
    }).subscribe({
      next: (instances) => {
        const instance = instances.find((i: any) =>
          i.entity_info?.id === this.claimId
        );

        if (instance && instance.id) {
          this.workflowService.getInstance(instance.id).subscribe({
            next: (workflow) => {
              this.workflow = workflow;
              this.updateCurrentStepExecution();
              this.workflowLoading = false;
            },
            error: (err) => {
              console.error('Error loading workflow details:', err);
              this.workflowLoading = false;
            }
          });
        } else {
          this.workflowLoading = false;
        }
      },
      error: (err) => {
        console.error('Error loading workflow:', err);
        this.workflowLoading = false;
      }
    });
  }

  updateCurrentStepExecution(): void {
    if (!this.workflow?.step_executions) {
      this.currentStepExecution = null;
      return;
    }

    this.currentStepExecution = this.workflow.step_executions.find(
      step => step.status === 'pending' &&
              step.workflow_step_detail?.step_order === this.workflow?.current_step_order &&
              step.can_action === true
    ) || null;
  }

  onWorkflowApproved(): void {
    this.toastService.success('Approval successful');
    this.loadClaimDetails();
    this.loadWorkflow();
  }

  onWorkflowRejected(): void {
    this.toastService.success('Request rejected');
    this.loadClaimDetails();
    this.loadWorkflow();
  }

  onWorkflowDelegated(): void {
    this.toastService.success('Successfully delegated');
    this.loadWorkflow();
  }

  // ... rest of your component methods
}
```

---

## 🚀 Testing Your Integration

### 1. Create a Test Request

1. Navigate to your module (e.g., Transport, Claims)
2. Create a new request
3. Submit the request

### 2. Check Workflow Creation

The workflow should be automatically created when the request is submitted. If not:

```bash
# Manually create workflow via Django shell
python manage.py shell

from workflows.models import WorkflowTemplate, WorkflowInstance
from transport.models import TransportRequest  # Change to your model

# Get the template
template = WorkflowTemplate.objects.get(module_name='transport', is_active=True)

# Get your request
request = TransportRequest.objects.get(id=1)

# Create workflow instance
instance = WorkflowInstance.objects.create(
    workflow_template=template,
    entity_type=template.entity_content_type,
    entity_id=request.id,
    initiated_by=request.created_by,
    status='in_progress'
)
```

### 3. View the Workflow

Navigate to the detail page of your request. You should see:

- **Workflow Timeline** - Visual representation of approval steps
- **Current Step** - Highlighted with pulsing animation
- **Action Buttons** - If you're assigned to the current step

### 4. Test Approvals

If you're assigned to a step:

1. Click **Approve** button
2. Optionally add comments
3. Confirm
4. Workflow should move to next step

### 5. Test Rejections

1. Click **Reject** button
2. Add required comments
3. Confirm
4. Workflow should mark request as rejected

### 6. Test Delegation

1. Click **Delegate** button
2. Enter user ID to delegate to
3. Add optional reason
4. Confirm
5. Workflow step should be reassigned

---

## 🐛 Troubleshooting

### Workflow Not Loading

**Problem:** Workflow section shows "No workflow has been initiated"

**Solutions:**
1. Check if workflow template exists for your module
   ```bash
   python manage.py shell
   from workflows.models import WorkflowTemplate
   WorkflowTemplate.objects.filter(module_name='your_module', is_active=True)
   ```

2. Check if workflow instance was created
   ```sql
   SELECT * FROM workflows_workflowinstance WHERE entity_id = YOUR_REQUEST_ID;
   ```

3. Verify entity_type string matches your model name (lowercase)

### Action Buttons Not Showing

**Problem:** Workflow shows but no action buttons

**Possible Causes:**
1. User is not assigned to current step
2. Step is already completed
3. `can_action` is false

**Check:**
```typescript
console.log('Current step execution:', this.currentStepExecution);
console.log('Can action?', this.currentStepExecution?.can_action);
```

### Workflow Not Progressing After Approval

**Problem:** Approved but stuck on same step

**Check Backend:**
```python
# Check step execution status
from workflows.models import WorkflowStepExecution
steps = WorkflowStepExecution.objects.filter(workflow_instance_id=YOUR_INSTANCE_ID)
for step in steps:
    print(f"Step {step.workflow_step.step_order}: {step.status}")
```

### Console Errors

**Error:** `Cannot find module 'WorkflowService'`

**Solution:** Check import path is correct (4 levels up from component)

**Error:** `Property 'workflow' does not exist`

**Solution:** Add workflow properties to component class

---

## 📊 Expected Workflow Behavior

### When Request is Created (Draft)
- No workflow exists yet
- Section shows "No workflow has been initiated"

### When Request is Submitted
- Backend signal creates workflow instance
- Workflow starts at Step 1
- First approver is auto-assigned

### When User Opens Detail Page
- If assigned to current step → Shows action buttons
- If not assigned → Shows "You do not have permission to action this step"
- Completed steps → Show checkmarks and actioner info
- Pending steps → Show gray circles

### After Approval Action
- Current step marked as approved
- Next step becomes current
- Next approver auto-assigned
- Email notification sent (if configured)

### After Rejection Action
- Current step marked as rejected
- Workflow status set to 'rejected'
- Request status updated
- No further steps processed

### After Delegation
- Step reassigned to delegate user
- Original user no longer has access
- Delegate receives notification

---

## 🎨 Customization Options

### Compact Mode for List Views

```html
<app-workflow-status
  [workflowInstanceId]="item.workflow_id"
  [compact]="true">
</app-workflow-status>
```

### Custom Styling

Override styles in your component's SCSS:

```scss
::ng-deep {
  .workflow-status {
    // Custom timeline styles
    .timeline-step.current {
      border-color: your-color;
    }
  }

  .approval-actions {
    // Custom button styles
    .btn-success {
      background-color: your-color;
    }
  }
}
```

### Hide Specific Buttons

Edit `approval-actions.component.html` to conditionally hide buttons:

```html
<button
  *ngIf="canAction && yourCustomCondition"
  class="btn btn-success"
  (click)="onApprove()">
  Approve
</button>
```

---

## ✅ Integration Checklist

For each module, complete this checklist:

- [ ] Import WorkflowService, components, and models
- [ ] Add components to imports array
- [ ] Add workflow properties (workflow, workflowLoading, currentStepExecution)
- [ ] Inject WorkflowService in constructor
- [ ] Add loadWorkflow() method with correct entity_type
- [ ] Add updateCurrentStepExecution() method
- [ ] Add event handler methods (onWorkflowApproved, etc.)
- [ ] Call loadWorkflow() in ngOnInit
- [ ] Add workflow section to HTML template
- [ ] Test workflow creation
- [ ] Test approval flow
- [ ] Test rejection flow
- [ ] Test delegation
- [ ] Verify permissions work correctly
- [ ] Test on mobile/responsive view

---

## 📚 Related Documentation

- **Backend API:** `BACKEND_WORKFLOW_COMPLETE.md`
- **Frontend Components:** `FRONTEND_WORKFLOW_PROGRESS.md`
- **Workflow Models:** `frontend/src/app/core/models/workflow.models.ts`
- **Workflow Service:** `frontend/src/app/core/services/workflow.service.ts`

---

## 🎯 Next Steps

After integrating workflows into all modules:

1. **Create Pending Approvals Dashboard** - Central view of all pending approvals
2. **Add Email Notifications** - Notify users of pending approvals
3. **Create Workflow Admin UI** - Allow admins to create/edit workflow templates
4. **Add Workflow Reports** - Analytics on approval times, bottlenecks, etc.
5. **Implement Auto-Escalation** - Automatically escalate overdue approvals

---

## ❓ Need Help?

If you encounter issues:

1. Check the Transport module implementation as reference
2. Review console logs for errors
3. Check Django admin for workflow data
4. Verify user permissions and role assignments
5. Test API endpoints directly using Django REST Framework browsable API

Good luck with your integration!
