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
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';

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
  private readonly EDITABLE_STATUSES = ['Draft', 'Rejected'];
  private readonly CANCELLABLE_STATUSES = ['Pending Department Focal', 'Pending HOD', 'Pending Travel Desk'];
  private readonly DELETABLE_STATUSES = ['Draft', 'Rejected'];

  // Statuses that indicate the request has been approved and should not be editable
  private readonly APPROVED_KEYWORDS = ['Approved', 'Completed', 'Assigned'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private trfService: TrfService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
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
      next: (response: any) => {
        // Backend returns { trf: { ...data } }, so extract the trf object
        const data = response.trf || response;
        this.trfData = this.transformTrfData(data);
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load TRF details: ' + (err.message || 'Unknown error');
        this.loading = false;
      }
    });
  }

  /**
   * Transform backend data to match the view structure
   */
  private transformTrfData(data: any): any {
    const travelType = data.travel_type || data.travelType;

    // Extract itinerary from the correct nested location based on travel type
    let itinerary: any[] = [];
    let mealSelections: any[] = [];
    let passportDetails: any = null;
    let bankDetails: any = null;
    let advanceAmounts: any[] = [];
    let purpose = data.purpose || '';

    // Backend returns nested structures based on travel type
    if (travelType === 'Domestic') {
      const domesticDetails = data.domesticTravelDetails || {};
      itinerary = domesticDetails.itinerary || data.itinerary_segments || data.itinerary || [];
      mealSelections = domesticDetails.mealProvision?.dailyMealSelections || data.daily_meals || data.daily_meal_selections || data.mealSelections || [];
      purpose = domesticDetails.purpose || data.purpose || '';
    } else if (travelType === 'Overseas' || travelType === 'Home Leave Passage') {
      const overseasDetails = data.overseasTravelDetails || {};
      itinerary = overseasDetails.itinerary || data.itinerary_segments || data.itinerary || [];
      bankDetails = overseasDetails.advanceBankDetails || data.advance_bank_details || data.bankDetails;
      advanceAmounts = overseasDetails.advanceAmountRequested || data.advance_amount_items || data.advanceAmounts || [];
      passportDetails = data.passport_details || data.passportDetails; // Passport details might be at top level
      purpose = overseasDetails.purpose || data.purpose || '';
    } else if (travelType === 'External Parties') {
      const externalDetails = data.externalPartiesTravelDetails || {};
      itinerary = externalDetails.itinerary || data.itinerary_segments || data.itinerary || [];
      purpose = externalDetails.purpose || data.purpose || '';
    }


    // Extract external party info from nested structure
    const externalRequestorInfo = data.externalPartyRequestorInfo || {};

    return {
      id: data.id,
      requestNumber: data.request_number || data.requestNumber,
      travelType: travelType,
      status: data.status,
      requestorName: data.requestor_name || data.requestorName,
      staffId: data.staff_id || data.staffId,
      department: data.department,
      position: data.position,
      costCenter: data.cost_center || data.costCenter,
      telEmail: data.tel_email || data.telEmail,
      purpose: purpose,
      additionalComments: data.additional_comments || data.additionalComments,
      estimatedCost: data.estimated_cost || data.estimatedCost || 0,
      // External party fields - from nested structure or top level
      externalPartyName: externalRequestorInfo.externalFullName || data.external_full_name || data.external_party_name || data.externalPartyName,
      externalPartyOrganization: externalRequestorInfo.externalOrganization || data.external_organization || data.external_party_organization || data.externalPartyOrganization,
      externalRefToAuthorityLetter: externalRequestorInfo.externalRefToAuthorityLetter || data.external_ref_to_authority_letter || data.externalRefToAuthorityLetter,
      externalCostCenter: externalRequestorInfo.externalCostCenter || data.external_cost_center || data.externalCostCenter,
      // Nested data extracted based on travel type
      itinerary: itinerary,
      mealSelections: mealSelections,
      passportDetails: passportDetails,
      bankDetails: bankDetails,
      advanceAmounts: advanceAmounts,
      approvalSteps: data.approval_steps || data.approvalSteps || data.approvalWorkflow || [],
      createdAt: data.created_at || data.createdAt,
      updatedAt: data.updated_at || data.updatedAt,
      submittedAt: data.submitted_at || data.submittedAt,
      flightDetails: data.flight_details || data.flightDetails || null
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
   * Once approved by any approval workflow, requests cannot be edited
   * Only allow editing for: Draft, Rejected, and Pending (before any approval)
   */
  canEdit(): boolean {
    if (!this.trfData?.status) return false;

    const status = this.trfData.status;

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
    return this.statusUtils.getStatusBadgeClass(this.trfData?.status);
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
   * Format flight date and time for display
   */
  formatFlightDateTime(date: string | Date | null | undefined, time: string | null | undefined): string {
    if (!date) return 'N/A';
    const formattedDate = this.dateUtils.formatDate(date);
    if (formattedDate === 'N/A' || formattedDate === 'Invalid Date') return formattedDate;

    if (!time) return formattedDate;
    const formattedTime = this.formatTime(time);
    return formattedTime === 'N/A' ? formattedDate : `${formattedDate} at ${formattedTime}`;
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
    // Check if request can be edited
    if (!this.canEdit()) {
      this.toastService.error(
        'This travel request cannot be edited because it has been approved. ' +
        'Approved requests can only be viewed, not modified.'
      );
      return;
    }

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
      }
    });
  }

  // ==================== Workflow Methods ====================

  loadWorkflow(): void {
    this.workflowLoading = true;

    this.workflowService.getInstances({
      entity_type: 'travelrequest',
      object_id: this.trfId
    }).subscribe({
      next: (response: any) => {
        // Handle both paginated response and array response
        const instances = Array.isArray(response) ? response : (response.results || []);

        // Find workflow instance for this specific TRF - check multiple fields
        const instance = instances.find((i: any) =>
          i.object_id === this.trfId ||
          i.entity_info?.id === this.trfId ||
          i.entity_id === this.trfId
        );

        if (instance && instance.id) {
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

  /**
   * Get workflow status display text
   */
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
        return `Pending Approval (Step ${currentStep} of ${totalSteps})`;
      }
      return 'Pending Approval';
    }
    if (status === 'pending') return 'Pending Approval';

    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  /**
   * Get workflow status badge class
   */
  getWorkflowStatusClass(): string {
    return this.statusUtils.getWorkflowStatusClass(this.workflow?.status);
  }
}
