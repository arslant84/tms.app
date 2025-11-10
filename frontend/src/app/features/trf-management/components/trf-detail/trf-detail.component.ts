import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { TrfService } from '../../services/trf.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { ApprovalActionsComponent } from '../../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../../../core/models/workflow.models';

@Component({
  selector: 'app-trf-detail',
  standalone: true,
  imports: [CommonModule, WorkflowStatusComponent, ApprovalActionsComponent],
  templateUrl: './trf-detail.component.html',
  styleUrls: ['./trf-detail.component.scss']
})
export class TrfDetailComponent implements OnInit {
  trfData: any = null;
  loading: boolean = true;
  error: string = '';
  trfId!: number;

  // Workflow properties
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;
  currentStepExecution: WorkflowStepExecution | null = null;

  // Status-based visibility constants
  // Editable: Draft, Rejected, or any Pending status (before approval)
  private readonly CANCELLABLE_STATUSES = ['Pending Department Focal', 'Pending HOD', 'Pending Travel Desk'];
  private readonly DELETABLE_STATUSES = ['Draft', 'Rejected'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private trfService: TrfService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService
  ) {}

  ngOnInit(): void {
    // Get TRF ID from route params
    this.route.params.subscribe(params => {
      this.trfId = +params['id'];
      if (this.trfId) {
        this.loadTrfDetails();
        this.loadWorkflow();
      }
    });
  }

