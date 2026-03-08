import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { FormUtilsService } from '../../../core/utils/form-utils.service';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { AccommodationService, AccommodationStaffHouse, AccommodationRoom } from '../../accommodation/services/accommodation.service';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-accommodation-request',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LoadingSpinnerComponent],
  templateUrl: './accommodation-request.component.html',
  styleUrl: './accommodation-request.component.scss'
})
export class AccommodationRequestComponent implements OnInit {
  currentStep: number = 1;
  totalSteps: number = 2;
  accommodationForm: FormGroup = new FormGroup({});
  isSubmitting: boolean = false;
  isLoading: boolean = false;

  // Calendar data
  calendarView: 'option1' | 'option2' = 'option1';
  currentMonth: Date = new Date();
  calendarDays: number[] = Array.from({ length: 31 }, (_, i) => i + 1);
  accommodations: AccommodationStaffHouse[] = [];
  rooms: AccommodationRoom[] = [];

  // All staff houses loaded from API
  allStaffHouses: AccommodationStaffHouse[] = [];
  allRooms: AccommodationRoom[] = [];

  // Form step titles
  stepTitles = [
    'Accommodation Selection',
    'Booking Confirmation'
  ];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private accommodationService: AccommodationService,
    private authService: AuthService,
    private toastService: ToastService,
    private formUtils: FormUtilsService
  ) {
    this.initForm();
  }

  ngOnInit(): void {
    this.loadInitialData();
    this.loadDraft();
  }

  // Load staff houses and rooms from API
  private loadInitialData(): void {
    this.isLoading = true;

    forkJoin({
      staffHouses: this.accommodationService.getAllStaffHouses(),
      rooms: this.accommodationService.getAllRooms()
    }).subscribe({
      next: ({ staffHouses, rooms }) => {
        this.allStaffHouses = staffHouses;
        this.allRooms = rooms;
        this.isLoading = false;

        // Initialize accommodations based on default type
        const defaultType = this.accommodationForm.get('accommodationType')?.value;
        if (defaultType) {
          this.updateAvailableAccommodations(defaultType);
        }
      },
      error: (err) => {
        console.error('Error loading accommodation data:', err);
        this.toastService.error('Failed to load accommodation options');
        this.isLoading = false;
      }
    });
  }
  
  // Initialize the form with all fields across all steps
  private initForm(): void {
    this.accommodationForm = this.fb.group({
      // Step 1: Accommodation Selection
      accommodationType: ['Ashgabat', Validators.required], // Location-based selection
      checkInDate: ['', Validators.required],
      checkOutDate: ['', Validators.required],
      gender: ['male', Validators.required], // For gender-segregated rooms
      selectedAccommodation: ['', Validators.required], // ID of selected staff house
      selectedRoom: ['', Validators.required], // ID of selected room

      // Step 2: Booking Confirmation
      relatedTravelRequest: [''], // TRF reference number
      specialRequirements: [''],
      reason: ['', Validators.required]
    });

    // Subscribe to form changes to update available options
    this.accommodationForm.get('accommodationType')?.valueChanges.subscribe(type => {
      this.updateAvailableAccommodations(type);
    });

    this.accommodationForm.get('selectedAccommodation')?.valueChanges.subscribe(accommodationId => {
      if (accommodationId) {
        this.updateAvailableRooms(Number(accommodationId));
      }
    });
  }

  // Update available accommodations based on selected location
  updateAvailableAccommodations(location: string): void {
    // Filter staff houses by location
    this.accommodations = this.allStaffHouses.filter(
      house => house.location?.toLowerCase() === location?.toLowerCase()
    );

    // Reset selected accommodation and room
    this.accommodationForm.patchValue({
      selectedAccommodation: '',
      selectedRoom: ''
    });
    this.rooms = [];
  }

  // Update available rooms based on selected staff house
  updateAvailableRooms(staffHouseId: number): void {
    // Filter rooms by staff house and available status
    this.rooms = this.allRooms.filter(
      room => room.staff_house === staffHouseId && room.status === 'Available'
    );

    // Reset selected room
    this.accommodationForm.patchValue({
      selectedRoom: ''
    });
  }
  
  // Navigation methods
  nextStep(): void {
    if (this.currentStep < this.totalSteps) {
      this.currentStep++;
      this.autosaveDraft();
    }
  }
  
  previousStep(): void {
    if (this.currentStep > 1) {
      this.currentStep--;
    }
  }
  
  // Check if current step is valid
  isCurrentStepValid(): boolean {
    const fieldsToValidate = this.getFieldsForCurrentStep();
    return fieldsToValidate.every(field => {
      const control = this.accommodationForm.get(field);
      return control ? control.valid : true;
    });
  }
  
  // Get fields that belong to current step
  private getFieldsForCurrentStep(): string[] {
    switch(this.currentStep) {
      case 1:
        return ['accommodationType', 'checkInDate', 'checkOutDate', 'gender', 'selectedAccommodation', 'selectedRoom'];
      case 2:
        return ['relatedTravelRequest', 'reason'];
      default:
        return [];
    }
  }
  
  // Toggle calendar view between option 1 and option 2
  toggleCalendarView(): void {
    this.calendarView = this.calendarView === 'option1' ? 'option2' : 'option1';
  }

  // Check if selected dates and room are valid (basic validation)
  areSelectedDatesAvailable(): boolean {
    const selectedRoom = this.accommodationForm.get('selectedRoom')?.value;
    const selectedAccommodation = this.accommodationForm.get('selectedAccommodation')?.value;
    const checkInDate = this.accommodationForm.get('checkInDate')?.value;
    const checkOutDate = this.accommodationForm.get('checkOutDate')?.value;

    if (!selectedRoom || !selectedAccommodation || !checkInDate || !checkOutDate) {
      return false;
    }

    // Check that checkout is on or after checkin (same-day checkout allowed)
    const checkIn = new Date(checkInDate);
    const checkOut = new Date(checkOutDate);
    return checkOut >= checkIn;
  }
  
  // Draft saving and loading
  autosaveDraft(): void {
    const draftData = this.accommodationForm.value;
    localStorage.setItem('draft_accommodation_request', JSON.stringify({
      formData: draftData,
      lastStep: this.currentStep,
      timestamp: new Date().toISOString()
    }));
  }
  
  loadDraft(): void {
    const savedDraft = localStorage.getItem('draft_accommodation_request');
    if (savedDraft) {
      try {
        const draftData = JSON.parse(savedDraft);
        this.accommodationForm.patchValue(draftData.formData);
        this.currentStep = draftData.lastStep || 1;
      } catch (error) {
        console.error('Error loading draft:', error);
      }
    }
  }
  
  clearDraft(): void {
    localStorage.removeItem('draft_accommodation_request');
    this.accommodationForm.reset();
    this.currentStep = 1;

    // Reset default values
    this.accommodationForm.patchValue({
      accommodationType: 'Ashgabat',
      gender: 'male'
    });
  }

  // Form submission
  submitRequest(): void {
    if (this.accommodationForm.valid && this.areSelectedDatesAvailable()) {
      this.isSubmitting = true;

      const currentUser = this.authService.getCurrentUser();
      const formValue = this.accommodationForm.value;

      // Build the request payload for the API
      // Extract department name if it's an object
      const department = this.extractDepartmentName(currentUser?.department);
      const requestData = {
        requestor_name: currentUser?.name || '',
        staff_id: currentUser?.staff_id || '',
        department: department,
        email: currentUser?.email || '',
        additional_comments: formValue.specialRequirements || '',
        additional_data: {
          location: formValue.accommodationType,
          requested_check_in_date: formValue.checkInDate,
          requested_check_out_date: formValue.checkOutDate,
          gender: formValue.gender,
          reason: formValue.reason,
          related_travel_request: formValue.relatedTravelRequest || null,
          accommodations: [{
            staff_house_id: Number(formValue.selectedAccommodation),
            room_id: Number(formValue.selectedRoom),
            check_in_date: formValue.checkInDate,
            check_out_date: formValue.checkOutDate,
            location: formValue.accommodationType
          }]
        }
      };

      this.accommodationService.createRequest(requestData).subscribe({
        next: (response) => {
          this.clearDraft();
          this.isSubmitting = false;
          this.toastService.success('Accommodation request submitted successfully!');
          this.router.navigate(['/requests/success'], {
            state: {
              message: 'Accommodation request submitted successfully!',
              reference: response.request_number || `ACC-${response.id}`
            }
          });
        },
        error: (err) => {
          console.error('Error submitting accommodation request:', err);
          this.toastService.error('Failed to submit request: ' + (err.error?.detail || err.message));
          this.isSubmitting = false;
        }
      });
    } else {
      // Mark all fields as touched to show validation errors
      this.formUtils.markFormGroupTouched(this.accommodationForm);
    }
  }

  // Get progress percentage for the progress bar
  get progressPercentage(): number {
    return (this.currentStep / this.totalSteps) * 100;
  }

  // Helper method to get accommodation name for the template
  getAccommodationName(): string {
    const accommodationId = this.accommodationForm.get('selectedAccommodation')?.value;

    if (!accommodationId) {
      return '';
    }

    const accommodation = this.allStaffHouses.find(h => h.id === Number(accommodationId));
    return accommodation ? accommodation.name : '';
  }
  
  // Helper method to get room name for the template
  getRoomNumber(): string {
    const roomId = this.accommodationForm.get('selectedRoom')?.value;
    if (!roomId) {
      return '';
    }

    const room = this.allRooms.find(r => r.id === Number(roomId));
    return room ? room.name : '';
  }
  
  // Helper method to format dates for the template
  getFormattedDate(fieldName: string): string {
    const date = this.accommodationForm.get(fieldName)?.value;
    if (!date) {
      return '';
    }
    
    // Format the date as medium date (e.g., 'Jun 15, 2025')
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }
  
  // Helper method to display gender in a user-friendly format
  getGenderDisplay(): string {
    const gender = this.accommodationForm.get('gender')?.value;
    return gender === 'male' ? 'Male' : 'Female';
  }

  private extractDepartmentName(department: any): string {
    if (!department) {
      return '';
    }
    if (typeof department === 'string') {
      return department;
    }
    return department.name || '';
  }
}
