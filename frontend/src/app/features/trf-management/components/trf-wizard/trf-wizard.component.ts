import { Component, type OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { HttpErrorResponse } from '@angular/common/http';
import { Router, ActivatedRoute } from '@angular/router';
import { from } from 'rxjs';
import { TrfStepperComponent } from '../trf-stepper/trf-stepper.component';
import {
  RequestorInformationComponent,
  type RequestorInformation,
} from '../requestor-information/requestor-information.component';
import {
  DomesticTravelDetailsComponent,
  type DomesticTravelSpecificDetails,
  type AccommodationDetails,
  type TransportJourney,
  type ItinerarySegment as DomesticItinerarySegment,
} from '../domestic-travel-details/domestic-travel-details.component';
import {
  OverseasTravelDetailsComponent,
  type OverseasTravelDetails,
  type ItinerarySegment as OverseasItinerarySegment,
} from '../overseas-travel-details/overseas-travel-details.component';
import {
  HomeLeaveDetailsComponent,
  type HomeLeaveDetails,
} from '../home-leave-details/home-leave-details.component';
import {
  ExternalPartiesDetailsComponent,
  type ExternalPartiesDetails,
} from '../external-parties-details/external-parties-details.component';
import {
  ApprovalSubmissionComponent,
  type ApprovalSubmissionData,
} from '../approval-submission/approval-submission.component';
import { TrfService } from '../../services/trf.service';
import { AccommodationService } from '../../../accommodation/services/accommodation.service';
import { TransportService } from '../../../transport/services/transport.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { RbacService } from '../../../../core/services/rbac.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';
import type {
  TrfBackendResponse,
  NestedItineraryRow,
  RawMealRow,
  RawBankDetailRow,
  RawAdvanceAmountRow,
  RawPassportRow,
  TransformedPassportDetails,
} from './trf-wizard.types';
import {
  deriveTripTypeFromItinerary,
  transformItineraryData,
  transformExternalPartiesItineraryData,
  transformMealSelectionsData,
  transformBankDetails,
  transformAdvanceAmounts,
  extractPassportFileInfo,
  transformPassportDetails,
} from './trf-data-mapper';
import { TrfSubmissionService } from './trf-submission.service';

@Component({
  selector: 'app-trf-wizard',
  standalone: true,
  imports: [
    CommonModule,
    TrfStepperComponent,
    RequestorInformationComponent,
    DomesticTravelDetailsComponent,
    OverseasTravelDetailsComponent,
    HomeLeaveDetailsComponent,
    ExternalPartiesDetailsComponent,
    ApprovalSubmissionComponent,
    LoadingSpinnerComponent,
  ],
  templateUrl: './trf-wizard.component.html',
  styleUrls: ['./trf-wizard.component.scss'],
})
export class TrfWizardComponent implements OnInit {
  @ViewChild(RequestorInformationComponent) requestorForm!: RequestorInformationComponent;
  @ViewChild(DomesticTravelDetailsComponent) domesticTravelForm!: DomesticTravelDetailsComponent;
  @ViewChild(OverseasTravelDetailsComponent) overseasTravelForm!: OverseasTravelDetailsComponent;
  @ViewChild(HomeLeaveDetailsComponent) homeLeaveForm!: HomeLeaveDetailsComponent;
  @ViewChild(ExternalPartiesDetailsComponent) externalPartiesForm!: ExternalPartiesDetailsComponent;
  @ViewChild(ApprovalSubmissionComponent) approvalForm!: ApprovalSubmissionComponent;

  currentStep: number = 1;
  totalSteps: number = 3; // Requestor Info + Travel Details + Approval & Submission
  stepLabels: string[] = ['Requestor Information', 'Travel Details', 'Approval & Submission'];
  completedSteps: boolean[] = [false, false, false];
  isSubmitting: boolean = false;
  submitError: string = '';

  // Edit mode
  isEditMode: boolean = false;
  trfId: number | null = null;
  existingTrfData: TrfBackendResponse | null = null;
  isLoadingTrf: boolean = false;

  // Travel type - determined by route
  selectedTravelType: 'Domestic' | 'Overseas' | 'Home Leave' | 'External Parties' | null = null;

  // Store form data from each step
  requestorData: Partial<RequestorInformation> = {};
  domesticTravelData: Partial<DomesticTravelSpecificDetails> = {};
  overseasTravelData: Partial<OverseasTravelDetails> = {};
  // The `passportDetails` extension here is a pre-existing bug this typing
  // just made visible, not something introduced by it: HomeLeaveDetails
  // (and HomeLeaveDetailsComponent) has no such field - it only knows about
  // passportUpload (file metadata). prePopulateTravelData() below sets
  // passportDetails on edit-load, but saveCurrentStepData() immediately
  // overwrites this whole object with getFormData()'s return the moment the
  // user reaches step 2, which never carries it forward - so it's silently
  // discarded before submission regardless. Left exactly as-is (including
  // the bug) rather than fixed under this typing task.
  homeLeaveData: Partial<HomeLeaveDetails> & {
    passportDetails?: TransformedPassportDetails | null;
  } = {};
  externalPartiesData: Partial<ExternalPartiesDetails> = {};
  approvalData: Partial<ApprovalSubmissionData> = {}; // Store approval & submission data including additionalComments
  approvalSubmissionData: Partial<ApprovalSubmissionData> = {};

  constructor(
    private trfService: TrfService,
    private accommodationService: AccommodationService,
    private transportService: TransportService,
    private router: Router,
    private route: ActivatedRoute,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private rbacService: RbacService,
    private errorHandler: HttpErrorHandlerService,
    private trfSubmission: TrfSubmissionService
  ) {}

  ngOnInit(): void {
    // Determine travel type from route
    const url = this.router.url;
    if (url.includes('/create/domestic')) {
      this.selectedTravelType = 'Domestic';
    } else if (url.includes('/create/overseas')) {
      this.selectedTravelType = 'Overseas';
    } else if (url.includes('/create/home-leave')) {
      this.selectedTravelType = 'Home Leave';
    } else if (url.includes('/create/external-parties')) {
      this.selectedTravelType = 'External Parties';
    }

    // Check if we're in edit mode
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.trfId = +params['id'];
        this.loadExistingTrf(this.trfId);
      }
    });
  }

  /**
   * Load existing TRF data for editing
   */
  private loadExistingTrf(id: number): void {
    this.isLoadingTrf = true;

    // Check if user has admin permissions for TRF module
    const hasAdminView =
      this.rbacService.hasPermission('view_all_trf') ||
      this.rbacService.hasPermission('manage_trf');

    this.trfService.getTrfById(id, false, hasAdminView).subscribe({
      // TrfService.getTrfById() is typed Observable<TravelRequestForm>, but
      // that model (core/models/trf.model.ts) is a stale/mock shape that
      // doesn't match what the endpoint actually returns (this file has
      // always read requestor_name/staff_id/etc., none of which exist on
      // TravelRequestForm) - out of scope to fix trf.service.ts's typing
      // here, so cast at this boundary to the shape this file actually
      // consumes instead of trusting the declared (wrong) type.
      next: response => {
        const raw = response as unknown as TrfBackendResponse;
        // The backend returns { trf: { ...data } }, so we need to extract the trf object
        const data = raw.trf || raw;

        this.existingTrfData = data;
        this.selectedTravelType = (data.travel_type ||
          data.travelType) as typeof this.selectedTravelType;

        // Check if TRF can be edited
        // Allow editing for Draft, Rejected, or any Pending status
        const canEdit =
          data.status === 'Draft' ||
          data.status === 'Rejected' ||
          !!data.status?.startsWith('Pending');

        if (data.status && !canEdit) {
          const errorMsg = `This TRF cannot be edited because its status is "${data.status}". Only Draft, Rejected, or Pending TRFs can be edited.`;
          this.isLoadingTrf = false;

          // Show error toast and redirect back to list
          this.toastService.error(errorMsg);
          setTimeout(() => {
            this.router.navigate(['/trf']);
          }, 3000);
          return;
        }

        // Pre-populate requestor data
        this.requestorData = {
          fullName: data.requestor_name || data.requestorName,
          staffId: data.staff_id || data.staffId,
          department: data.department,
          position: data.position,
          costCenter: data.cost_center || data.costCenter,
          contactNo: data.tel_email || data.telEmail,
          email: data.email,
        };

        // Pre-populate approval data (additional comments, selected approvers, and skipped steps)
        this.approvalData = {
          additionalComments: data.additional_comments || data.additionalComments || '',
          selected_approvers: data.selected_approvers || {},
          skipped_steps: data.skipped_steps || {},
        };

        // Pre-populate travel-specific data based on type
        this.prePopulateTravelData(data);

        this.isLoadingTrf = false;
      },
      error: (err: HttpErrorResponse) => {
        this.submitError = `Failed to load TRF: ${err.error?.message || err.message || 'Unknown error'}`;
        this.isLoadingTrf = false;
      },
    });
  }

  /**
   * Pre-populate travel-specific data
   *
   * High cyclomatic complexity is a 4-branch switch over travel type, each
   * branch a straight-line field mapping from the backend's nested response
   * shape - not genuinely branchy logic. A real refactor (e.g. one mapper
   * method per travel type) is better done on its own rather than folded
   * into an unrelated form-field removal.
   */
  // eslint-disable-next-line complexity
  private prePopulateTravelData(data: TrfBackendResponse): void {
    switch (this.selectedTravelType) {
      case 'Domestic': {
        // Backend returns nested structure: data.domesticTravelDetails.itinerary
        const domesticDetails = data.domesticTravelDetails || {};
        const itineraryData =
          domesticDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const mealData =
          domesticDetails.mealProvision?.dailyMealSelections ||
          data.daily_meals ||
          data.daily_meal_selections ||
          data.mealSelections ||
          [];
        const domesticPassport = extractPassportFileInfo(
          (data.passport_details || data.passportDetails) as RawPassportRow | RawPassportRow[]
        );

        const domesticItinerary = transformItineraryData(itineraryData as NestedItineraryRow[]);
        this.domesticTravelData = {
          purposeOfTravel: domesticDetails.purpose || data.purpose || '',
          tripType: deriveTripTypeFromItinerary(
            domesticItinerary as unknown as Record<string, unknown>[],
            'from',
            'to',
            'date'
          ),
          itinerary: domesticItinerary as unknown as DomesticItinerarySegment[],
          mealProvisions: {
            dailySelections: transformMealSelectionsData(mealData as RawMealRow[]),
          },
          passportUpload: domesticPassport,
        };
        this.loadLinkedAccommodationForEdit(data.id);
        this.loadLinkedTransportForEdit(data.id);
        break;
      }

      case 'Overseas': {
        // Backend returns nested structure: data.overseasTravelDetails
        const overseasDetails = data.overseasTravelDetails || {};
        const overseasItinerary =
          overseasDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const bankDetails =
          overseasDetails.advanceBankDetails ||
          data.bank_detail ||
          data.advance_bank_details ||
          data.bankDetails;
        const advanceAmounts =
          overseasDetails.advanceAmountRequested ||
          data.advance_amounts ||
          data.advance_amount_items ||
          data.advanceAmounts ||
          [];
        const overseasPassport = extractPassportFileInfo(
          (data.passport_details || data.passportDetails) as RawPassportRow | RawPassportRow[]
        );

        const overseasTransformedItinerary = transformItineraryData(
          overseasItinerary as NestedItineraryRow[]
        );
        this.overseasTravelData = {
          purpose: overseasDetails.purpose || data.purpose || '',
          tripType: deriveTripTypeFromItinerary(
            overseasTransformedItinerary as unknown as Record<string, unknown>[],
            'from',
            'to',
            'date'
          ),
          itinerary: overseasTransformedItinerary as unknown as OverseasItinerarySegment[],
          advanceBankDetails: transformBankDetails(bankDetails as RawBankDetailRow),
          advanceAmountRequested: transformAdvanceAmounts(advanceAmounts as RawAdvanceAmountRow[]),
          advanceConsentAccepted: data.advance_consent_accepted || false,
          passportUpload: overseasPassport,
        };
        break;
      }

      case 'Home Leave': {
        // Backend returns nested structure: data.overseasTravelDetails (Home Leave reuses overseas structure)
        const homeLeaveDetails = data.overseasTravelDetails || {};
        const homeLeaveItinerary =
          homeLeaveDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const passportDetails = (data.passport_details || data.passportDetails) as
          | RawPassportRow
          | RawPassportRow[];
        const homeLeaveBank =
          homeLeaveDetails.advanceBankDetails ||
          data.bank_detail ||
          data.advance_bank_details ||
          data.bankDetails;
        const homeLeaveAdvanceAmounts =
          homeLeaveDetails.advanceAmountRequested ||
          data.advance_amounts ||
          data.advance_amount_items ||
          data.advanceAmounts ||
          [];
        const homeLeavePassport = extractPassportFileInfo(passportDetails);

        const homeLeaveTransformedItinerary = transformItineraryData(
          homeLeaveItinerary as NestedItineraryRow[]
        );
        this.homeLeaveData = {
          purpose: homeLeaveDetails.purpose || data.purpose || '',
          tripType: deriveTripTypeFromItinerary(
            homeLeaveTransformedItinerary as unknown as Record<string, unknown>[],
            'from',
            'to',
            'date'
          ),
          itinerary: homeLeaveTransformedItinerary,
          passportDetails: transformPassportDetails(passportDetails),
          advanceBankDetails: transformBankDetails(homeLeaveBank as RawBankDetailRow),
          advanceAmountRequested: transformAdvanceAmounts(
            homeLeaveAdvanceAmounts as RawAdvanceAmountRow[]
          ),
          advanceConsentAccepted: data.advance_consent_accepted || false,
          passportUpload: homeLeavePassport,
        };
        break;
      }

      case 'External Parties': {
        // Backend returns nested structure: data.externalPartiesTravelDetails
        const externalDetails = data.externalPartiesTravelDetails || {};
        const externalRequestorInfo = data.externalPartyRequestorInfo || {};
        const externalItinerary =
          externalDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const externalPassport = extractPassportFileInfo(
          (data.passport_details || data.passportDetails) as RawPassportRow | RawPassportRow[]
        );

        const externalTransformedItinerary = transformExternalPartiesItineraryData(
          externalItinerary as NestedItineraryRow[]
        );
        this.externalPartiesData = {
          purpose: externalDetails.purpose || data.purpose || '',
          tripType: deriveTripTypeFromItinerary(
            externalTransformedItinerary as unknown as Record<string, unknown>[],
            'departureLocation',
            'arrivalLocation',
            'departureDate',
            'departureTime'
          ),
          externalFullName:
            externalRequestorInfo.externalFullName ||
            data.external_full_name ||
            data.externalFullName ||
            '',
          externalOrganization:
            externalRequestorInfo.externalOrganization ||
            data.external_organization ||
            data.externalOrganization ||
            '',
          externalRefToAuthorityLetter:
            externalRequestorInfo.externalRefToAuthorityLetter ||
            data.external_ref_to_authority_letter ||
            data.externalRefToAuthorityLetter ||
            '',
          externalCostCenter:
            externalRequestorInfo.externalCostCenter ||
            data.external_cost_center ||
            data.externalCostCenter ||
            '',
          itinerary: externalTransformedItinerary,
          passportUpload: externalPassport,
        };
        break;
      }
    }
  }

  /**
   * Accommodation requests embedded in a TSR are linked via AccommodationRequest.trf,
   * not returned as part of the TRF payload itself (same reasoning as
   * trf-detail.component.ts's loadLinkedAccommodation). When editing an existing
   * Domestic TRF, fetch its linked accommodation request (if any) and merge it into
   * domesticTravelData so the "Requires Accommodation" section pre-populates instead
   * of always starting blank. Assigns a new object so the DomesticTravelDetailsComponent's
   * ngOnChanges (which rebuilds the form on non-first initialData changes) picks it up.
   */
  private loadLinkedAccommodationForEdit(trfId: number): void {
    // AccommodationService.getAllRequests() is typed Observable<any> at its
    // own declaration (out of scope to fix here) - this interface describes
    // only the fields this call site actually reads off each row.
    interface LinkedAccommodationRow {
      trf?: number;
      additional_data?: {
        requestor_gender?: string;
        location?: string;
        requested_check_in_date?: string;
        flight_arrival_time?: string;
        requested_check_out_date?: string;
        flight_departure_time?: string;
        requested_room_type?: string;
        special_requests?: string;
      };
    }

    this.accommodationService.getAllRequests({ page_size: 100 }).subscribe({
      next: (response: { results?: LinkedAccommodationRow[] } | LinkedAccommodationRow[]) => {
        const results = (Array.isArray(response) ? response : response?.results) || [];
        const linked = results.find(req => req.trf === trfId);
        if (!linked) {
          return;
        }
        const additionalData = linked.additional_data || {};
        this.domesticTravelData = {
          ...this.domesticTravelData,
          // gender/location/roomType are backend free-text that this form's
          // AccommodationDetails narrows to specific literal unions - trust
          // the backend value the same way the rest of this file already
          // trusts loosely-typed API responses (see TrfBackendResponse's own
          // doc comment) rather than validating every possible literal here.
          accommodation: {
            required: true,
            gender: (additionalData.requestor_gender || '') as AccommodationDetails['gender'],
            location: (additionalData.location || '') as AccommodationDetails['location'],
            checkInDate: additionalData.requested_check_in_date || '',
            checkInTime: additionalData.flight_arrival_time || '',
            checkOutDate: additionalData.requested_check_out_date || '',
            checkOutTime: additionalData.flight_departure_time || '',
            roomType: (additionalData.requested_room_type ||
              '') as AccommodationDetails['roomType'],
            specialRequests: additionalData.special_requests || '',
          },
        };
      },
      error: () => {
        // Non-critical - the rest of the edit form still works without it
      },
    });
  }

  /**
   * Transport requests embedded in a TSR are linked via TransportRequest.trf, not
   * returned as part of the TRF payload itself - same reasoning/pattern as
   * loadLinkedAccommodationForEdit above.
   */
  private loadLinkedTransportForEdit(trfId: number): void {
    // TransportService.getAllRequests() is typed Observable<any> at its own
    // declaration (out of scope to fix here) - this interface describes
    // only the fields this call site actually reads off each row.
    interface LinkedTransportRow {
      trfId?: number | string;
      transportDetails?: TransportJourney[];
    }

    this.transportService.getAllRequests({ page_size: 100 }).subscribe({
      next: (response: { results?: LinkedTransportRow[] } | LinkedTransportRow[]) => {
        const results = (Array.isArray(response) ? response : response?.results) || [];
        const linked = results.find(req => Number(req.trfId) === trfId);
        if (!linked) {
          return;
        }
        this.domesticTravelData = {
          ...this.domesticTravelData,
          transport: {
            required: true,
            journeys: linked.transportDetails || [],
          },
        };
      },
      error: () => {
        // Non-critical - the rest of the edit form still works without it
      },
    });
  }

  /**
   * Handle requestor form submission
   */
  onRequestorSubmit(data: RequestorInformation): void {
    this.requestorData = data;
    this.completedSteps[0] = true;
    this.currentStep = 2; // Move to travel details
  }

  /**
   * Handle travel details form submission
   */
  onTravelDetailsSubmit(
    data:
      | DomesticTravelSpecificDetails
      | OverseasTravelDetails
      | HomeLeaveDetails
      | ExternalPartiesDetails
  ): void {
    // Save the data based on travel type
    switch (this.selectedTravelType) {
      case 'Domestic':
        this.domesticTravelData = data as DomesticTravelSpecificDetails;
        break;
      case 'Overseas':
        this.overseasTravelData = data as OverseasTravelDetails;
        break;
      case 'Home Leave':
        this.homeLeaveData = data as HomeLeaveDetails;
        break;
      case 'External Parties':
        this.externalPartiesData = data as ExternalPartiesDetails;
        break;
    }
    this.completedSteps[1] = true;
    this.currentStep = 3; // Move to approval & submission
  }

  /**
   * Handle step click from stepper
   */
  onStepClick(step: number): void {
    // Validate current step before allowing navigation
    if (step > this.currentStep) {
      if (!this.validateCurrentStep()) {
        return;
      }
    }
    this.currentStep = step;
  }

  /**
   * Validate the current step
   */
  private validateCurrentStep(): boolean {
    if (this.currentStep === 1) {
      // Validate requestor information
      if (this.requestorForm && !this.requestorForm.isValid()) {
        this.requestorForm.markAllAsTouched();
        return false;
      }
    } else if (this.currentStep === 2) {
      // Validate travel details based on selected type
      return this.validateTravelDetailsForm();
    } else if (this.currentStep === 3) {
      // Validate approval & submission
      if (this.approvalForm && !this.approvalForm.isValid()) {
        this.approvalForm.markAllAsTouched();
        return false;
      }
    }
    return true;
  }

  /**
   * Validate the appropriate travel details form
   */
  private validateTravelDetailsForm(): boolean {
    switch (this.selectedTravelType) {
      case 'Domestic':
        if (this.domesticTravelForm && !this.domesticTravelForm.isValid()) {
          this.warnIfItineraryIncomplete(this.domesticTravelForm.isItineraryIncomplete);
          this.warnIfItineraryOutOfOrder(this.domesticTravelForm.isItineraryOutOfOrder);
          this.domesticTravelForm.markAllAsTouched();
          return false;
        }
        break;
      case 'Overseas':
        if (this.overseasTravelForm && !this.overseasTravelForm.isValid()) {
          this.warnIfItineraryIncomplete(this.overseasTravelForm.isItineraryIncomplete);
          this.warnIfItineraryOutOfOrder(this.overseasTravelForm.isItineraryOutOfOrder);
          this.overseasTravelForm.markAllAsTouched();
          return false;
        }
        break;
      case 'Home Leave':
        if (this.homeLeaveForm && !this.homeLeaveForm.isValid()) {
          this.warnIfItineraryIncomplete(this.homeLeaveForm.isItineraryIncomplete);
          this.warnIfItineraryOutOfOrder(this.homeLeaveForm.isItineraryOutOfOrder);
          this.homeLeaveForm.markAllAsTouched();
          return false;
        }
        break;
      case 'External Parties':
        if (this.externalPartiesForm && !this.externalPartiesForm.isValid()) {
          this.warnIfItineraryIncomplete(this.externalPartiesForm.isItineraryIncomplete);
          this.warnIfItineraryOutOfOrder(this.externalPartiesForm.isItineraryOutOfOrder);
          this.externalPartiesForm.markAllAsTouched();
          return false;
        }
        break;
      default:
        return false;
    }
    return true;
  }

  /**
   * Round Trip requires at least 2 itinerary segments (outbound + return).
   * The itinerary segment count isn't tracked by the reactive form, so it
   * doesn't get an inline validation message like other fields - surface
   * it as a toast instead.
   */
  private warnIfItineraryIncomplete(isIncomplete: boolean): void {
    if (isIncomplete) {
      this.toastService.error(
        'Round Trip requires a return itinerary segment. Please add the return leg before continuing.'
      );
    }
  }

  /**
   * Itinerary segments must be in chronological order (e.g. a return leg
   * cannot be dated before the outbound leg). Like the incomplete-itinerary
   * check above, this spans multiple segments so it isn't a per-field
   * reactive form error - surfaced as a toast instead.
   */
  private warnIfItineraryOutOfOrder(isOutOfOrder: boolean): void {
    if (isOutOfOrder) {
      this.toastService.error(
        'Itinerary dates must be in chronological order. A later segment cannot be dated before an earlier one.'
      );
    }
  }

  /**
   * Handle next button click
   */
  onNext(): void {
    if (!this.validateCurrentStep()) {
      return;
    }

    // Save current step data
    this.saveCurrentStepData();

    // Move to next step
    if (this.currentStep < this.totalSteps) {
      this.currentStep++;
    }
  }

  /**
   * Handle previous button click
   */
  onPrevious(): void {
    // Save current step data (optional, for draft)
    this.saveCurrentStepData();

    if (this.currentStep > 1) {
      this.currentStep--;
    }
  }

  /**
   * Save data from the current step
   */
  private saveCurrentStepData(): void {
    if (this.currentStep === 1 && this.requestorForm) {
      this.requestorData = this.requestorForm.getFormData();
    } else if (this.currentStep === 2) {
      // Save appropriate travel details based on type
      switch (this.selectedTravelType) {
        case 'Domestic':
          if (this.domesticTravelForm) {
            this.domesticTravelData = this.domesticTravelForm.getFormData();
          }
          break;
        case 'Overseas':
          if (this.overseasTravelForm) {
            this.overseasTravelData = this.overseasTravelForm.getFormData();
          }
          break;
        case 'Home Leave':
          if (this.homeLeaveForm) {
            this.homeLeaveData = this.homeLeaveForm.getFormData();
          }
          break;
        case 'External Parties':
          if (this.externalPartiesForm) {
            this.externalPartiesData = this.externalPartiesForm.getFormData();
          }
          break;
      }
    } else if (this.currentStep === 3) {
      // Approval & Submission step
      if (this.approvalForm) {
        this.approvalSubmissionData = this.approvalForm.getFormData();
      }
    }
  }

  /**
   * Handle save as draft
   */
  onSaveDraft(): void {
    this.saveCurrentStepData();
    this.submitTrf(true); // true = save as draft
  }

  /**
   * Handle final submission
   */
  onSubmit(): void {
    // Validate all steps
    if (!this.validateAllSteps()) {
      return;
    }

    // Save current step data
    this.saveCurrentStepData();

    // Submit the TRF
    this.submitTrf(false); // false = submit for approval
  }

  /**
   * Validate all steps
   */
  private validateAllSteps(): boolean {
    let isValid = true;

    // Validate requestor form
    if (this.requestorForm && !this.requestorForm.isValid()) {
      this.requestorForm.markAllAsTouched();
      this.currentStep = 1;
      isValid = false;
    }

    // Validate travel details form based on selected type
    if (!this.validateTravelDetailsForm()) {
      if (isValid) {
        this.currentStep = 2;
      }
      isValid = false;
    }

    // Validate approval form
    if (this.approvalForm && !this.approvalForm.isValid()) {
      this.approvalForm.markAllAsTouched();
      if (isValid) {
        this.currentStep = 3;
      }
      isValid = false;
    }

    return isValid;
  }

  /**
   * Submit TRF to backend
   */
  private submitTrf(isDraft: boolean): void {
    this.isSubmitting = true;
    this.submitError = '';

    // Combine all form data
    const combinedData = this.trfSubmission.prepareTrfData({
      selectedTravelType: this.selectedTravelType,
      requestorData: this.requestorData,
      domesticTravelData: this.domesticTravelData,
      overseasTravelData: this.overseasTravelData,
      homeLeaveData: this.homeLeaveData,
      externalPartiesData: this.externalPartiesData,
      additionalComments: this.approvalForm?.getFormData()?.additionalComments || '',
    });
    const passportFile = this.getPassportFileFromTravelForm();

    if (this.isEditMode && this.trfId) {
      // Update existing TRF
      // TrfService.updateTrf() is typed to take TravelRequestForm - the same
      // stale/mock model noted at loadExistingTrf() above, not what this
      // file actually builds - cast at this boundary rather than fixing
      // trf.service.ts's typing here.
      const mainTrfPayload = combinedData.mainTrf as unknown as Parameters<
        typeof this.trfService.updateTrf
      >[1];
      this.trfService.updateTrf(this.trfId, mainTrfPayload).subscribe({
        next: () => {
          // For edit mode, we might need to delete and recreate nested resources
          // This is a simplified approach - ideally, you'd update existing ones
          from(
            this.trfSubmission.createNestedResources(
              this.trfId!,
              combinedData,
              isDraft,
              this.isEditMode,
              this.requestorData,
              passportFile
            )
          ).subscribe({
            next: () => {
              // If not saving as draft, submit the TRF to workflow
              if (!isDraft) {
                // Get selected approvers and skipped steps from approval form
                const selectedApprovers = this.approvalSubmissionData?.selected_approvers || {};
                const skippedSteps = this.approvalSubmissionData?.skipped_steps || {};
                this.trfService
                  .submitTrf(this.trfId!, false, selectedApprovers, skippedSteps)
                  .subscribe({
                    next: () => {
                      this.isSubmitting = false;
                      this.toastService.success('TRF updated and submitted successfully!');
                      this.router.navigate(['/trf']);
                    },
                    error: (error: HttpErrorResponse) => {
                      this.isSubmitting = false;

                      let errorMessage = 'Error submitting TRF to workflow: ';
                      if (error.error && typeof error.error === 'object') {
                        if (error.error.error) {
                          errorMessage += error.error.error;
                        } else if (error.error.message) {
                          errorMessage += error.error.message;
                        } else if (error.error.detail) {
                          errorMessage += error.error.detail;
                        } else {
                          errorMessage += JSON.stringify(error.error);
                        }
                      } else if (error.error && typeof error.error === 'string') {
                        errorMessage += error.error;
                      } else if (error.message) {
                        errorMessage += error.message;
                      } else {
                        errorMessage += 'Unknown error';
                      }

                      this.submitError = errorMessage;
                      this.toastService.error(this.submitError);
                    },
                  });
              } else {
                this.isSubmitting = false;
                this.toastService.success('TRF updated and saved as draft!');
                this.router.navigate(['/trf']);
              }
            },
            error: (error: HttpErrorResponse) => {
              this.isSubmitting = false;
              this.submitError = this.errorHandler.getErrorMessage(
                error,
                'Error updating nested resources'
              );
              this.toastService.error(this.submitError);
            },
          });
        },
        error: (error: HttpErrorResponse) => {
          this.isSubmitting = false;
          this.submitError = this.errorHandler.getErrorMessage(error, 'Error updating TRF');
          this.toastService.error(this.submitError);
        },
      });
    } else {
      // Create new TRF
      this.trfService.createTravelRequest(combinedData.mainTrf).subscribe({
        next: (createdTrf: { id: number }) => {
          // Step 2: Create nested resources (itinerary, meals, etc.)
          from(
            this.trfSubmission.createNestedResources(
              createdTrf.id,
              combinedData,
              isDraft,
              this.isEditMode,
              this.requestorData,
              passportFile
            )
          ).subscribe({
            next: () => {
              // If not saving as draft, submit the TRF to generate request number and start workflow
              if (!isDraft) {
                // Get selected approvers and skipped steps from approval form
                const selectedApprovers = this.approvalSubmissionData?.selected_approvers || {};
                const skippedSteps = this.approvalSubmissionData?.skipped_steps || {};
                this.trfService
                  .submitTrf(createdTrf.id, false, selectedApprovers, skippedSteps)
                  .subscribe({
                    next: () => {
                      this.isSubmitting = false;
                      this.toastService.success('TRF submitted successfully!');
                      this.router.navigate(['/trf']);
                    },
                    error: (error: HttpErrorResponse) => {
                      this.isSubmitting = false;
                      this.submitError = this.errorHandler.getErrorMessage(
                        error,
                        'Error submitting TRF'
                      );
                      this.toastService.error(this.submitError);
                    },
                  });
              } else {
                this.isSubmitting = false;
                this.toastService.success('TRF saved as draft successfully!');
                this.router.navigate(['/trf']);
              }
            },
            error: (error: HttpErrorResponse) => {
              this.isSubmitting = false;
              this.submitError = this.errorHandler.getErrorMessage(
                error,
                'Error creating nested resources'
              );
              this.toastService.error(this.submitError);
            },
          });
        },
        error: (error: HttpErrorResponse) => {
          this.isSubmitting = false;
          this.submitError = this.errorHandler.getErrorMessage(error, 'Error creating TRF');
          this.toastService.error(this.submitError);
        },
      });
    }
  }

  /**
   * Get travel details for the approval component
   */
  getTravelDetailsForApproval():
    | Partial<DomesticTravelSpecificDetails>
    | Partial<OverseasTravelDetails>
    | Partial<HomeLeaveDetails>
    | Partial<ExternalPartiesDetails>
    | null {
    switch (this.selectedTravelType) {
      case 'Domestic':
        return this.domesticTravelData;
      case 'Overseas':
        return this.overseasTravelData;
      case 'Home Leave':
        return this.homeLeaveData;
      case 'External Parties':
        return this.externalPartiesData;
      default:
        return null;
    }
  }

  /**
   * Get passport file from the current travel form component
   */
  private getPassportFileFromTravelForm(): File | null {
    switch (this.selectedTravelType) {
      case 'Domestic':
        return this.domesticTravelForm?.getPassportFile?.() || null;
      case 'Overseas':
        return this.overseasTravelForm?.getPassportFile?.() || null;
      case 'Home Leave':
        return this.homeLeaveForm?.getPassportFile?.() || null;
      case 'External Parties':
        return this.externalPartiesForm?.getPassportFile?.() || null;
      default:
        return null;
    }
  }

  /**
   * Handle cancel
   */
  onCancel(): void {
    this.confirmationService.confirmCancel().subscribe(confirmed => {
      if (confirmed) {
        this.router.navigate(['/trf']);
      }
    });
  }
}
