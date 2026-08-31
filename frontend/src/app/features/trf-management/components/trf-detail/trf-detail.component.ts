import { Component, type OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TrfService } from '../../services/trf.service';
import {
  AccommodationService,
  type AccommodationRequest,
} from '../../../accommodation/services/accommodation.service';
import { TransportService } from '../../../transport/services/transport.service';
import type { TransportRequestForm } from '../../../transport/models/transport.model';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { RbacService } from '../../../../core/services/rbac.service';
import { AuthService } from '../../../../core/services/auth.service';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import type {
  WorkflowInstance,
  WorkflowInstanceList,
} from '../../../../core/models/workflow.models';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';
import { firstTruthy } from '../../../../shared/utils/first-truthy';
import type {
  TrfDetailRawResponse,
  TrfViewData,
  TravelTypeFields,
  TrfFlightSegment,
  TrfFlightDetails,
  TrfItineraryRow,
  TrfMealRow,
  TrfBankDetails,
  TrfAdvanceAmountRow,
  TrfPassportRow,
  TrfApprovalStepRow,
} from './trf-detail.types';

@Component({
  selector: 'app-trf-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, WorkflowStatusComponent, LoadingSpinnerComponent],
  templateUrl: './trf-detail.component.html',
  styleUrls: ['./trf-detail.component.scss'],
})
export class TrfDetailComponent implements OnInit {
  trfData: TrfViewData | null = null;
  loading: boolean = true;
  error: string = '';
  trfId!: number;

  // Workflow properties
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;

  // Status-based visibility constants
  // Note: Cancellable statuses are determined dynamically - any status starting with "Pending"
  private readonly EDITABLE_STATUSES = ['Draft', 'Rejected'];
  private readonly DELETABLE_STATUSES = ['Draft', 'Rejected'];

  // Statuses that indicate the request has been approved and should not be editable
  private readonly APPROVED_KEYWORDS = ['Approved', 'Completed', 'Assigned'];

  linkedAccommodation: AccommodationRequest | null = null;
  linkedTransport: TransportRequestForm | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private trfService: TrfService,
    private accommodationService: AccommodationService,
    private transportService: TransportService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService,
    private rbacService: RbacService,
    private authService: AuthService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService,
    private errorHandler: HttpErrorHandlerService
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

    // Check if user has admin view permissions for TRF module
    const hasAdminView =
      this.rbacService.hasPermission('view_all_trf') ||
      this.rbacService.hasPermission('approve_trf') ||
      this.rbacService.hasPermission('manage_trf');

