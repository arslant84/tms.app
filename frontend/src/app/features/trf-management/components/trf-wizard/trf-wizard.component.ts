import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { TrfStepperComponent } from '../trf-stepper/trf-stepper.component';
import { RequestorInformationComponent } from '../requestor-information/requestor-information.component';
import { DomesticTravelDetailsComponent } from '../domestic-travel-details/domestic-travel-details.component';
import { TrfService } from '../../services/trf.service';

@Component({
  selector: 'app-trf-wizard',
  standalone: true,
  imports: [
    CommonModule,
    TrfStepperComponent,
    RequestorInformationComponent,
    DomesticTravelDetailsComponent
  ],
  templateUrl: './trf-wizard.component.html',
  styleUrls: ['./trf-wizard.component.scss']
})
export class TrfWizardComponent implements OnInit {
  @ViewChild(RequestorInformationComponent) requestorForm!: RequestorInformationComponent;
  @ViewChild(DomesticTravelDetailsComponent) domesticTravelForm!: DomesticTravelDetailsComponent;

  currentStep: number = 1;
  totalSteps: number = 2; // For now: Requestor Info + Domestic Travel
  stepLabels: string[] = ['Requestor Information', 'Travel Details'];
  completedSteps: boolean[] = [false, false];
  isSubmitting: boolean = false;
  submitError: string = '';

  // Store form data from each step
  requestorData: any = null;
  domesticTravelData: any = null;

  constructor(
    private trfService: TrfService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Initialization logic
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
      // Validate domestic travel details
      if (this.domesticTravelForm && !this.domesticTravelForm.isValid()) {
        this.domesticTravelForm.markAllAsTouched();
        return false;
      }
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
    } else if (this.currentStep === 2 && this.domesticTravelForm) {
      this.domesticTravelData = this.domesticTravelForm.getFormData();
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

    // Validate domestic travel form
    if (this.domesticTravelForm && !this.domesticTravelForm.isValid()) {
      this.domesticTravelForm.markAllAsTouched();
      if (isValid) {
        this.currentStep = 2;
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
      position: this.requestorData.position,
      cost_center: this.requestorData.costCenter,
      tel_email: this.requestorData.telephone,
      email: this.requestorData.email,
      travel_type: 'Domestic',
      purpose: this.domesticTravelData?.purpose?.purposeOfTravel || '',
      status: isDraft ? 'Draft' : 'Pending Department Focal',
      estimated_cost: 0 // Calculate from nested data if needed
    };

    return {
      mainTrf,
      itinerarySegments: this.domesticTravelData?.itinerary?.segments || [],
      mealSelections: this.domesticTravelData?.meals?.selections || [],
      accommodation: this.domesticTravelData?.accommodation || null,
      transport: this.domesticTravelData?.transport?.details || []
    };
  }

  /**
   * Create nested resources (itinerary, meals, etc.)
   */
  private createNestedResources(trfId: number, data: any): any {
    // This will be replaced with actual API calls
    // For now, return a mock observable
    return new Promise((resolve, reject) => {
      // Simulate API calls
      const promises: Promise<any>[] = [];

      // Create itinerary segments
      if (data.itinerarySegments && data.itinerarySegments.length > 0) {
        data.itinerarySegments.forEach((segment: any) => {
          const itineraryData = {
            trf: trfId,
            segment_date: segment.date,
            day_of_week: segment.day,
            from_location: segment.from,
            to_location: segment.to,
            departure_time: segment.departureTime,
            arrival_time: segment.arrivalTime,
            flight_number: segment.flightNumber,
            remarks: segment.remarks
          };

          promises.push(
            this.trfService.createItinerarySegment(itineraryData).toPromise()
          );
        });
      }

      // Create meal selections
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

      // Create accommodation
      if (data.accommodation) {
        const accommodationData = {
          trf: trfId,
          accommodation_type: data.accommodation.type,
          check_in_date: data.accommodation.checkInDate,
          check_in_time: data.accommodation.checkInTime,
          check_out_date: data.accommodation.checkOutDate,
          check_out_time: data.accommodation.checkOutTime,
          remarks: data.accommodation.remarks
        };

        promises.push(
          this.trfService.createAccommodation(accommodationData).toPromise()
        );
      }

      // Create transport details
      if (data.transport && data.transport.length > 0) {
        data.transport.forEach((transport: any) => {
          const transportData = {
            trf: trfId,
            transport_date: transport.date,
            day_of_week: transport.day,
            from_location: transport.from,
            to_location: transport.to,
            bt_no_required: transport.btNumber,
            accommodation_type_n: transport.accommodationType,
            address: transport.address,
            remarks: transport.remarks
          };

          promises.push(
            this.trfService.createTransport(transportData).toPromise()
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
