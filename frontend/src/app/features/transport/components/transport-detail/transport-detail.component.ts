import { Component, type OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TransportService } from '../../services/transport.service';
import type { TransportRequestForm } from '../../models/transport.model';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { ApprovalActionsComponent } from '../../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import type {
  WorkflowInstance,
  WorkflowInstanceList,
  WorkflowStepExecution,
} from '../../../../core/models/workflow.models';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { AuthService } from '../../../../core/services/auth.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';

@Component({
  selector: 'app-transport-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    ApprovalActionsComponent,
    WorkflowStatusComponent,
    LoadingSpinnerComponent,
  ],
  templateUrl: './transport-detail.component.html',
  styleUrls: ['./transport-detail.component.scss'],
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

  // Statuses that indicate the request has been approved and should not be editable
  private readonly APPROVED_KEYWORDS = ['Approved', 'Completed', 'Assigned'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private transportService: TransportService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService,
    private appSettingsService: AppSettingsService,
    private authService: AuthService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService,
    private errorHandler: HttpErrorHandlerService
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
      next: data => {
        this.request = data;
        this.loading = false;
      },
      error: err => {
        this.error =
          'Failed to load transport request: ' +
          (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
      },
    });
  }

  loadWorkflow(): void {
    this.workflowLoading = true;

    // Try to get workflow for this transport request
    this.workflowService
      .getInstances({
        entity_type: 'transportrequest',
        object_id: this.requestId,
      })
      .subscribe({
        next: (instances: WorkflowInstanceList[]) => {
          // Find workflow instance for this specific request
          const instance = instances.find(
            i => i.object_id === this.requestId || i.entity_info?.id === this.requestId
          );

          if (instance?.id) {
            // Load full workflow details
            this.workflowService.getInstance(instance.id).subscribe({
              next: workflow => {
                this.workflow = workflow;
                this.updateCurrentStepExecution();
                this.workflowLoading = false;
              },
              error: () => {
                this.workflowLoading = false;
              },
            });
          } else {
            this.workflowLoading = false;
          }
        },
        error: () => {
          this.workflowLoading = false;
        },
      });
  }

  updateCurrentStepExecution(): void {
    if (!this.workflow?.step_executions) {
      this.currentStepExecution = null;
      return;
    }

    // Find the current pending step that the user can action
    this.currentStepExecution =
      this.workflow.step_executions.find(
        step =>
          step.status === 'pending' &&
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

  /**
   * The signed-in user has a pending, actionable workflow step on this
   * request right now - i.e. they're the one being asked to approve/reject
   * it. Reuses the same can_action signal the approval-actions UI already
   * trusts, rather than a separate role check.
   */
  get isCurrentApprover(): boolean {
    return !!this.currentStepExecution;
  }

  /**
   * The signed-in user created this request. Owner-only actions
   * (Edit/Cancel/Delete) are gated on this so a viewer with read access -
   * an approver, an admin browsing, anyone else - can't act on someone
   * else's request.
   */
  get isOwner(): boolean {
    const currentUserId = this.authService.getCurrentUserId();
    return currentUserId != null && this.request?.requestorId === currentUserId;
  }

  canEdit(): boolean {
    if (!this.isOwner || this.isCurrentApprover) return false;
    if (!this.request?.status) return false;

    const status = this.request.status;

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
    if (!this.isOwner || this.isCurrentApprover) return false;
    const status = this.request?.status || '';
    // Allow cancel for any status that contains 'Pending' and is not approved
    if (status.includes('Pending')) {
      const isApproved = this.APPROVED_KEYWORDS.some(keyword => status.includes(keyword));
      return !isApproved;
    }
    return false;
  }

  canDelete(): boolean {
    if (!this.isOwner || this.isCurrentApprover) return false;
    return this.DELETABLE_STATUSES.includes(this.request?.status || '');
  }

  getStatusClass(): string {
    return this.statusUtils.getStatusBadgeClass(this.request?.status);
  }

  getWorkflowStatus(): string {
    if (!this.workflow) return '';

    const status = this.workflow.status;
    const currentStep = this.workflow.current_step_order;
    // The template's real, configured step count - not step_executions.length,
    // which only counts steps reached so far (see trf-detail.component.ts's
    // getWorkflowStatus for the full explanation).
    const totalSteps =
      this.workflow.workflow_template_detail?.step_count ||
      this.workflow.step_executions?.length ||
      0;

    if (status === 'approved') return 'Approved';
    if (status === 'rejected') return 'Rejected';
    if (status === 'cancelled') return 'Cancelled';
    if (status === 'in_progress') return `Pending Approval (Step ${currentStep} of ${totalSteps})`;
    if (status === 'pending') return 'Pending Approval';

    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  getWorkflowStatusClass(): string {
    return this.statusUtils.getWorkflowStatusClass(this.workflow?.status);
  }

  goBack(): void {
    this.router.navigate(['/transport']);
  }

  // Check if there's a TRF link to display (i.e. this was created via TSR embedding)
  hasTrfLink(): boolean {
    return !!this.request?.trfId;
  }

  getTrfLink(): string {
    return `/trf/${this.request?.trfId}`;
  }

  onEdit(): void {
    // Check if request can be edited
    if (!this.canEdit()) {
      this.toastService.error(
        'This transport request cannot be edited because it has been approved. ' +
          'Approved requests can only be viewed, not modified.'
      );
      return;
    }

    this.router.navigate(['/transport/edit', this.requestId]);
  }

  onCancel(): void {
    this.confirmationService
      .confirmCancel(
        'Are you sure you want to cancel this transport request? This action cannot be undone.'
      )
      .subscribe(confirmed => {
        if (confirmed) {
          this.transportService.cancelRequest(this.requestId).subscribe({
            next: () => {
              this.toastService.success('Transport request cancelled successfully');
              this.router.navigate(['/transport']);
            },
            error: err => {
              this.toastService.error(
                this.errorHandler.getErrorMessage(err, 'Failed to cancel request')
              );
            },
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
          error: err => {
            this.toastService.error(
              this.errorHandler.getErrorMessage(err, 'Failed to delete request')
            );
          },
        });
      }
    });
  }

  onExportPdf(): void {
    if (!this.requestId) return;

    this.transportService.exportToPdf(this.requestId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `Transport-${this.request?.request_number || this.requestId}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('PDF exported successfully');
      },
      error: (err: HttpErrorResponse) => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to export PDF'));
      },
    });
  }

  formatCurrency(amount: number | null | undefined, currency?: string | null): string {
    if (amount === null || amount === undefined || Number.isNaN(amount)) {
      return 'N/A';
    }

    const currencyCode = currency || this.appSettingsService.getDefaultCurrency();

    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(amount);
    } catch {
      return `${currencyCode} ${amount.toFixed(2)}`;
    }
  }

  formatTime(timeString: string | undefined): string {
    if (!timeString) return 'N/A';
    return timeString;
  }
}
