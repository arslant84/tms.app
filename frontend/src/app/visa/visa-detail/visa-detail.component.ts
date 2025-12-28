import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { VisaService, VisaApplication, VisaApprovalStep, VisaDocument } from '../visa.service';
import { WorkflowService } from '../../core/services/workflow.service';
import { ApprovalActionsComponent } from '../../shared/components/approval-actions/approval-actions.component';
import { WorkflowStatusComponent } from '../../shared/components/workflow-status/workflow-status.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../core/models/workflow.models';

@Component({
  selector: 'app-visa-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, ApprovalActionsComponent, WorkflowStatusComponent],
  templateUrl: './visa-detail.component.html',
  styleUrl: './visa-detail.component.scss'
})
export class VisaDetailComponent implements OnInit {
  application!: VisaApplication;
  approvalSteps: VisaApprovalStep[] = [];
  documents: VisaDocument[] = [];
  isLoading = true;
  applicationId!: number;

  // Workflow properties
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;
  currentStepExecution: WorkflowStepExecution | null = null;

  private readonly EDITABLE_STATUSES = ['Draft', 'Rejected'];
  private readonly CANCELLABLE_STATUSES = ['Pending'];

  // Statuses that indicate the request has been approved and should not be editable
  private readonly APPROVED_KEYWORDS = ['Approved', 'Completed', 'Assigned'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private visaService: VisaService,
    public workflowService: WorkflowService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.applicationId = +params['id'];
      if (this.applicationId) {
        this.loadApplicationDetails();
        this.loadWorkflow();
      }
    });
  }

  loadApplicationDetails(): void {
    this.isLoading = true;
    this.visaService.getApplicationById(this.applicationId).subscribe({
      next: (application) => {
        this.application = application;
        this.isLoading = false;
        this.loadApprovalSteps();
        this.loadDocuments();
      },
      error: (error) => {
        this.isLoading = false;
        alert('Failed to load visa application details');
      }
    });
  }


  loadWorkflow(): void {
    this.workflowLoading = true;

    // Try to get workflow for this visa application
    this.workflowService.getInstances({
      entity_type: 'visaapplication'
    }).subscribe({
      next: (response: any) => {
        // Check if response is an array or paginated object
        const instances = Array.isArray(response) ? response : (response.results || []);

        // Find workflow instance for this specific request
        const instance = instances.find((i: any) =>
          i.object_id === this.applicationId ||
          i.entity_info?.id === this.applicationId ||
          i.entity_id === this.applicationId
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
              this.workflowLoading = false;
            }
          });
        } else {
          this.workflowLoading = false;
        }
      },
      error: (err) => {
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

  onWorkflowApproved(): void {
    alert('Approval successful');
    this.loadApplicationDetails();
    this.loadWorkflow();
  }

  onWorkflowRejected(): void {
    alert('Request rejected');
    this.loadApplicationDetails();
    this.loadWorkflow();
  }

  onWorkflowDelegated(): void {
    alert('Successfully delegated');
    this.loadWorkflow();
  }

  loadApprovalSteps(): void {
    this.visaService.getApprovalSteps(this.applicationId).subscribe({
      next: (steps) => {
        this.approvalSteps = steps;
      },
      error: (error) => {
      }
    });
  }

  loadDocuments(): void {
    this.visaService.getDocuments(this.applicationId).subscribe({
      next: (documents) => {
        this.documents = documents;
      },
      error: (error) => {
      }
    });
  }

  canEdit(): boolean {
    if (!this.application?.status) return false;

    const status = this.application.status;

    // Check if status is in editable list
    if (this.EDITABLE_STATUSES.includes(status)) {
      return true;
    }

    // Check if status contains any approved keywords - if so, not editable
    const isApproved = this.APPROVED_KEYWORDS.some(keyword => status.includes(keyword));
    if (isApproved) {
      return false;
    }

    // Allow editing for pending statuses that haven't been approved yet
    if (status.includes('Pending')) {
      return true;
    }

    return false;
  }

  canCancel(): boolean {
    return this.CANCELLABLE_STATUSES.includes(this.application?.status || '');
  }

  onEdit(): void {
    // Check if request can be edited
    if (!this.canEdit()) {
      alert('This visa application cannot be edited because it has been approved. Approved requests can only be viewed, not modified.');
      return;
    }

    this.router.navigate(['/visa', this.applicationId, 'edit']);
  }

  onCancel(): void {
    if (confirm('Are you sure you want to cancel this visa application?')) {
      this.visaService.cancelApplication(this.applicationId).subscribe({
        next: () => {
          alert('Visa application cancelled successfully');
          this.loadApplicationDetails();
        },
        error: (error) => {
          alert('Failed to cancel visa application');
        }
      });
    }
  }

  onPrint(): void {
    window.print();
  }

  onDelete(): void {
    if (confirm('Are you sure you want to delete this visa application? This action cannot be undone.')) {
      this.visaService.deleteApplication(this.applicationId).subscribe({
        next: () => {
          alert('Visa application deleted successfully');
          this.router.navigate(['/visa']);
        },
        error: (error) => {
          alert('Failed to delete visa application');
        }
      });
    }
  }

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }

  formatDateTime(dateString: string | null | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getStatusBadgeClass(status: string): string {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('approved') || statusLower.includes('completed')) return 'badge-success';
    if (statusLower.includes('rejected')) return 'badge-danger';
    if (statusLower.includes('pending')) return 'badge-warning';
    if (statusLower.includes('draft')) return 'badge-secondary';
    if (statusLower.includes('cancelled')) return 'badge-secondary';
    return 'badge-info';
  }

  getWorkflowStatus(): string {
    if (!this.workflow) return '';

    const status = this.workflow.status;
    const currentStep = this.workflow.current_step_order;
    const totalSteps = this.workflow.step_executions?.length || 0;

    if (status === 'approved') return 'Approved';
    if (status === 'rejected') return 'Rejected';
    if (status === 'cancelled') return 'Cancelled';
    if (status === 'in_progress') {
      if (currentStep && totalSteps) {
        return `In Progress (Step ${currentStep} of ${totalSteps})`;
      }
      return 'In Progress';
    }
    if (status === 'pending') return 'Pending Approval';

    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  getWorkflowStatusClass(): string {
    if (!this.workflow) return 'badge-secondary';

    const status = this.workflow.status;
    if (status === 'approved') return 'badge-success';
    if (status === 'rejected') return 'badge-danger';
    if (status === 'cancelled') return 'badge-secondary';
    if (status === 'in_progress' || status === 'pending') return 'badge-warning';

    return 'badge-info';
  }

}
