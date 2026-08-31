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
import { AuthService } from '../../../../core/services/auth.service';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { WorkflowInstance } from '../../../../core/models/workflow.models';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';

@Component({
  selector: 'app-visa-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, WorkflowStatusComponent, LoadingSpinnerComponent],
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
    private authService: AuthService,
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

  /**
   * The signed-in user created this application. Owner-only actions
   * (Edit/Cancel/Delete) are gated on this so a viewer with read access -
   * an approver, an admin browsing, anyone else - can't act on someone
   * else's application.
   */
  get isOwner(): boolean {
    const currentUserId = this.authService.getCurrentUserId();
    return currentUserId != null && this.application?.user === currentUserId;
  }

  canEdit(): boolean {
    if (!this.isOwner) return false;
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
    if (!this.isOwner) return false;
    const status = this.application?.status || '';
    // Allow cancel for any status that contains 'Pending' and is not approved
    if (status.includes('Pending')) {
      const isApproved = this.APPROVED_KEYWORDS.some(keyword => status.includes(keyword));
      return !isApproved;
    }
    return false;
  }

  /**
   * Delete was previously always shown regardless of status/ownership -
   * matching the other three modules' Delete guard (Draft/Rejected only,
   * owner only), the same gap fixed there.
   */
  canDelete(): boolean {
    if (!this.isOwner) return false;
    return this.EDITABLE_STATUSES.includes(this.application?.status || '');
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