  loadTrfDetails(): void {
    this.loading = true;
    this.error = '';

    // Fetch TRF details from the backend using TrfService
    this.trfService.getTrfById(this.trfId).subscribe({
      next: (data) => {
        this.trfData = this.transformTrfData(data);
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load TRF details: ' + (err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading TRF:', err);
      }
    });
  }

  /**
   * Transform backend data to match the view structure
   */
  private transformTrfData(data: any): any {
    return {
      id: data.id,
      requestNumber: data.request_number || data.requestNumber,
      travelType: data.travel_type || data.travelType,
      status: data.status,
      requestorName: data.requestor_name || data.requestorName,
      staffId: data.staff_id || data.staffId,
      department: data.department,
      position: data.position,
      costCenter: data.cost_center || data.costCenter,
      telEmail: data.tel_email || data.telEmail,
      purpose: data.purpose,
      additionalComments: data.additional_comments || data.additionalComments,
      estimatedCost: data.estimated_cost || data.estimatedCost || 0,
      // External party fields
      externalPartyName: data.external_party_name || data.externalPartyName,
      externalPartyOrganization: data.external_party_organization || data.externalPartyOrganization,
      externalRefToAuthorityLetter: data.external_ref_to_authority_letter || data.externalRefToAuthorityLetter,
      externalCostCenter: data.external_cost_center || data.externalCostCenter,
      // Nested data (will be loaded separately or included in response)
      // Backend uses 'itinerary_segments', but fallback to 'itinerary'
      itinerary: data.itinerary_segments || data.itinerary || [],
      mealSelections: data.daily_meals || data.daily_meal_selections || data.mealSelections || [],
      passportDetails: data.passport_details || data.passportDetails,
      bankDetails: data.advance_bank_details || data.bankDetails,
      advanceAmounts: data.advance_amount_items || data.advanceAmounts || [],
      approvalSteps: data.approval_steps || data.approvalSteps || [],
      createdAt: data.created_at || data.createdAt,
      updatedAt: data.updated_at || data.updatedAt,
      submittedAt: data.submitted_at || data.submittedAt
    };
  }

  /**
   * Check if TRF is for external parties
   */
  get isExternal(): boolean {
    return this.trfData?.travelType === 'External Parties';
  }

  /**
   * Check if TRF is overseas or home leave
   */
  get isOverseas(): boolean {
    return this.trfData?.travelType === 'Overseas' || this.trfData?.travelType === 'Home Leave';
  }

  /**
   * Check if TRF is domestic
   */
  get isDomestic(): boolean {
    return this.trfData?.travelType === 'Domestic';
  }

  /**
   * Check if TRF can be edited based on status
   * Allow editing for: Draft, Rejected, or any Pending status
   */
  canEdit(): boolean {
    if (!this.trfData?.status) return false;

    const status = this.trfData.status;
    // Allow editing if status is Draft, Rejected, or starts with Pending
    return status === 'Draft' ||
           status === 'Rejected' ||
           status.startsWith('Pending');
  }

  /**
   * Check if TRF can be cancelled based on status
   */
  canCancel(): boolean {
    return this.CANCELLABLE_STATUSES.includes(this.trfData?.status);
  }

  /**
   * Check if TRF can be deleted based on status
   * Only allow deletion for Draft and Rejected statuses
   */
  canDelete(): boolean {
    if (!this.trfData?.status) return false;
    return this.DELETABLE_STATUSES.includes(this.trfData.status);
  }

  /**
   * Get status badge class
   */
  getStatusClass(): string {
    const status = this.trfData?.status?.toLowerCase() || '';
    if (status.includes('approved')) return 'badge-success';
    if (status.includes('rejected')) return 'badge-danger';
    if (status.includes('pending')) return 'badge-warning';
    if (status.includes('draft')) return 'badge-secondary';
    return 'badge-info';
  }

  /**
   * Format date for display
   */
  formatDate(date: string | Date | null | undefined): string {
    if (!date) return 'N/A';
    try {
      const d = typeof date === 'string' ? new Date(date) : date;
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return 'Invalid Date';
    }
  }

  /**
   * Format time for display
   */
  formatTime(time: string | null | undefined): string {
    if (!time) return 'N/A';
    try {
      // Handle HH:MM or HH:MM:SS format
      const timeMatch = time.match(/^([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$/);
      if (!timeMatch) return 'N/A';

      const [, hours, minutes] = timeMatch;
      const date = new Date();
      date.setHours(parseInt(hours), parseInt(minutes));
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'N/A';
    }
  }

  /**
   * Format number for display
   */
  formatNumber(num: number | string | null | undefined, decimals: number = 0): string {
    if (num === null || num === undefined || String(num).trim() === '') return 'N/A';
    const parsedNum = Number(num);
    return isNaN(parsedNum) ? String(num) : parsedNum.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  /**
   * Calculate meal totals
   */
  getMealTotal(mealType: string): number {
    if (!this.trfData?.mealSelections) return 0;
    return this.trfData.mealSelections.reduce((acc: number, meal: any) => {
      return acc + (meal[mealType] ? 1 : 0);
    }, 0);
  }

  /**
   * Navigate back to list
   */
  goBack(): void {
    this.router.navigate(['/trf']);
  }

  /**
   * Edit TRF
   */
  onEdit(): void {
    this.router.navigate(['/trf/edit', this.trfId]);
  }

  /**
   * Cancel TRF
   */
  onCancel(): void {
    this.confirmationService.confirmDestructive('Cancel', 'this TRF').subscribe(confirmed => {
      if (confirmed) {
        // Call the cancel action endpoint using TrfService
        this.trfService.cancelTrf(this.trfId).subscribe({
          next: () => {
            this.toastService.success('TRF cancelled successfully');
            this.router.navigate(['/trf']);
          },
          error: (err) => {
            this.toastService.error('Failed to cancel TRF: ' + (err.message || 'Unknown error'));
            console.error('Error cancelling TRF:', err);
          }
        });
      }
    });
  }

  /**
   * Delete TRF
   */
  onDelete(): void {
    this.confirmationService.confirmDelete('this TRF').subscribe(confirmed => {
      if (confirmed) {
        // Call delete endpoint using TrfService
        this.trfService.deleteTrf(this.trfId).subscribe({
          next: () => {
            this.toastService.success('TRF deleted successfully');
            this.router.navigate(['/trf']);
          },
          error: (err) => {
            this.toastService.error('Failed to delete TRF: ' + (err.message || 'Unknown error'));
            console.error('Error deleting TRF:', err);
          }
        });
      }
    });
  }

  /**
   * Print TRF
   */
  onPrint(): void {
    window.print();
  }

  /**
   * Export to PDF
   */
  onExportPdf(): void {
    this.trfService.exportTrfToPdf(this.trfId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `TRF-${this.trfId}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('PDF exported successfully');
      },
      error: (err: any) => {
        this.toastService.error('Failed to export PDF: ' + (err.error?.message || err.message || 'Unknown error'));
        console.error('Error exporting PDF:', err);
      }
    });
  }

  // ==================== Workflow Methods ====================

  loadWorkflow(): void {
    this.workflowLoading = true;

    this.workflowService.getInstances({
      entity_type: 'travelrequest'
    }).subscribe({
      next: (response: any) => {
        // Handle both paginated response and array response
        const instances = Array.isArray(response) ? response : (response.results || []);

        const instance = instances.find((i: any) =>
          i.entity_info?.id === this.trfId
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
    this.loadTrfDetails();
    this.loadWorkflow();
  }

  onWorkflowRejected(): void {
    this.toastService.success('Request rejected');
    this.loadTrfDetails();
    this.loadWorkflow();
  }

  onWorkflowDelegated(): void {
    this.toastService.success('Successfully delegated');
    this.loadWorkflow();
  }
}
