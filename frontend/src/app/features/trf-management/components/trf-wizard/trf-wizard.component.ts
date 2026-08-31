import { CommonModule } from '@angular/common';
import type { HttpErrorResponse } from '@angular/common/http';
import { Component, type OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { from } from 'rxjs';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { RbacService } from '../../../../core/services/rbac.service';
import { ToastService } from '../../../../core/services/toast.service';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { TrfService } from '../../services/trf.service';
import {
  ApprovalSubmissionComponent,
  type ApprovalSubmissionData,
} from '../approval-submission/approval-submission.component';
import {
  DomesticTravelDetailsComponent,
  type DomesticTravelSpecificDetails,
} from '../domestic-travel-details/domestic-travel-details.component';
import {
  type ExternalPartiesDetails,
  ExternalPartiesDetailsComponent,
} from '../external-parties-details/external-parties-details.component';
import {
  type OverseasTravelDetails,
  OverseasTravelDetailsComponent,
} from '../overseas-travel-details/overseas-travel-details.component';
import {
  type RequestorInformation,
  RequestorInformationComponent,
} from '../requestor-information/requestor-information.component';
import { TrfStepperComponent } from '../trf-stepper/trf-stepper.component';
import { TrfEditLoaderService } from './trf-edit-loader.service';
import { TrfSubmissionService } from './trf-submission.service';
import type { TrfBackendResponse } from './trf-wizard.types';

@Component({
  selector: 'app-trf-wizard',
  standalone: true,
  imports: [
    CommonModule,
    TrfStepperComponent,
    RequestorInformationComponent,
    DomesticTravelDetailsComponent,
    OverseasTravelDetailsComponent,
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
  // Whether this TRF already has a linked accommodation/transport request
  // (fetched via loadLinkedAccommodation/loadLinkedTransport below). This is
  // distinct from isEditMode: a Draft TRF that's being edited for the very
  // first "real" submission is still isEditMode=true but has no linked
  // accommodation/transport yet, and createNestedResources() must still be
  // allowed to create them then - see hasLinkedAccommodation/hasLinkedTransport
  // usage in submitTrf() below.
  hasLinkedAccommodation: boolean = false;
  hasLinkedTransport: boolean = false;

  // Travel type - determined by route
  selectedTravelType: 'Domestic' | 'Overseas' | 'External Parties' | null = null;

  // Store form data from each step
  requestorData: Partial<RequestorInformation> = {};
  domesticTravelData: Partial<DomesticTravelSpecificDetails> = {};
  overseasTravelData: Partial<OverseasTravelDetails> = {};
  externalPartiesData: Partial<ExternalPartiesDetails> = {};
  approvalData: Partial<ApprovalSubmissionData> = {}; // Store approval & submission data including additionalComments
  approvalSubmissionData: Partial<ApprovalSubmissionData> = {};

  constructor(
    private trfService: TrfService,
    private router: Router,
    private route: ActivatedRoute,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private rbacService: RbacService,
    private errorHandler: HttpErrorHandlerService,
    private trfSubmission: TrfSubmissionService,
    private trfEditLoader: TrfEditLoaderService
  ) {}

  ngOnInit(): void {
    // Determine travel type from route
    const url = this.router.url;
    if (url.includes('/create/domestic')) {
      this.selectedTravelType = 'Domestic';
    } else if (url.includes('/create/overseas')) {
      this.selectedTravelType = 'Overseas';
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

    this.trfEditLoader.loadForEdit(id, hasAdminView).subscribe({
      next: data => {
        this.existingTrfData = data;
        this.selectedTravelType = (data.travel_type ||
          data.travelType) as typeof this.selectedTravelType;

        if (data.status && !this.trfEditLoader.canEditStatus(data.status)) {
          const errorMsg = `This TRF cannot be edited because its status is "${data.status}". Only Draft, Rejected, or Pending TRFs can be edited.`;
          this.isLoadingTrf = false;

          // Show error toast and redirect back to list
          this.toastService.error(errorMsg);
          setTimeout(() => {
            this.router.navigate(['/trf']);
          }, 3000);
          return;
        }

        this.requestorData = this.trfEditLoader.buildRequestorData(data);
        this.approvalData = this.trfEditLoader.buildApprovalData(data);

        const travelTypeData = this.trfEditLoader.buildTravelTypeData(
          this.selectedTravelType,
          data
        );
        if (travelTypeData.domesticTravelData) {
          this.domesticTravelData = travelTypeData.domesticTravelData;
          // Merged in asynchronously, separately from the main TRF payload -
          // see TrfEditLoaderService.loadLinkedAccommodation/loadLinkedTransport.
          // Assigns a new object each time so DomesticTravelDetailsComponent's
          // ngOnChanges (which rebuilds the form on non-first initialData
          // changes) picks it up.
          this.trfEditLoader.loadLinkedAccommodation(data.id).subscribe(accommodation => {
            if (accommodation) {
              this.domesticTravelData = { ...this.domesticTravelData, accommodation };
              this.hasLinkedAccommodation = true;
            }
          });
          this.trfEditLoader.loadLinkedTransport(data.id).subscribe(transport => {
            if (transport) {
              this.domesticTravelData = { ...this.domesticTravelData, transport };
              this.hasLinkedTransport = true;
            }
          });
        }
        if (travelTypeData.overseasTravelData) {
          this.overseasTravelData = travelTypeData.overseasTravelData;
        }
        if (travelTypeData.externalPartiesData) {
          this.externalPartiesData = travelTypeData.externalPartiesData;
          // Same reasoning as the Domestic branch above - accommodation/
          // transport are embedded here the same way as Domestic, and are
          // likewise linked via AccommodationRequest.trf/TransportRequest.trf
          // rather than being part of the TRF payload itself.
          this.trfEditLoader.loadLinkedAccommodation(data.id).subscribe(accommodation => {
            if (accommodation) {
              this.externalPartiesData = { ...this.externalPartiesData, accommodation };
              this.hasLinkedAccommodation = true;
            }
          });
          this.trfEditLoader.loadLinkedTransport(data.id).subscribe(transport => {
            if (transport) {
              this.externalPartiesData = { ...this.externalPartiesData, transport };
              this.hasLinkedTransport = true;
            }
          });
        }

        this.isLoadingTrf = false;
      },
      error: (err: HttpErrorResponse) => {
        this.submitError = `Failed to load TRF: ${err.error?.message || err.message || 'Unknown error'}`;
        this.isLoadingTrf = false;
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
    data: DomesticTravelSpecificDetails | OverseasTravelDetails | ExternalPartiesDetails
  ): void {
    // Save the data based on travel type
    switch (this.selectedTravelType) {
      case 'Domestic':
        this.domesticTravelData = data as DomesticTravelSpecificDetails;
        break;
      case 'Overseas':
        this.overseasTravelData = data as OverseasTravelDetails;
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
      externalPartiesData: this.externalPartiesData,
      additionalComments: this.approvalForm?.getFormData()?.additionalComments || '',
    });
    const passportFile = this.getPassportFileFromTravelForm();

    if (this.isEditMode && this.trfId) {
      // Narrow to a local const: this.trfId is a mutable class property, so
      // TS can't carry the `if` check's truthiness narrowing into the
      // .subscribe() callback closures below - a local const can.
      const trfId = this.trfId;
      // Update existing TRF
      // TrfService.updateTrf() is typed to take TravelRequestForm - the same
      // stale/mock model noted at loadExistingTrf() above, not what this
      // file actually builds - cast at this boundary rather than fixing
      // trf.service.ts's typing here.
      const mainTrfPayload = combinedData.mainTrf as unknown as Parameters<
        typeof this.trfService.updateTrf
      >[1];
      this.trfService.updateTrf(trfId, mainTrfPayload).subscribe({
        next: () => {
          // For edit mode, we might need to delete and recreate nested resources
          // This is a simplified approach - ideally, you'd update existing ones
          from(
            this.trfSubmission.createNestedResources(
              trfId,
              combinedData,
              isDraft,
              this.isEditMode,
              this.requestorData,
              passportFile,
              this.hasLinkedAccommodation,
              this.hasLinkedTransport
            )
          ).subscribe({
            next: () => {
              // If not saving as draft, submit the TRF to workflow
              if (!isDraft) {
                // Get selected approvers and skipped steps from approval form
                const selectedApprovers = this.approvalSubmissionData?.selected_approvers || {};
                const skippedSteps = this.approvalSubmissionData?.skipped_steps || {};
                this.trfService.submitTrf(trfId, false, selectedApprovers, skippedSteps).subscribe({
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
        next: (raw: unknown) => {
          const createdTrf = raw as { id: number };
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
    | Partial<ExternalPartiesDetails>
    | null {
    switch (this.selectedTravelType) {
      case 'Domestic':
        return this.domesticTravelData;
      case 'Overseas':
        return this.overseasTravelData;
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
