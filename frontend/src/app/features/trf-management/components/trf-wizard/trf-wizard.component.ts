import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { TrfStepperComponent } from '../trf-stepper/trf-stepper.component';
import { RequestorInformationComponent } from '../requestor-information/requestor-information.component';
import { DomesticTravelDetailsComponent } from '../domestic-travel-details/domestic-travel-details.component';
import { OverseasTravelDetailsComponent } from '../overseas-travel-details/overseas-travel-details.component';
import { HomeLeaveDetailsComponent } from '../home-leave-details/home-leave-details.component';
import { ExternalPartiesDetailsComponent } from '../external-parties-details/external-parties-details.component';
import { TrfService } from '../../services/trf.service';

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
    ExternalPartiesDetailsComponent
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

  currentStep: number = 1;
  totalSteps: number = 3; // Requestor Info + Travel Type Selection + Travel Details
  stepLabels: string[] = ['Requestor Information', 'Travel Type', 'Travel Details'];
  completedSteps: boolean[] = [false, false, false];
  isSubmitting: boolean = false;
  submitError: string = '';

  // Travel type selection
  selectedTravelType: 'Domestic' | 'Overseas' | 'Home Leave' | 'External Parties' | null = null;

  // Store form data from each step
  requestorData: any = null;
  domesticTravelData: any = null;
  overseasTravelData: any = null;
  homeLeaveData: any = null;
  externalPartiesData: any = null;

  constructor(
    private trfService: TrfService,
    private router: Router
  ) {}

  ngOnInit(): void {
    console.log('TRF Wizard initialized');
    console.log('Current step:', this.currentStep);
    console.log('Total steps:', this.totalSteps);
    console.log('Selected travel type:', this.selectedTravelType);
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
      // Validate travel type selection
      if (!this.selectedTravelType) {
        this.submitError = 'Please select a travel type';
        return false;
      }
    } else if (this.currentStep === 3) {
      // Validate travel details based on selected type
      return this.validateTravelDetailsForm();
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
   * Handle travel type selection
   */
  onTravelTypeSelect(type: 'Domestic' | 'Overseas' | 'Home Leave' | 'External Parties'): void {
    console.log('Travel type selected:', type);
    this.selectedTravelType = type;
    this.submitError = '';
    console.log('Selected travel type now:', this.selectedTravelType);
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
      // Travel type selection - no data to save
    } else if (this.currentStep === 3) {
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

    // Validate travel type selection
    if (!this.selectedTravelType) {
      if (isValid) {
        this.currentStep = 2;
        this.submitError = 'Please select a travel type';
      }
      isValid = false;
    }

    // Validate travel details form based on selected type
    if (!this.validateTravelDetailsForm()) {
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

    // Step 1: Create main TRF
    this.trfService.createTravelRequest(combinedData.mainTrf).subscribe({
      next: (createdTrf: any) => {
        console.log('TRF created successfully:', createdTrf);

        // Step 2: Create nested resources (itinerary, meals, accommodation, transport)
        this.createNestedResources(createdTrf.id, combinedData).subscribe({
          next: () => {
            this.isSubmitting = false;

            // Show success message and navigate
            alert(isDraft ? 'TRF saved as draft successfully!' : 'TRF submitted successfully!');
            this.router.navigate(['/trf']);
          },
          error: (error: any) => {
            this.isSubmitting = false;
            this.submitError = 'Error creating nested resources: ' + (error.message || 'Unknown error');
            console.error('Error creating nested resources:', error);
          }
        });
      },
      error: (error: any) => {
        this.isSubmitting = false;
        this.submitError = 'Error creating TRF: ' + (error.error?.message || error.message || 'Unknown error');
        console.error('Error creating TRF:', error);
      }
    });
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
    mainTrf.purpose = this.domesticTravelData?.purpose?.purposeOfTravel || '';
    mainTrf.additional_comments = this.domesticTravelData?.purpose?.additionalComments || '';

    return {
      mainTrf,
      itinerarySegments: this.domesticTravelData?.itinerary?.segments || [],
      mealSelections: this.domesticTravelData?.meals?.selections || [],
      accommodation: this.domesticTravelData?.accommodation || null,
      transport: this.domesticTravelData?.transport?.details || [],
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

    // Add external party specific fields
    mainTrf.external_party_name = this.externalPartiesData?.externalFullName || '';
    mainTrf.external_party_organization = this.externalPartiesData?.externalOrganization || '';
    mainTrf.external_ref_to_authority_letter = this.externalPartiesData?.externalRefToAuthorityLetter || '';
    mainTrf.external_cost_center = this.externalPartiesData?.externalCostCenter || '';

    return {
      mainTrf,
      itinerarySegments: [],
      mealSelections: [],
      accommodation: this.externalPartiesData?.accommodation || [],
      transport: this.externalPartiesData?.transport || [],
      passportDetails: null,
      bankDetails: null,
      advanceAmounts: []
    };
  }

  /**
   * Create nested resources (itinerary, meals, passport, bank details, etc.)
   */
  private createNestedResources(trfId: number, data: any): any {
    return new Promise((resolve, reject) => {
      const promises: Promise<any>[] = [];

      // Create itinerary segments
      if (data.itinerarySegments && data.itinerarySegments.length > 0) {
        data.itinerarySegments.forEach((segment: any) => {
          const itineraryData = {
            trf: trfId,
            segment_date: segment.date,
            day_of_week: segment.day || '',
            from_location: segment.from,
            to_location: segment.to,
            departure_time: segment.departureTime || segment.etd || '',
            arrival_time: segment.arrivalTime || segment.eta || '',
            flight_number: segment.flightNumber || '',
            remarks: segment.remarks || ''
          };

          promises.push(
            this.trfService.createItinerarySegment(itineraryData).toPromise()
          );
        });
      }

      // Create meal selections (Domestic only)
      if (data.mealSelections && data.mealSelections.length > 0) {
        data.mealSelections.forEach((meal: any) => {
          const mealData = {
            trf: trfId,
            meal_date: meal.date,
            breakfast: meal.breakfast || false,
            lunch: meal.lunch || false,
            dinner: meal.dinner || false,
            supper: meal.supper || false,
            refreshment: meal.refreshment || false
          };

          promises.push(
            this.trfService.createDailyMeal(mealData).toPromise()
          );
        });
      }

      // Create accommodation (can be single object or array)
      if (data.accommodation) {
        if (Array.isArray(data.accommodation)) {
          // External Parties accommodation (array)
          data.accommodation.forEach((acc: any) => {
            const accommodationData = {
              trf: trfId,
              accommodation_type: acc.accommodationType || '',
              check_in_date: acc.fromDate || '',
              check_in_time: '',
              check_out_date: acc.toDate || '',
              check_out_time: '',
              from_location: acc.fromLocation || '',
              to_location: acc.toLocation || '',
              address: acc.address || '',
              remarks: acc.remarks || ''
            };

            promises.push(
              this.trfService.createAccommodation(accommodationData).toPromise()
            );
          });
        } else {
          // Domestic accommodation (single object)
          const accommodationData = {
            trf: trfId,
            accommodation_type: data.accommodation.type || '',
            check_in_date: data.accommodation.checkInDate || '',
            check_in_time: data.accommodation.checkInTime || '',
            check_out_date: data.accommodation.checkOutDate || '',
            check_out_time: data.accommodation.checkOutTime || '',
            from_location: '',
            to_location: '',
            address: '',
            remarks: data.accommodation.remarks || ''
          };

          promises.push(
            this.trfService.createAccommodation(accommodationData).toPromise()
          );
        }
      }

      // Create transport details (can be single array or nested)
      if (data.transport && data.transport.length > 0) {
        data.transport.forEach((transport: any) => {
          const transportData = {
            trf: trfId,
            transport_date: transport.date || '',
            day_of_week: transport.day || '',
            from_location: transport.from || transport.fromLocation || '',
            to_location: transport.to || transport.toLocation || '',
            bt_no_required: transport.btNumber || transport.btNoRequired || '',
            accommodation_type_n: transport.accommodationType || '',
            address: transport.address || '',
            remarks: transport.remarks || ''
          };

          promises.push(
            this.trfService.createTransport(transportData).toPromise()
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
            this.trfService.createPassportDetail(passportData).toPromise()
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
          this.trfService.createBankDetail(bankData).toPromise()
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
            this.trfService.createAdvanceAmountItem(advanceData).toPromise()
          );
        });
      }

      // Wait for all nested resources to be created
      Promise.all(promises)
        .then(() => resolve(true))
        .catch((error) => reject(error));
    });
  }

  /**
   * Handle cancel
   */
  onCancel(): void {
    if (confirm('Are you sure you want to cancel? All unsaved data will be lost.')) {
      this.router.navigate(['/trf']);
    }
  }
}
