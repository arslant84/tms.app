import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import {
  VisaService,
  VisaApplication,
  VisaApprovalStep,
  VisaDocument,
} from '../../services/visa.service';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { RbacService } from '../../../../core/services/rbac.service';
import { ApprovalActionsComponent } from '../../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../../../core/models/workflow.models';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';

@Component({
  selector: 'app-visa-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    ApprovalActionsComponent,
    WorkflowStatusComponent,
    LoadingSpinnerComponent,
  ],
  templateUrl: './visa-detail.component.html',
  styleUrl: './visa-detail.component.scss',
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
    public workflowService: WorkflowService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private rbacService: RbacService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService,
    private errorHandler: HttpErrorHandlerService
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
    // Check if user has admin view permissions for visa module
    const hasAdminView =
      this.rbacService.hasPermission('view_all_visa') ||
      this.rbacService.hasPermission('approve_visa');
    this.visaService.getApplicationById(this.applicationId, hasAdminView).subscribe({
      next: application => {
        this.application = application;
        this.isLoading = false;
        this.loadApprovalSteps();
        this.loadDocuments();
      },
      error: () => {
        this.isLoading = false;
        this.toastService.error('Failed to load visa application details');
      },
    });
  }

  loadWorkflow(): void {
    this.workflowLoading = true;

    // Try to get workflow for this visa application
    this.workflowService
      .getInstances({
        entity_type: 'visaapplication',
        object_id: this.applicationId,
      })
      .subscribe({
        next: instances => {
          // Find workflow instance for this specific request
          const instance = instances.find(
            i => i.object_id === this.applicationId || i.entity_info?.id === this.applicationId
          );

          if (instance && instance.id) {
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
    this.loadApplicationDetails();
    this.loadWorkflow();
  }

  onWorkflowRejected(): void {
    this.toastService.info('Request rejected');
    this.loadApplicationDetails();
    this.loadWorkflow();
  }

  onWorkflowDelegated(): void {
    this.toastService.success('Successfully delegated');
    this.loadWorkflow();
  }

  loadApprovalSteps(): void {
    this.visaService.getApprovalSteps(this.applicationId).subscribe({
      next: steps => {
        this.approvalSteps = steps;
      },
    });
  }

  loadDocuments(): void {
    this.visaService.getDocuments(this.applicationId).subscribe({
      next: documents => {
        this.documents = documents;
      },
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
    const status = this.application?.status || '';
    // Allow cancel for any status that contains 'Pending' and is not approved
    if (status.includes('Pending')) {
      const isApproved = this.APPROVED_KEYWORDS.some(keyword => status.includes(keyword));
      return !isApproved;
    }
    return false;
  }

  onEdit(): void {
    // Check if request can be edited
    if (!this.canEdit()) {
      this.toastService.warning(
        'This visa application cannot be edited because it has been approved. Approved requests can only be viewed, not modified.'
      );
      return;
    }

    this.router.navigate(['/visa', this.applicationId, 'edit']);
  }

  onCancel(): void {
    this.confirmationService
      .confirm({
        title: 'Cancel Application',
        message: 'Are you sure you want to cancel this visa application?',
        confirmText: 'Cancel Application',
        type: 'warning',
      })
      .subscribe(confirmed => {
        if (confirmed) {
          this.visaService.cancelApplication(this.applicationId).subscribe({
            next: () => {
              this.toastService.success('Visa application cancelled successfully');
              this.loadApplicationDetails();
            },
            error: () => {
              this.toastService.error('Failed to cancel visa application');
            },
          });
        }
      });
  }

  onExportPdf(): void {
    if (!this.applicationId) return;

    this.visaService.exportToPdf(this.applicationId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `Visa-${this.application?.request_number || this.applicationId}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('PDF exported successfully');
      },
      error: (err: HttpErrorResponse) => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to export PDF'));
      },
    });
  }

  onDelete(): void {
    this.confirmationService.confirmDelete('this visa application').subscribe(confirmed => {
      if (confirmed) {
        this.visaService.deleteApplication(this.applicationId).subscribe({
          next: () => {
            this.toastService.success('Visa application deleted successfully');
            this.router.navigate(['/visa']);
          },
          error: () => {
            this.toastService.error('Failed to delete visa application');
          },
        });
      }
    });
  }

  getStatusBadgeClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
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
    return this.statusUtils.getWorkflowStatusClass(this.workflow?.status);
  }
}
