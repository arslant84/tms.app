import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { from, firstValueFrom } from 'rxjs';
import { TrfStepperComponent } from '../trf-stepper/trf-stepper.component';
import { RequestorInformationComponent } from '../requestor-information/requestor-information.component';
import { DomesticTravelDetailsComponent } from '../domestic-travel-details/domestic-travel-details.component';
import { OverseasTravelDetailsComponent } from '../overseas-travel-details/overseas-travel-details.component';
import { HomeLeaveDetailsComponent } from '../home-leave-details/home-leave-details.component';
import { ExternalPartiesDetailsComponent } from '../external-parties-details/external-parties-details.component';
import { ApprovalSubmissionComponent } from '../approval-submission/approval-submission.component';
import { TrfService } from '../../services/trf.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { RbacService } from '../../../../core/services/rbac.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

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
    LoadingSpinnerComponent
  ],
  templateUrl: './trf-wizard.component.html',
  styleUrls: ['./trf-wizard.component.scss']
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
  existingTrfData: any = null;
  isLoadingTrf: boolean = false;

  // Travel type - determined by route
  selectedTravelType: 'Domestic' | 'Overseas' | 'Home Leave' | 'External Parties' | null = null;

  // Store form data from each step
  requestorData: any = {};
  domesticTravelData: any = {};
  overseasTravelData: any = {};
  homeLeaveData: any = {};
  externalPartiesData: any = {};
  approvalData: any = {}; // Store approval & submission data including additionalComments
  approvalSubmissionData: any = {};

  constructor(
    private trfService: TrfService,
    private router: Router,
    private route: ActivatedRoute,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private rbacService: RbacService
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
    const hasAdminView = this.rbacService.hasPermission('view_all_trf') ||
                         this.rbacService.hasPermission('manage_trf');

    this.trfService.getTrfById(id, false, hasAdminView).subscribe({
      next: (response: any) => {
        // The backend returns { trf: { ...data } }, so we need to extract the trf object
        const data = response.trf || response;

        this.existingTrfData = data;
        this.selectedTravelType = data.travel_type || data.travelType;

        // Check if TRF can be edited
        // Allow editing for Draft, Rejected, or any Pending status
        const canEdit = data.status === 'Draft' ||
                        data.status === 'Rejected' ||
                        data.status.startsWith('Pending');

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
          email: data.email
        };

        // Pre-populate approval data (additional comments, selected approvers, and skipped steps)
        this.approvalData = {
          additionalComments: data.additional_comments || data.additionalComments || '',
          selected_approvers: data.selected_approvers || {},
          skipped_steps: data.skipped_steps || {}
        };

        // Pre-populate travel-specific data based on type
        this.prePopulateTravelData(data);

        this.isLoadingTrf = false;
      },
      error: (err: any) => {
        this.submitError = 'Failed to load TRF: ' + (err.error?.message || err.message || 'Unknown error');
        this.isLoadingTrf = false;
      }
    });
  }

  /**
   * Pre-populate travel-specific data
   */
  private prePopulateTravelData(data: any): void {
    switch (this.selectedTravelType) {
      case 'Domestic':
        // Backend returns nested structure: data.domesticTravelDetails.itinerary
        const domesticDetails = data.domesticTravelDetails || {};
        const itineraryData = domesticDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const mealData = domesticDetails.mealProvision?.dailyMealSelections || data.daily_meals || data.daily_meal_selections || data.mealSelections || [];
        const domesticPassport = this.extractPassportFileInfo(data.passport_details || data.passportDetails);

        this.domesticTravelData = {
          purposeOfTravel: domesticDetails.purpose || data.purpose || '',
          tripType: data.trip_type || data.tripType || 'Round Trip',
          itinerary: this.transformItineraryData(itineraryData),
          mealProvisions: {
            dailySelections: this.transformMealSelectionsData(mealData)
          },
          passportUpload: domesticPassport
        };
        break;

      case 'Overseas':
        // Backend returns nested structure: data.overseasTravelDetails
        const overseasDetails = data.overseasTravelDetails || {};
        const overseasItinerary = overseasDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const bankDetails = overseasDetails.advanceBankDetails || data.bank_detail || data.advance_bank_details || data.bankDetails;
        const advanceAmounts = overseasDetails.advanceAmountRequested || data.advance_amounts || data.advance_amount_items || data.advanceAmounts || [];
        const overseasPassport = this.extractPassportFileInfo(data.passport_details || data.passportDetails);

        this.overseasTravelData = {
          purpose: overseasDetails.purpose || data.purpose || '',
          tripType: data.trip_type || data.tripType || 'Round Trip',
          itinerary: this.transformItineraryData(overseasItinerary),
          advanceBankDetails: this.transformBankDetails(bankDetails),
          advanceAmountRequested: this.transformAdvanceAmounts(advanceAmounts),
          passportUpload: overseasPassport
        };
        break;

      case 'Home Leave':
        // Backend returns nested structure: data.overseasTravelDetails (Home Leave reuses overseas structure)
        const homeLeaveDetails = data.overseasTravelDetails || {};
        const homeLeaveItinerary = homeLeaveDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const passportDetails = data.passport_details || data.passportDetails;
        const homeLeaveBank = homeLeaveDetails.advanceBankDetails || data.bank_detail || data.advance_bank_details || data.bankDetails;
        const homeLeaveAdvanceAmounts = homeLeaveDetails.advanceAmountRequested || data.advance_amounts || data.advance_amount_items || data.advanceAmounts || [];
        const homeLeavePassport = this.extractPassportFileInfo(passportDetails);

        this.homeLeaveData = {
          purpose: homeLeaveDetails.purpose || data.purpose || '',
          tripType: data.trip_type || data.tripType || 'Round Trip',
          itinerary: this.transformItineraryData(homeLeaveItinerary),
          passportDetails: this.transformPassportDetails(passportDetails),
          advanceBankDetails: this.transformBankDetails(homeLeaveBank),
          advanceAmountRequested: this.transformAdvanceAmounts(homeLeaveAdvanceAmounts),
          passportUpload: homeLeavePassport
        };
        break;

      case 'External Parties':
        // Backend returns nested structure: data.externalPartiesTravelDetails
        const externalDetails = data.externalPartiesTravelDetails || {};
        const externalRequestorInfo = data.externalPartyRequestorInfo || {};
        const externalItinerary = externalDetails.itinerary || data.itinerary_segments || data.itinerary || [];
        const externalPassport = this.extractPassportFileInfo(data.passport_details || data.passportDetails);

        this.externalPartiesData = {
          purpose: externalDetails.purpose || data.purpose || '',
          tripType: data.trip_type || data.tripType || 'One Way',
          externalFullName: externalRequestorInfo.externalFullName || data.external_full_name || data.externalFullName || '',
          externalOrganization: externalRequestorInfo.externalOrganization || data.external_organization || data.externalOrganization || '',
          externalRefToAuthorityLetter: externalRequestorInfo.externalRefToAuthorityLetter || data.external_ref_to_authority_letter || data.externalRefToAuthorityLetter || '',
          externalCostCenter: externalRequestorInfo.externalCostCenter || data.external_cost_center || data.externalCostCenter || '',
          itinerary: this.transformExternalPartiesItineraryData(externalItinerary),
          passportUpload: externalPassport
        };
        break;
    }
  }

  /**
   * Handle requestor form submission
   */
  onRequestorSubmit(data: any): void {
    this.requestorData = data;
    this.completedSteps[0] = true;
    this.currentStep = 2; // Move to travel details
  }

  /**
   * Handle travel details form submission
   */
  onTravelDetailsSubmit(data: any): void {
    // Save the data based on travel type
    switch (this.selectedTravelType) {
      case 'Domestic':
        this.domesticTravelData = data;
        break;
      case 'Overseas':
        this.overseasTravelData = data;
        break;
      case 'Home Leave':
        this.homeLeaveData = data;
        break;
      case 'External Parties':
        this.externalPartiesData = data;
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
          this.domesticTravelForm.markAllAsTouched();
          return false;
        }
        break;
      case 'Overseas':
        if (this.overseasTravelForm && !this.overseasTravelForm.isValid()) {
          this.overseasTravelForm.markAllAsTouched();
          return false;
        }
        break;
      case 'Home Leave':
        if (this.homeLeaveForm && !this.homeLeaveForm.isValid()) {
          this.homeLeaveForm.markAllAsTouched();
          return false;
        }
        break;
      case 'External Parties':
        if (this.externalPartiesForm && !this.externalPartiesForm.isValid()) {
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
    const combinedData = this.prepareTrfData(isDraft);

    if (this.isEditMode && this.trfId) {
      // Update existing TRF
      this.trfService.updateTrf(this.trfId, combinedData.mainTrf).subscribe({
        next: (updatedTrf: any) => {

          // For edit mode, we might need to delete and recreate nested resources
          // This is a simplified approach - ideally, you'd update existing ones
          from(this.createNestedResources(this.trfId!, combinedData)).subscribe({
            next: () => {
              // If not saving as draft, submit the TRF to workflow
              if (!isDraft) {
                // Get selected approvers and skipped steps from approval form
                const selectedApprovers = this.approvalSubmissionData?.selected_approvers || {};
                const skippedSteps = this.approvalSubmissionData?.skipped_steps || {};
                this.trfService.submitTrf(this.trfId!, false, selectedApprovers, skippedSteps).subscribe({
                  next: (submittedTrf: any) => {
                    this.isSubmitting = false;
                    this.toastService.success('TRF updated and submitted successfully!');
                    this.router.navigate(['/trf']);
                  },
                  error: (error: any) => {
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
                  }
                });
              } else {
                this.isSubmitting = false;
                this.toastService.success('TRF updated and saved as draft!');
                this.router.navigate(['/trf']);
              }
            },
            error: (error: any) => {
              this.isSubmitting = false;
              this.submitError = 'Error updating nested resources: ' + (error.message || 'Unknown error');
              this.toastService.error(this.submitError);
            }
          });
        },
        error: (error: any) => {
          this.isSubmitting = false;

          // Extract validation errors if available
          let errorMessage = 'Error updating TRF: ';
          if (error.error && typeof error.error === 'object') {
            if (error.error.non_field_errors) {
              errorMessage += error.error.non_field_errors.join(', ');
            } else if (error.error.message) {
              errorMessage += error.error.message;
            } else {
              // Flatten all field errors
              const fieldErrors = Object.entries(error.error)
                .map(([field, messages]: [string, any]) => {
                  if (Array.isArray(messages)) {
                    return `${field}: ${messages.join(', ')}`;
                  }
                  return `${field}: ${messages}`;
                })
                .join('; ');
              errorMessage += fieldErrors || error.message || 'Unknown error';
            }
          } else {
            errorMessage += error.message || 'Unknown error';
          }

          this.submitError = errorMessage;
          this.toastService.error(this.submitError);
        }
      });
    } else {
      // Create new TRF
      this.trfService.createTravelRequest(combinedData.mainTrf).subscribe({
        next: (createdTrf: any) => {

          // Step 2: Create nested resources (itinerary, meals, etc.)
          from(this.createNestedResources(createdTrf.id, combinedData)).subscribe({
            next: () => {
              // If not saving as draft, submit the TRF to generate request number and start workflow
              if (!isDraft) {
                // Get selected approvers and skipped steps from approval form
                const selectedApprovers = this.approvalSubmissionData?.selected_approvers || {};
                const skippedSteps = this.approvalSubmissionData?.skipped_steps || {};
                this.trfService.submitTrf(createdTrf.id, false, selectedApprovers, skippedSteps).subscribe({
                  next: (submittedTrf: any) => {
                    this.isSubmitting = false;
                    this.toastService.success('TRF submitted successfully!');
                    this.router.navigate(['/trf']);
                  },
                  error: (error: any) => {
                    this.isSubmitting = false;
                    this.submitError = 'Error submitting TRF: ' + (error.error?.error || error.error?.message || error.message || 'Unknown error');
                    this.toastService.error(this.submitError);
                  }
                });
              } else {
                this.isSubmitting = false;
                this.toastService.success('TRF saved as draft successfully!');
                this.router.navigate(['/trf']);
              }
            },
            error: (error: any) => {
              this.isSubmitting = false;
              this.submitError = 'Error creating nested resources: ' + (error.message || 'Unknown error');
              this.toastService.error(this.submitError);
            }
          });
        },
        error: (error: any) => {
          this.isSubmitting = false;
          this.submitError = 'Error creating TRF: ' + (error.error?.message || error.message || 'Unknown error');
          this.toastService.error(this.submitError);
        }
      });
    }
  }

  /**
   * Prepare TRF data for submission
   */
  private prepareTrfData(isDraft: boolean): any {
    // Main TRF data
    const mainTrf: any = {
      requestor_name: this.requestorData.fullName,
      staff_id: this.requestorData.staffId,
      department: this.requestorData.department,
      position: this.requestorData.position || '',
      cost_center: this.requestorData.costCenter,
      tel_email: this.requestorData.contactNo,
      email: this.requestorData.email,
      travel_type: this.selectedTravelType,
      // Always create as Draft, then call submit endpoint to generate request number
      status: 'Draft',
      estimated_cost: 0
    };

    // Prepare data based on travel type
    switch (this.selectedTravelType) {
      case 'Domestic':
        return this.prepareDomesticData(mainTrf, isDraft);
      case 'Overseas':
        return this.prepareOverseasData(mainTrf, isDraft);
      case 'Home Leave':
        return this.prepareHomeLeaveData(mainTrf, isDraft);
      case 'External Parties':
        return this.prepareExternalPartiesData(mainTrf, isDraft);
      default:
        return { mainTrf, itinerarySegments: [], mealSelections: [] };
    }
  }

  /**
   * Prepare Domestic travel data
   */
  private prepareDomesticData(mainTrf: any, isDraft: boolean): any {
    mainTrf.purpose = this.domesticTravelData?.purposeOfTravel || '';
    mainTrf.additional_comments = this.approvalForm?.getFormData()?.additionalComments || '';

    return {
      mainTrf,
      itinerarySegments: this.domesticTravelData?.itinerary || [],
      mealSelections: this.domesticTravelData?.mealProvisions?.dailySelections || [],
      passportDetails: null,
      bankDetails: null,
      advanceAmounts: []
    };
  }

  /**
   * Prepare Overseas travel data
   */
  private prepareOverseasData(mainTrf: any, isDraft: boolean): any {
    mainTrf.purpose = this.overseasTravelData?.purpose || '';
    mainTrf.additional_comments = this.approvalForm?.getFormData()?.additionalComments || '';

    return {
      mainTrf,
      itinerarySegments: this.overseasTravelData?.itinerary || [],
      mealSelections: [],
      passportDetails: null,
      bankDetails: this.overseasTravelData?.advanceBankDetails || null,
      advanceAmounts: this.overseasTravelData?.advanceAmountRequested || []
    };
  }

  /**
   * Prepare Home Leave data
   */
  private prepareHomeLeaveData(mainTrf: any, isDraft: boolean): any {
    mainTrf.purpose = this.homeLeaveData?.purpose || '';
    mainTrf.additional_comments = this.approvalForm?.getFormData()?.additionalComments || '';

    return {
      mainTrf,
      itinerarySegments: this.homeLeaveData?.itinerary || [],
      mealSelections: [],
      passportDetails: this.homeLeaveData?.passportDetails || null,
      bankDetails: this.homeLeaveData?.advanceBankDetails || null,
      advanceAmounts: this.homeLeaveData?.advanceAmountRequested || []
    };
  }

  /**
   * Prepare External Parties data
   */
  private prepareExternalPartiesData(mainTrf: any, isDraft: boolean): any {
    mainTrf.purpose = this.externalPartiesData?.purpose || '';
    mainTrf.additional_comments = this.approvalForm?.getFormData()?.additionalComments || '';

    // Add external party specific fields - CORRECTED FIELD NAMES
    mainTrf.external_full_name = this.externalPartiesData?.externalFullName || '';
    mainTrf.external_organization = this.externalPartiesData?.externalOrganization || '';
    mainTrf.external_ref_to_authority_letter = this.externalPartiesData?.externalRefToAuthorityLetter || '';
    mainTrf.external_cost_center = this.externalPartiesData?.externalCostCenter || '';

    return {
      mainTrf,
      itinerarySegments: this.externalPartiesData?.itinerary || [],
      mealSelections: [],
      passportDetails: null,
      bankDetails: null,
      advanceAmounts: []
    };
  }

  /**
   * Convert Date object or ISO string to YYYY-MM-DD format
   */
  private formatDateForAPI(date: any): string {
    if (!date) return '';

    const dateObj = typeof date === 'string' ? new Date(date) : date;

    if (!(dateObj instanceof Date) || isNaN(dateObj.getTime())) {
      return '';
    }

    const year = dateObj.getFullYear();
    const month = String(dateObj.getMonth() + 1).padStart(2, '0');
    const day = String(dateObj.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
  }

  /**
   * Delete existing nested resources for a TRF (used during update to prevent duplicates)
   */
  private deleteExistingNestedResources(trfId: number): Promise<void> {

    const promises: Promise<any>[] = [];

    // Delete all existing nested resources
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'itinerary')).catch(err => {
      })
    );
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'meals')).catch(err => {
      })
    );
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'passport')).catch(err => {
      })
    );
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'bank')).catch(err => {
      })
    );
    promises.push(
      firstValueFrom(this.trfService.deleteNestedResources(trfId, 'advance-amounts')).catch(err => {
      })
    );

    return Promise.all(promises).then(() => {
    });
  }

  /**
   * Create nested resources (itinerary, meals, passport, bank details, etc.)
   */
  private createNestedResources(trfId: number, data: any): any {
    return new Promise(async (resolve, reject) => {

      // Guard: Ensure trfId is valid
      if (!trfId || typeof trfId !== 'number' || trfId <= 0) {
        const error = `Invalid TRF ID: ${trfId}`;
        reject(new Error(error));
        return;
      }

      // If in edit mode, delete existing nested resources first to prevent duplicates
      if (this.isEditMode) {
        try {
          await this.deleteExistingNestedResources(trfId);
        } catch (err) {
          // Continue anyway - some resources might not exist
        }
      }

      const promises: Promise<any>[] = [];

      // Create itinerary segments
      if (data.itinerarySegments && data.itinerarySegments.length > 0) {
        data.itinerarySegments.forEach((segment: any) => {
          // Handle both standard fields (date, from, to) and External Parties fields (departureDate, departureLocation, arrivalLocation)
          const date = segment.date || segment.departureDate;
          const from = segment.from || segment.departureLocation;
          const to = segment.to || segment.arrivalLocation;

          // Skip segments with missing required fields
          if (!date || !from || !to) {
            return;
          }

          const itineraryData = {
            trf: trfId,
            segment_date: this.formatDateForAPI(date),
            day_of_week: segment.day || '',
            from_location: from,
            to_location: to,
            departure_time: segment.departureTime || segment.etd || '',
            arrival_time: segment.arrivalTime || segment.eta || '',
            flight_number: segment.modeOfTransport || segment.flightNumber || '',
            remarks: segment.remarks || ''
          };

          promises.push(
            firstValueFrom(this.trfService.createItinerarySegment(itineraryData))
          );
        });
      }

      // Create meal selections (Domestic only)
      if (data.mealSelections && data.mealSelections.length > 0) {
        data.mealSelections.forEach((meal: any) => {
          // Skip meals with missing required meal_date
          if (!meal.date) {
            return;
          }

          const mealData = {
            trf: trfId,
            meal_date: this.formatDateForAPI(meal.date),
            breakfast: meal.breakfast || false,
            lunch: meal.lunch || false,
            dinner: meal.dinner || false,
            supper: meal.supper || false,
            refreshment: meal.refreshment || false
          };

          promises.push(
            firstValueFrom(this.trfService.createDailyMeal(mealData))
          );
        });
      }

      // Create passport details (Home Leave)
      if (data.passportDetails) {
        const passportData = {
          trf: trfId,
          full_name: data.passportDetails.fullName || '',
          passport_number: data.passportDetails.passportNumber || '',
          nationality: data.passportDetails.nationality || '',
          date_of_birth: data.passportDetails.dateOfBirth || '',
          place_of_birth: data.passportDetails.placeOfBirth || '',
          passport_issue_date: data.passportDetails.passportIssueDate || '',
          passport_expiry_date: data.passportDetails.passportExpiryDate || ''
        };

        // Note: Need to create passport details endpoint in service
        // For now, we'll skip if not available
        if (this.trfService.createPassportDetail) {
          promises.push(
            firstValueFrom(this.trfService.createPassportDetail(passportData))
          );
        }
      }

      // Create bank details (Overseas, Home Leave)
      if (data.bankDetails) {
        const bankData = {
          trf: trfId,
          bank_name: data.bankDetails.bankName || '',
          account_number: data.bankDetails.accountNumber || '',
          account_name: data.bankDetails.accountName || '',
          branch_address: data.bankDetails.branchAddress || '',
          currency: data.bankDetails.currency || 'USD'
        };

        promises.push(
          firstValueFrom(this.trfService.createBankDetail(bankData))
        );
      }

      // Create advance amount items (Overseas, Home Leave)
      if (data.advanceAmounts && data.advanceAmounts.length > 0) {
        data.advanceAmounts.forEach((amount: any) => {
          const advanceData = {
            trf: trfId,
            date_from: amount.dateFrom || '',
            date_to: amount.dateTo || '',
            lh: amount.lh || 0,
            ma: amount.ma || 0,
            oa: amount.oa || 0,
            tr: amount.tr || 0,
            oe: amount.oe || 0,
            usd: amount.usd || 0,
            remarks: amount.remarks || ''
          };

          promises.push(
            firstValueFrom(this.trfService.createAdvanceAmountItem(advanceData))
          );
        });
      }

      // Upload passport file if provided
      const passportFile = this.getPassportFileFromTravelForm();
      if (passportFile) {
        promises.push(
          firstValueFrom(this.trfService.uploadPassportDocument(trfId, passportFile))
        );
      }

      // Wait for all nested resources to be created

      Promise.all(promises)
        .then(() => {
          resolve(true);
        })
        .catch((error) => {
          if (error.error) {
          }
          reject(error);
        });
    });
  }

  /**
   * Get travel details for the approval component
   */
  getTravelDetailsForApproval(): any {
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

  /**
   * Transform itinerary data from backend format to component format
   */
  private transformItineraryData(itinerary: any[]): any[] {
    return itinerary.map((segment: any) => ({
      date: segment.segment_date || segment.date || null,
      day: segment.day_of_week || segment.day || '',
      from: segment.from_location || segment.from || '',
      to: segment.to_location || segment.to || '',
      etd: segment.departure_time || segment.etd || '',
      eta: segment.arrival_time || segment.eta || '',
      flightNumber: segment.flight_number || segment.flightNumber || '',
      remarks: segment.remarks || ''
    }));
  }

  /**
   * Transform itinerary data specifically for External Parties
   * External Parties component expects different field names
   */
  private transformExternalPartiesItineraryData(itinerary: any[]): any[] {

    const transformed = itinerary.map((segment: any) => {
      const result = {
        departureDate: segment.segment_date || segment.date || segment.departureDate || null,
        day: segment.day_of_week || segment.day || '',
        departureTime: segment.departure_time || segment.etd || segment.departureTime || '',
        departureLocation: segment.from_location || segment.from || segment.departureLocation || '',
        arrivalDate: segment.arrival_date || segment.date || segment.arrivalDate || null,
        arrivalTime: segment.arrival_time || segment.eta || segment.arrivalTime || '',
        arrivalLocation: segment.to_location || segment.to || segment.arrivalLocation || '',
        modeOfTransport: segment.mode_of_transport || segment.modeOfTransport || segment.flight_number || segment.flightNumber || '',
        remarks: segment.remarks || ''
      };
      return result;
    });

    return transformed;
  }

  /**
   * Transform meal selections data from backend format to component format
   */
  private transformMealSelectionsData(mealSelections: any[]): any[] {

    const transformed = mealSelections.map((meal: any) => {
      const result = {
        date: meal.meal_date || meal.date || null,
        // Explicitly handle boolean values - backend returns true/false
        breakfast: meal.breakfast === true || meal.breakfast === 'true' || meal.breakfast === 1,
        lunch: meal.lunch === true || meal.lunch === 'true' || meal.lunch === 1,
        dinner: meal.dinner === true || meal.dinner === 'true' || meal.dinner === 1,
        supper: meal.supper === true || meal.supper === 'true' || meal.supper === 1,
        refreshment: meal.refreshment === true || meal.refreshment === 'true' || meal.refreshment === 1
      };
      return result;
    });

    return transformed;
  }

  /**
   * Transform bank details from backend format to component format
   */
  private transformBankDetails(bankDetail: any): any {
    if (!bankDetail || Object.keys(bankDetail).length === 0) {
      return {
        bankName: '',
        accountNumber: '',
        accountName: '',
        branchAddress: '',
        currency: 'USD'
      };
    }

    return {
      bankName: bankDetail.bank_name || bankDetail.bankName || '',
      accountNumber: bankDetail.account_number || bankDetail.accountNumber || '',
      accountName: bankDetail.account_name || bankDetail.accountName || '',
      branchAddress: bankDetail.branch_address || bankDetail.branchAddress || '',
      currency: bankDetail.currency || 'USD'
    };
  }

  /**
   * Transform advance amounts from backend format to component format
   */
  private transformAdvanceAmounts(advanceAmounts: any[]): any[] {
    if (!advanceAmounts || advanceAmounts.length === 0) {
      return [];
    }

    return advanceAmounts.map((item: any) => ({
      dateFrom: item.date_from || item.dateFrom || null,
      dateTo: item.date_to || item.dateTo || null,
      lh: item.lh || 0,
      ma: item.ma || 0,
      oa: item.oa || 0,
      tr: item.tr || 0,
      oe: item.oe || 0,
      usd: item.usd || 0,
      remarks: item.remarks || ''
    }));
  }

  /**
   * Extract passport file info from passport details for upload component
   */
  private extractPassportFileInfo(passportDetails: any): any {
    if (!passportDetails) {
      return { file: null, fileName: '', fileUrl: '' };
    }

    // Handle array format from backend
    const detail = Array.isArray(passportDetails) ? passportDetails[0] : passportDetails;

    if (!detail) {
      return { file: null, fileName: '', fileUrl: '' };
    }

    const fileUrl = detail.passport_file_url || detail.passportFileUrl || detail.passport_file || '';
    const fileName = fileUrl ? fileUrl.split('/').pop() || '' : '';

    return {
      file: null, // File object is not available from backend, only URL
      fileName: fileName,
      fileUrl: fileUrl
    };
  }

  /**
   * Transform passport details from backend format to component format
   */
  private transformPassportDetails(passportDetails: any): any {
    // Backend returns array, we need first element
    if (Array.isArray(passportDetails) && passportDetails.length > 0) {
      const detail = passportDetails[0];
      return {
        fullName: detail.full_name || detail.fullName || '',
        passportNumber: detail.passport_number || detail.passportNumber || '',
        nationality: detail.nationality || '',
        dateOfBirth: detail.date_of_birth || detail.dateOfBirth || null,
        placeOfBirth: detail.place_of_birth || detail.placeOfBirth || '',
        passportIssueDate: detail.passport_issue_date || detail.passportIssueDate || null,
        passportExpiryDate: detail.passport_expiry_date || detail.passportExpiryDate || null
      };
    }

    // If already an object (not array)
    if (passportDetails && !Array.isArray(passportDetails)) {
      return {
        fullName: passportDetails.full_name || passportDetails.fullName || '',
        passportNumber: passportDetails.passport_number || passportDetails.passportNumber || '',
        nationality: passportDetails.nationality || '',
        dateOfBirth: passportDetails.date_of_birth || passportDetails.dateOfBirth || null,
        placeOfBirth: passportDetails.place_of_birth || passportDetails.placeOfBirth || '',
        passportIssueDate: passportDetails.passport_issue_date || passportDetails.passportIssueDate || null,
        passportExpiryDate: passportDetails.passport_expiry_date || passportDetails.passportExpiryDate || null
      };
    }

    // Return empty object if no data
    return {
      fullName: '',
      passportNumber: '',
      nationality: '',
      dateOfBirth: null,
      placeOfBirth: '',
      passportIssueDate: null,
      passportExpiryDate: null
    };
  }
}
