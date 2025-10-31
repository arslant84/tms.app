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
    ApprovalSubmissionComponent
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
  approvalSubmissionData: any = {};

  constructor(
    private trfService: TrfService,
    private router: Router,
    private route: ActivatedRoute,
    private toastService: ToastService,
    private confirmationService: ConfirmationService
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

    console.log('TRF Wizard initialized');
    console.log('Current step:', this.currentStep);
    console.log('Total steps:', this.totalSteps);
    console.log('Selected travel type:', this.selectedTravelType);
    console.log('Edit mode:', this.isEditMode);
  }

  /**
   * Load existing TRF data for editing
   */
  private loadExistingTrf(id: number): void {
    this.isLoadingTrf = true;

    // TODO: Use the proper GET endpoint once available
    // For now, this is a placeholder
    this.trfService.getTrfById(id).subscribe({
      next: (data: any) => {
        this.existingTrfData = data;
        this.selectedTravelType = data.travel_type || data.travelType;

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

        // Pre-populate travel-specific data based on type
        this.prePopulateTravelData(data);

        this.isLoadingTrf = false;
      },
      error: (err: any) => {
        this.submitError = 'Failed to load TRF: ' + (err.error?.message || err.message || 'Unknown error');
        this.isLoadingTrf = false;
        console.error('Error loading TRF:', err);
      }
    });
  }

  /**
   * Pre-populate travel-specific data
   */
  private prePopulateTravelData(data: any): void {
    switch (this.selectedTravelType) {
      case 'Domestic':
        this.domesticTravelData = {
          purposeOfTravel: data.purpose,
          tripType: data.trip_type || data.tripType || 'Round Trip',
          itinerary: data.itinerary || [],
          mealProvisions: {
            dailySelections: data.daily_meal_selections || data.mealSelections || []
          },
          accommodation: data.accommodation_details?.[0] || data.accommodation || {},
          companyTransportation: data.company_transport_details || data.transportDetails || []
        };
        break;

      case 'Overseas':
        this.overseasTravelData = {
          purpose: data.purpose,
          tripType: data.trip_type || data.tripType || 'Round Trip',
          itinerary: data.itinerary || [],
          advanceBankDetails: data.advance_bank_details || data.bankDetails || {},
          advanceAmountRequested: data.advance_amount_items || data.advanceAmounts || []
        };
        break;

      case 'Home Leave':
        this.homeLeaveData = {
          purpose: data.purpose,
          tripType: data.trip_type || data.tripType || 'Round Trip',
          itinerary: data.itinerary || [],
          passportDetails: data.passport_details || data.passportDetails || {},
          advanceBankDetails: data.advance_bank_details || data.bankDetails || {}
        };
        break;

      case 'External Parties':
        this.externalPartiesData = {
          purpose: data.purpose,
          tripType: data.trip_type || data.tripType || 'One Way',
          externalFullName: data.external_full_name || data.externalFullName || '',
          externalOrganization: data.external_organization || data.externalOrganization || '',
          externalRefToAuthorityLetter: data.external_ref_to_authority_letter || data.externalRefToAuthorityLetter || '',
          externalCostCenter: data.external_cost_center || data.externalCostCenter || '',
          itinerary: data.itinerary_segments || data.itinerary || [],
          accommodation: data.accommodation_details || data.accommodation || [],
          transport: data.transport_details || data.transport || []
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
          console.log('TRF updated successfully:', updatedTrf);

          // For edit mode, we might need to delete and recreate nested resources
          // This is a simplified approach - ideally, you'd update existing ones
          from(this.createNestedResources(this.trfId!, combinedData)).subscribe({
            next: () => {
              this.isSubmitting = false;

              // Show success message and navigate
              this.toastService.success(isDraft ? 'TRF updated and saved as draft!' : 'TRF updated successfully!');
              this.router.navigate(['/trf']);
            },
            error: (error: any) => {
              this.isSubmitting = false;
              this.submitError = 'Error updating nested resources: ' + (error.message || 'Unknown error');
              this.toastService.error(this.submitError);
              console.error('Error updating nested resources:', error);
            }
          });
        },
        error: (error: any) => {
          this.isSubmitting = false;
          this.submitError = 'Error updating TRF: ' + (error.error?.message || error.message || 'Unknown error');
          this.toastService.error(this.submitError);
          console.error('Error updating TRF:', error);
        }
      });
    } else {
      // Create new TRF
      this.trfService.createTravelRequest(combinedData.mainTrf).subscribe({
        next: (createdTrf: any) => {
          console.log('TRF created successfully:', createdTrf);
          console.log('TRF response keys:', Object.keys(createdTrf));
          console.log('TRF.id:', createdTrf.id);
          console.log('TRF.pk:', createdTrf.pk);

          // Step 2: Create nested resources (itinerary, meals, accommodation, transport)
          from(this.createNestedResources(createdTrf.id, combinedData)).subscribe({
            next: () => {
              this.isSubmitting = false;

              // Show success message and navigate
              this.toastService.success(isDraft ? 'TRF saved as draft successfully!' : 'TRF submitted successfully!');
              this.router.navigate(['/trf']);
            },
            error: (error: any) => {
              this.isSubmitting = false;
              this.submitError = 'Error creating nested resources: ' + (error.message || 'Unknown error');
              this.toastService.error(this.submitError);
              console.error('Error creating nested resources:', error);
            }
          });
        },
        error: (error: any) => {
          this.isSubmitting = false;
          this.submitError = 'Error creating TRF: ' + (error.error?.message || error.message || 'Unknown error');
          this.toastService.error(this.submitError);
          console.error('Error creating TRF:', error);
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
      status: isDraft ? 'Draft' : 'Pending Department Focal',
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
        return { mainTrf, itinerarySegments: [], mealSelections: [], accommodation: null, transport: [] };
    }
  }

  /**
   * Prepare Domestic travel data
   */
  private prepareDomesticData(mainTrf: any, isDraft: boolean): any {
    mainTrf.purpose = this.domesticTravelData?.purposeOfTravel || '';
    mainTrf.additional_comments = '';

    return {
      mainTrf,
      itinerarySegments: this.domesticTravelData?.itinerary || [],
      mealSelections: this.domesticTravelData?.mealProvisions?.dailySelections || [],
      accommodation: this.domesticTravelData?.accommodation || null,
      transport: this.domesticTravelData?.companyTransportation || [],
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
    mainTrf.additional_comments = '';

    return {
      mainTrf,
      itinerarySegments: this.overseasTravelData?.itinerary || [],
      mealSelections: [],
      accommodation: null,
      transport: [],
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
    mainTrf.additional_comments = '';

    return {
      mainTrf,
      itinerarySegments: this.homeLeaveData?.itinerary || [],
      mealSelections: [],
      accommodation: null,
      transport: [],
      passportDetails: this.homeLeaveData?.passportDetails || null,
      bankDetails: this.homeLeaveData?.advanceBankDetails || null,
      advanceAmounts: []
    };
  }

  /**
   * Prepare External Parties data
   */
  private prepareExternalPartiesData(mainTrf: any, isDraft: boolean): any {
    mainTrf.purpose = this.externalPartiesData?.purpose || '';
    mainTrf.additional_comments = '';

    // Add external party specific fields - CORRECTED FIELD NAMES
    mainTrf.external_full_name = this.externalPartiesData?.externalFullName || '';
    mainTrf.external_organization = this.externalPartiesData?.externalOrganization || '';
    mainTrf.external_ref_to_authority_letter = this.externalPartiesData?.externalRefToAuthorityLetter || '';
    mainTrf.external_cost_center = this.externalPartiesData?.externalCostCenter || '';

    return {
      mainTrf,
      itinerarySegments: this.externalPartiesData?.itinerary || [],
      mealSelections: [],
      accommodation: this.externalPartiesData?.accommodation || [],
      transport: this.externalPartiesData?.transport || [],
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
      console.warn('Invalid date:', date);
      return '';
    }

    const year = dateObj.getFullYear();
    const month = String(dateObj.getMonth() + 1).padStart(2, '0');
    const day = String(dateObj.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
  }

  /**
   * Create nested resources (itinerary, meals, passport, bank details, etc.)
   */
  private createNestedResources(trfId: number, data: any): any {
    return new Promise((resolve, reject) => {
      console.log('=== Creating Nested Resources ===');
      console.log('TRF ID:', trfId);
      console.log('TRF ID type:', typeof trfId);
      console.log('TRF ID is number:', typeof trfId === 'number');
      console.log('TRF ID is valid:', trfId && trfId > 0);
      console.log('Data:', JSON.stringify(data, null, 2));

      // Guard: Ensure trfId is valid
      if (!trfId || typeof trfId !== 'number' || trfId <= 0) {
        const error = `Invalid TRF ID: ${trfId}`;
        console.error(error);
        reject(new Error(error));
        return;
      }

      const promises: Promise<any>[] = [];

      // Create itinerary segments
      if (data.itinerarySegments && data.itinerarySegments.length > 0) {
        data.itinerarySegments.forEach((segment: any) => {
          // Skip segments with missing required fields
          if (!segment.date || !segment.from || !segment.to) {
            console.warn('Skipping itinerary segment with missing required fields:', segment);
            return;
          }

          const itineraryData = {
            trf: trfId,
            segment_date: this.formatDateForAPI(segment.date),
            day_of_week: segment.day || '',
            from_location: segment.from,
            to_location: segment.to,
            departure_time: segment.departureTime || segment.etd || '',
            arrival_time: segment.arrivalTime || segment.eta || '',
            flight_number: segment.flightNumber || '',
            remarks: segment.remarks || ''
          };

          console.log('Creating itinerary segment:', itineraryData);
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
            console.warn('Skipping meal selection with missing date:', meal);
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

          console.log('Creating meal selection:', mealData);
          promises.push(
            firstValueFrom(this.trfService.createDailyMeal(mealData))
          );
        });
      }

      // Create accommodation (can be single object or array)
      if (data.accommodation) {
        if (Array.isArray(data.accommodation)) {
          // External Parties accommodation (array)
          data.accommodation.forEach((acc: any) => {
            // Skip accommodation with missing required fields
            if (!acc.fromDate || !acc.toDate) {
              console.warn('Skipping accommodation with missing dates:', acc);
              return;
            }

            const accommodationData = {
              trf: trfId,
              accommodation_type: acc.accommodationType || '',
              check_in_date: this.formatDateForAPI(acc.fromDate),
              check_in_time: '',
              check_out_date: this.formatDateForAPI(acc.toDate),
              check_out_time: '',
              location: acc.fromLocation || '',
              address: acc.address || '',
              place_of_stay: acc.toLocation || '',
              remarks: acc.remarks || ''
            };

            console.log('Creating accommodation (array):', accommodationData);
            promises.push(
              firstValueFrom(this.trfService.createAccommodation(accommodationData))
            );
          });
        } else {
          // Domestic accommodation (single object)
          // Skip if missing required fields
          if (!data.accommodation.checkInDate || !data.accommodation.checkOutDate) {
            console.warn('Skipping accommodation with missing dates:', data.accommodation);
          } else {
            const accommodationData = {
              trf: trfId,
              accommodation_type: data.accommodation.type || '',
              check_in_date: this.formatDateForAPI(data.accommodation.checkInDate),
              check_in_time: data.accommodation.checkInTime || '',
              check_out_date: this.formatDateForAPI(data.accommodation.checkOutDate),
              check_out_time: data.accommodation.checkOutTime || '',
              location: '',
              address: '',
              place_of_stay: '',
              remarks: data.accommodation.remarks || ''
            };

            console.log('Creating accommodation (single):', accommodationData);
            promises.push(
              firstValueFrom(this.trfService.createAccommodation(accommodationData))
            );
          }
        }
      }

      // Create transport details (can be single array or nested)
      if (data.transport && data.transport.length > 0) {
        data.transport.forEach((transport: any) => {
          // Skip transport with missing required date
          if (!transport.date) {
            console.warn('Skipping transport with missing date:', transport);
            return;
          }

          const transportData = {
            trf: trfId,
            transport_date: this.formatDateForAPI(transport.date),
            day_of_week: transport.day || '',
            from_location: transport.from || transport.fromLocation || '',
            to_location: transport.to || transport.toLocation || '',
            bt_no_required: transport.btNumber || transport.btNoRequired || '',
            accommodation_type_n: transport.accommodationType || '',
            address: transport.address || '',
            remarks: transport.remarks || ''
          };

          console.log('Creating transport:', transportData);
          promises.push(
            firstValueFrom(this.trfService.createTransport(transportData))
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
          account_number: data.bankDetails.accountNumber || ''
        };

        promises.push(
          firstValueFrom(this.trfService.createBankDetail(bankData))
        );
      }

      // Create advance amount items (Overseas)
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

      // Wait for all nested resources to be created
      console.log(`Created ${promises.length} promises for nested resources`);

      Promise.all(promises)
        .then(() => {
          console.log('✓ All nested resources created successfully');
          resolve(true);
        })
        .catch((error) => {
          console.error('✗ Error creating nested resources:', error);
          console.error('Error details:', JSON.stringify(error, null, 2));
          if (error.error) {
            console.error('Validation errors:', error.error);
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
