import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { TransportService } from '../../services/transport.service';
import { TransportRequestForm } from '../../models/transport.model';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { ApprovalActionsComponent } from '../../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../../../core/models/workflow.models';

@Component({
  selector: 'app-transport-detail',
  standalone: true,
  imports: [CommonModule, ApprovalActionsComponent, WorkflowStatusComponent],
  templateUrl: './transport-detail.component.html',
  styleUrls: ['./transport-detail.component.scss']
})
export class TransportDetailComponent implements OnInit {
  request: TransportRequestForm | null = null;
  loading: boolean = true;
  error: string = '';
  requestId!: number;

  // Workflow properties
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;
  currentStepExecution: WorkflowStepExecution | null = null;

  // Status-based visibility constants
  private readonly EDITABLE_STATUSES = ['Draft', 'Rejected'];
  private readonly CANCELLABLE_STATUSES = ['Pending'];
  private readonly DELETABLE_STATUSES = ['Draft', 'Rejected'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private transportService: TransportService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.requestId = +params['id'];
      if (this.requestId) {
        this.loadRequestDetails();
        this.loadWorkflow();
      }
    });
  }

  loadRequestDetails(): void {
    this.loading = true;
    this.error = '';

    this.transportService.getRequestById(this.requestId).subscribe({
      next: (data) => {
        this.request = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load transport request: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading request:', err);
      }
    });
  }

  loadWorkflow(): void {
    this.workflowLoading = true;

    // Try to get workflow for this transport request
    this.workflowService.getInstances({
      entity_type: 'transportrequest'
    }).subscribe({
      next: (response: any) => {
        // Check if response is an array or paginated object
        const instances = Array.isArray(response) ? response : (response.results || []);

        // Find workflow instance for this specific request
        const instance = instances.find((i: any) =>
          i.entity_info?.id === this.requestId ||
          i.entity_id === this.requestId
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

  onWorkflowApproved(): void {
    this.toastService.success('Approval successful');
    this.loadRequestDetails();
    this.loadWorkflow();
  }

  onWorkflowRejected(): void {
    this.toastService.success('Request rejected');
    this.loadRequestDetails();
    this.loadWorkflow();
  }

  onWorkflowDelegated(): void {
    this.toastService.success('Successfully delegated');
    this.loadWorkflow();
  }

  canEdit(): boolean {
    return this.EDITABLE_STATUSES.includes(this.request?.status || '');
  }

  canCancel(): boolean {
    return this.CANCELLABLE_STATUSES.includes(this.request?.status || '');
  }

  canDelete(): boolean {
    return this.DELETABLE_STATUSES.includes(this.request?.status || '');
  }

  getStatusClass(): string {
    const status = this.request?.status?.toLowerCase() || '';
    if (status.includes('approved') || status.includes('completed')) return 'badge-success';
    if (status.includes('rejected')) return 'badge-danger';
    if (status.includes('pending')) return 'badge-warning';
    if (status.includes('draft')) return 'badge-secondary';
    if (status.includes('cancelled')) return 'badge-secondary';
    return 'badge-info';
  }

  goBack(): void {
    this.router.navigate(['/transport']);
  }

  onEdit(): void {
    this.router.navigate(['/transport/edit', this.requestId]);
  }

  onCancel(): void {
    this.confirmationService.confirmDestructive('Cancel', 'this transport request').subscribe(confirmed => {
      if (confirmed) {
        this.transportService.cancelRequest(this.requestId).subscribe({
          next: () => {
            this.toastService.success('Transport request cancelled successfully');
            this.router.navigate(['/transport']);
          },
          error: (err) => {
            this.toastService.error('Failed to cancel request: ' + (err.error?.message || err.message));
            console.error('Error cancelling request:', err);
          }
        });
      }
    });
  }

  onDelete(): void {
    this.confirmationService.confirmDelete('this transport request').subscribe(confirmed => {
      if (confirmed) {
        this.transportService.deleteRequest(this.requestId).subscribe({
          next: () => {
            this.toastService.success('Transport request deleted successfully');
            this.router.navigate(['/transport']);
          },
          error: (err) => {
            this.toastService.error('Failed to delete request: ' + (err.error?.message || err.message));
            console.error('Error deleting request:', err);
          }
        });
      }
    });
  }

  onPrint(): void {
    window.print();
  }

  formatCurrency(amount: number | undefined, currency: string = 'USD'): string {
    if (!amount && amount !== 0) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  formatTime(timeString: string | undefined): string {
    if (!timeString) return 'N/A';
    return timeString;
  }
}