    // Fetch TRF details from the backend using TrfService. TrfService
    // declares this Observable<TravelRequestForm>, but that model doesn't
    // match the actual raw backend response (snake_case fields, nested
    // travel-type details, etc.) - a pre-existing mismatch, not introduced
    // here. Cast at the boundary to the shape this page actually receives.
    this.trfService.getTrfById(this.trfId, false, hasAdminView).subscribe({
      next: response => {
        const raw = response as unknown as TrfDetailRawResponse;
        // Backend returns { trf: { ...data } }, so extract the trf object
        const data = raw.trf || raw;
        this.trfData = this.transformTrfData(data);
        this.loading = false;
        this.loadLinkedAccommodation();
        this.loadLinkedTransport();
      },
      error: (err: { message?: string }) => {
        this.error = `Failed to load TRF details: ${err.message || 'Unknown error'}`;
        this.loading = false;
      },
    });
  }

  /**
   * Accommodation requests embedded in a TSR are linked via AccommodationRequest.trf,
   * not returned as part of the TRF payload itself. The list endpoint has no `trf`
   * query param, so this matches client-side against the requestor's own accommodation
   * requests (a small list per user) rather than adding a new backend filter.
   */
  private loadLinkedAccommodation(): void {
    this.accommodationService.getAllRequests({ page_size: 100 }).subscribe({
      next: (response: AccommodationRequest[] | { results?: AccommodationRequest[] }) => {
        const results = Array.isArray(response) ? response : response?.results || [];
        this.linkedAccommodation = results.find(req => req.trf === this.trfId) || null;
      },
      error: () => {
        // Non-critical - the rest of the TRF detail page still works without it
        this.linkedAccommodation = null;
      },
    });
  }

  /**
   * Transport requests embedded in a TSR are linked via TransportRequest.trf, not
   * returned as part of the TRF payload itself - same reasoning and pattern as
   * loadLinkedAccommodation above.
   */
  private loadLinkedTransport(): void {
    this.transportService.getAllRequests({ page_size: 100 }).subscribe({
      next: (response: TransportRequestForm[] | { results?: TransportRequestForm[] }) => {
        const results = Array.isArray(response) ? response : response?.results || [];
        this.linkedTransport = results.find(req => Number(req.trfId) === this.trfId) || null;
      },
      error: () => {
        // Non-critical - the rest of the TRF detail page still works without it
        this.linkedTransport = null;
      },
    });
  }

  private extractDomesticFields(data: TrfDetailRawResponse): TravelTypeFields {
    const details = data.domesticTravelDetails || {};
    return {
      itinerary: firstTruthy<TrfItineraryRow[]>(
        [],
        details.itinerary,
        data.itinerary_segments,
        data.itinerary
      ),
      mealSelections: firstTruthy<TrfMealRow[]>(
        [],
        details.mealProvision?.dailyMealSelections,
        data.daily_meals,
        data.daily_meal_selections,
        data.mealSelections
      ),
      bankDetails: null,
      advanceAmounts: [],
      purpose: firstTruthy('', details.purpose, data.purpose),
    };
  }

  private extractOverseasFields(data: TrfDetailRawResponse): TravelTypeFields {
    const details = data.overseasTravelDetails || {};
    return {
      itinerary: firstTruthy<TrfItineraryRow[]>(
        [],
        details.itinerary,
        data.itinerary_segments,
        data.itinerary
      ),
      mealSelections: [],
      bankDetails: firstTruthy<TrfBankDetails | null>(
        null,
        details.advanceBankDetails,
        data.advance_bank_details,
        data.bankDetails
      ),
      advanceAmounts: firstTruthy<TrfAdvanceAmountRow[]>(
        [],
        details.advanceAmountRequested,
        data.advance_amount_items,
        data.advanceAmounts
      ),
      purpose: firstTruthy('', details.purpose, data.purpose),
    };
  }

  private extractExternalPartiesFields(data: TrfDetailRawResponse): TravelTypeFields {
    const details = data.externalPartiesTravelDetails || {};
    return {
      itinerary: firstTruthy<TrfItineraryRow[]>(
        [],
        details.itinerary,
        data.itinerary_segments,
        data.itinerary
      ),
      mealSelections: firstTruthy<TrfMealRow[]>(
        [],
        details.mealProvision?.dailyMealSelections,
        data.daily_meals,
        data.daily_meal_selections,
        data.mealSelections
      ),
      bankDetails: null,
      advanceAmounts: [],
      purpose: firstTruthy('', details.purpose, data.purpose),
    };
  }

  /**
   * Transform backend data to match the view structure. Itinerary/meal/
   * bank-detail/advance-amount extraction is delegated to per-travel-type
   * helpers above - each travel type nests these under a different key
   * (domesticTravelDetails/overseasTravelDetails/
   * externalPartiesTravelDetails), so they can't be read generically.
   */
  private transformTrfData(data: TrfDetailRawResponse): TrfViewData {
    const travelType = firstTruthy('', data.travel_type, data.travelType);

    let travelTypeFields: TravelTypeFields = {
      itinerary: [],
      mealSelections: [],
      bankDetails: null,
      advanceAmounts: [],
      purpose: data.purpose ?? '',
    };
    if (travelType === 'Domestic') {
      travelTypeFields = this.extractDomesticFields(data);
    } else if (travelType === 'Overseas') {
      travelTypeFields = this.extractOverseasFields(data);
    } else if (travelType === 'External Parties') {
      travelTypeFields = this.extractExternalPartiesFields(data);
    }

    // Passport details are returned at the top level (passport_details) regardless
    // of travel type - Domestic and External Parties can upload one too, not just
    // Overseas.
    const passportDetails = firstTruthy<TrfPassportRow[]>(
      [],
      data.passport_details,
      data.passportDetails
    );

    // Extract external party info from nested structure
    const externalRequestorInfo = data.externalPartyRequestorInfo ?? {};

    return {
      id: data.id,
      requestNumber: firstTruthy('', data.request_number, data.requestNumber),
      travelType,
      status: data.status ?? '',
      requestorName: firstTruthy('', data.requestor_name, data.requestorName),
      createdBy: firstTruthy<number | null>(null, data.created_by, data.createdBy),
      staffId: firstTruthy('', data.staff_id, data.staffId),
      department: data.department ?? '',
      position: data.position ?? '',
      costCenter: firstTruthy('', data.cost_center, data.costCenter),
      telEmail: firstTruthy('', data.tel_email, data.telEmail),
      purpose: travelTypeFields.purpose,
      additionalComments: firstTruthy('', data.additional_comments, data.additionalComments),
      estimatedCost: firstTruthy<number | string>(0, data.estimated_cost, data.estimatedCost),
      // External party fields - from nested structure or top level
      externalPartyName: firstTruthy(
        '',
        externalRequestorInfo.externalFullName,
        data.external_full_name,
        data.external_party_name,
        data.externalPartyName
      ),
      externalPartyOrganization: firstTruthy(
        '',
        externalRequestorInfo.externalOrganization,
        data.external_organization,
        data.external_party_organization,
        data.externalPartyOrganization
      ),
      externalRefToAuthorityLetter: firstTruthy(
        '',
        externalRequestorInfo.externalRefToAuthorityLetter,
        data.external_ref_to_authority_letter,
        data.externalRefToAuthorityLetter
      ),
      externalCostCenter: firstTruthy(
        '',
        externalRequestorInfo.externalCostCenter,
        data.external_cost_center,
        data.externalCostCenter
      ),
      // Nested data extracted based on travel type
      itinerary: travelTypeFields.itinerary,
      mealSelections: travelTypeFields.mealSelections,
      mealProcessingStatus: firstTruthy('', data.meal_processing_status, data.mealProcessingStatus),
      passportDetails,
      bankDetails: travelTypeFields.bankDetails,
      advanceAmounts: travelTypeFields.advanceAmounts,
      advanceConsentAccepted: data.advance_consent_accepted ?? data.advanceConsentAccepted ?? false,
      advanceConsentAcceptedAt: firstTruthy(
        '',
        data.advance_consent_accepted_at,
        data.advanceConsentAcceptedAt
      ),
      approvalSteps: firstTruthy<TrfApprovalStepRow[]>(
        [],
        data.approval_steps,
        data.approvalSteps,
        data.approvalWorkflow
      ),
      createdAt: firstTruthy('', data.created_at, data.createdAt),
      updatedAt: firstTruthy('', data.updated_at, data.updatedAt),
      submittedAt: firstTruthy('', data.submitted_at, data.submittedAt),
      flightDetails: firstTruthy<TrfFlightDetails | null>(
        null,
        data.flight_details,
        data.flightDetails
      ),
    };
  }

  /**
   * Check if TRF is for external parties
   */
  get isExternal(): boolean {
    return this.trfData?.travelType === 'External Parties';
  }

  /**
   * Check if TRF is overseas
   */
  get isOverseas(): boolean {
    return this.trfData?.travelType === 'Overseas';
  }

  /**
   * Check if TRF is domestic
   */
  get isDomestic(): boolean {
    return this.trfData?.travelType === 'Domestic';
  }

  /**
   * Meal provisions are only captured for Domestic and External Parties
   * travel types (not Overseas, by design).
   */
  get hasMealProvision(): boolean {
    return !!this.trfData?.mealSelections?.length;
  }

  /**
   * The signed-in user created this TRF. Owner-only actions (Edit/Cancel/
   * Delete) are gated on this so a viewer with read access - an approver,
   * an admin browsing, anyone else - can't act on someone else's request.
   */
  get isOwner(): boolean {
    const currentUserId = this.authService.getCurrentUserId();
    return currentUserId != null && this.trfData?.createdBy === currentUserId;
  }

  /**
   * Check if TRF can be edited based on status
   * Once approved by any approval workflow, requests cannot be edited
   * Only allow editing for: Draft, Rejected, and Pending (before any approval)
   */
  canEdit(): boolean {
    if (!this.isOwner) return false;
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
    if (!this.isOwner) return false;
    const status = this.trfData?.status || '';
    // Allow cancel for any status that contains 'Pending' and is not approved
    if (status.includes('Pending')) {
      const isApproved = this.APPROVED_KEYWORDS.some(keyword => status.includes(keyword));
      return !isApproved;
    }
    return false;
  }

  /**
   * Check if TRF can be deleted based on status
   * Only allow deletion for Draft and Rejected statuses
   */
  canDelete(): boolean {
    if (!this.isOwner) return false;
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
   * Format time for display. ETD/ETA are free-text fields (a requestor may write
   * "Morning"/"Evening" instead of an exact time), so anything that isn't a
   * recognizable HH:MM value is shown as entered rather than discarded as N/A.
   */
  formatTime(time: string | null | undefined): string {
    if (!time) return 'N/A';
    const timeMatch = time.match(/^([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$/);
    if (!timeMatch) return time;

    const [, hours, minutes] = timeMatch;
    const date = new Date();
    date.setHours(parseInt(hours), parseInt(minutes));
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }

  /**
   * Format flight date and time for display
   */
  formatFlightDateTime(
    date: string | Date | null | undefined,
    time: string | null | undefined
  ): string {
    if (!date) return 'N/A';
    const formattedDate = this.dateUtils.formatDate(date);
    if (formattedDate === 'N/A' || formattedDate === 'Invalid Date') return formattedDate;

    if (!time) return formattedDate;
    const formattedTime = this.formatTime(time);
    return formattedTime === 'N/A' ? formattedDate : `${formattedDate} at ${formattedTime}`;
  }

  /**
   * Flight bookings can have any number of legs per direction
   * (connections); this splits the flat segments list for the Outbound
   * and Return tables on the Flight Processing Details card.
   */
  getSegmentsByDirection(direction: 'OUTBOUND' | 'RETURN'): TrfFlightSegment[] {
    const segments = this.trfData?.flightDetails?.segments;
    if (!segments) {
      return [];
    }
    return segments.filter(seg => seg.direction === direction);
  }

  /**
   * Format number for display
   */
  formatNumber(num: number | string | null | undefined, decimals: number = 0): string {
    if (num === null || num === undefined || String(num).trim() === '') return 'N/A';
    const parsedNum = Number(num);
    return Number.isNaN(parsedNum)
      ? String(num)
      : parsedNum.toLocaleString(undefined, {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        });
  }

  /**
   * Calculate meal totals
   */
  getMealTotal(mealType: keyof TrfMealRow): number {
    if (!this.trfData?.mealSelections) return 0;
    return this.trfData.mealSelections.reduce((acc: number, meal: TrfMealRow) => {
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
    this.confirmationService
      .confirmCancel('Are you sure you want to cancel this TRF? This action cannot be undone.')
      .subscribe(confirmed => {
        if (confirmed) {
          // Call the cancel action endpoint using TrfService
          this.trfService.cancelTrf(this.trfId).subscribe({
            next: () => {
              this.toastService.success('TRF cancelled successfully');
              this.router.navigate(['/trf']);
            },
            error: err => {
              this.toastService.error(
                this.errorHandler.getErrorMessage(err, 'Failed to cancel TRF')
              );
            },
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
          error: err => {
            this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to delete TRF'));
          },
        });
      }
    });
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
        link.download = `TSR-${this.trfData?.requestNumber || this.trfId}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('PDF exported successfully');
      },
      error: (err: HttpErrorResponse) => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to export PDF'));
      },
    });
  }

  // ==================== Workflow Methods ====================

  loadWorkflow(): void {
    this.workflowLoading = true;

    this.workflowService
      .getInstances({
        entity_type: 'travelrequest',
        object_id: this.trfId,
      })
      .subscribe({
        next: (instances: WorkflowInstanceList[]) => {
          // Find workflow instance for this specific TRF - check multiple fields
          const instance = instances.find(
            i => i.object_id === this.trfId || i.entity_info?.id === this.trfId
          );

          if (instance?.id) {
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

  /**
   * Get workflow status display text
   */
  getWorkflowStatus(): string {
    if (!this.workflow) return '';

    const status = this.workflow.status;
    const currentStep = this.workflow.current_step_order;
    // The template's real, configured step count - not step_executions.length,
    // which only counts steps reached so far (WorkflowEngine creates step
    // executions lazily, one at a time, so a workflow still on step 1 of a
    // 3-step template only has 1 step_execution row and would wrongly show
    // "Step 1 of 1").
    const totalSteps =
      this.workflow.workflow_template_detail?.step_count ||
      this.workflow.step_executions?.length ||
      0;

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
