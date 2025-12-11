import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Observable, of } from 'rxjs';
import { User } from '../../../core/models/user.model';
import { AccommodationService } from '../../../core/services/accommodation.service';

@Component({
  selector: 'app-accommodation-request',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './accommodation-request.component.html',
  styleUrl: './accommodation-request.component.scss'
})
export class AccommodationRequestComponent implements OnInit {
  currentStep: number = 1;
  totalSteps: number = 2;
  accommodationForm: FormGroup = new FormGroup({});
  isSubmitting: boolean = false;
  
  // Calendar data
  calendarView: 'option1' | 'option2' = 'option1';
  currentMonth: Date = new Date();
  calendarDays: number[] = Array.from({ length: 31 }, (_, i) => i + 1);
  accommodations: any[] = [];
  rooms: any[] = [];
  
  // Available staff houses/camps
  staffHouses = [
    { id: '41', name: 'Staff House 41', location: 'Ashgabat', rooms: 4 },
    { id: '42', name: 'Staff House 42', location: 'Ashgabat', rooms: 4 }
  ];
  
  camps = [
    { id: '1', name: 'Camp 1', location: 'Kiyanly', rooms: 6 },
    { id: '2', name: 'Camp 2', location: 'Kiyanly', rooms: 8 }
  ];
  
  // Room availability data (mock)
  roomAvailability: any = {};
  
  // Form step titles
  stepTitles = [
    'Accommodation Selection',
    'Booking Confirmation'
  ];
  
  constructor(
    private fb: FormBuilder,
    private router: Router,
    private accommodationService: AccommodationService
  ) {
    this.initForm();
  }
  
  ngOnInit(): void {
    this.loadDraft();
  }
  
  // Initialize the form with all fields across all steps
  private initForm(): void {
    this.accommodationForm = this.fb.group({
      // Step 1: Accommodation Selection
      accommodationType: ['ashgabat', Validators.required], // 'ashgabat' or 'kiyanly'
      checkInDate: ['', Validators.required],
      checkOutDate: ['', Validators.required],
      gender: ['male', Validators.required], // For gender-segregated rooms
      selectedAccommodation: ['', Validators.required], // ID of selected staff house or camp
      selectedRoom: ['', Validators.required], // ID of selected room
      
      // Step 2: Booking Confirmation
      relatedTravelRequest: [''], // TRF reference number
      specialRequirements: [''],
      reason: ['', Validators.required]
    });
    
    // Load mock room availability data
    this.loadRoomAvailability();
    
    // Subscribe to form changes to update available rooms
    this.accommodationForm.get('accommodationType')?.valueChanges.subscribe(type => {
      this.updateAvailableAccommodations(type);
    });
    
    this.accommodationForm.get('selectedAccommodation')?.valueChanges.subscribe(accommodationId => {
      if (accommodationId) {
        this.updateAvailableRooms(accommodationId);
      }
    });
    
    this.accommodationForm.get('gender')?.valueChanges.subscribe(() => {
      const accommodationId = this.accommodationForm.get('selectedAccommodation')?.value;
      if (accommodationId) {
        this.updateAvailableRooms(accommodationId);
      }
    });
  }
  
  // Load mock room availability data
  private loadRoomAvailability(): void {
    // This would normally come from an API
    this.roomAvailability = {
      // Staff House 41
      '41': {
        'room1': { available: [1, 2, 3, 5, 6, 7, 8, 15, 16, 17, 25, 26, 27, 28], gender: 'male' },
        'room2': { available: [1, 2, 3, 8, 9, 10, 15, 16, 17, 18, 25, 26, 27], gender: 'male' },
        'room3': { available: [5, 6, 7, 8, 9, 10, 18, 19, 20, 21, 22], gender: 'female' },
        'room4': { available: [1, 2, 3, 10, 11, 12, 13, 14, 15, 22, 23, 24, 25], gender: 'female' }
      },
      // Staff House 42
      '42': {
        'room1': { available: [5, 6, 7, 8, 15, 16, 17, 18, 25, 26, 27, 28], gender: 'male' },
        'room2': { available: [1, 2, 3, 10, 11, 12, 20, 21, 22, 23], gender: 'male' },
        'room3': { available: [5, 6, 7, 15, 16, 17, 18, 25, 26, 27], gender: 'female' },
        'room4': { available: [1, 2, 3, 8, 9, 10, 20, 21, 22], gender: 'female' }
      },
      // Camp 1
      '1': {
        'room1': { available: [1, 2, 3, 8, 9, 10, 15, 16, 17], gender: 'male' },
        'room2': { available: [5, 6, 7, 12, 13, 14, 19, 20, 21], gender: 'male' },
        'room3': { available: [3, 4, 5, 10, 11, 12, 17, 18, 19], gender: 'female' }
      },
      // Camp 2
      '2': {
        'room1': { available: [2, 3, 4, 9, 10, 11, 16, 17, 18], gender: 'male' },
        'room2': { available: [6, 7, 8, 13, 14, 15, 20, 21, 22], gender: 'male' },
        'room3': { available: [1, 2, 3, 8, 9, 10, 15, 16, 17], gender: 'female' }
      }
    };
  }
  
  // Update available accommodations based on selected type
  updateAvailableAccommodations(type: string): void {
    if (type === 'ashgabat') {
      this.accommodations = this.staffHouses;
    } else if (type === 'kiyanly') {
      this.accommodations = this.camps;
    } else {
      this.accommodations = [];
    }
    
    // Reset selected accommodation and room
    this.accommodationForm.patchValue({
      selectedAccommodation: '',
      selectedRoom: ''
    });
  }
  
  // Update available rooms based on selected accommodation and gender
  updateAvailableRooms(accommodationId: string): void {
    const gender = this.accommodationForm.get('gender')?.value;
    const accommodationRooms = this.roomAvailability[accommodationId];
    
    if (!accommodationRooms) {
      this.rooms = [];
      return;
    }
    
    this.rooms = Object.keys(accommodationRooms)
      .filter(roomId => accommodationRooms[roomId].gender === gender)
      .map(roomId => ({
        id: roomId,
        name: `Room ${roomId.replace('room', '')}`,
        gender: accommodationRooms[roomId].gender,
        availableDays: accommodationRooms[roomId].available
      }));
      
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
  
  // Check if a room is available for a specific date
  isRoomAvailable(roomId: string, accommodationId: string, day: number): boolean {
    const room = this.roomAvailability[accommodationId]?.[roomId];
    return room ? room.available.includes(day) : false;
  }
  
  // Get room availability class for calendar cell
  getRoomAvailabilityClass(roomId: string, accommodationId: string, day: number): string {
    return this.isRoomAvailable(roomId, accommodationId, day) ? 'available' : 'booked';
  }
  
  // Check if selected dates are available for the selected room
  areSelectedDatesAvailable(): boolean {
    const selectedRoom = this.accommodationForm.get('selectedRoom')?.value;
    const selectedAccommodation = this.accommodationForm.get('selectedAccommodation')?.value;
    const checkInDate = this.accommodationForm.get('checkInDate')?.value;
    const checkOutDate = this.accommodationForm.get('checkOutDate')?.value;
    
    if (!selectedRoom || !selectedAccommodation || !checkInDate || !checkOutDate) {
      return false;
    }
    
    const startDay = new Date(checkInDate).getDate();
    const endDay = new Date(checkOutDate).getDate();
    
    const room = this.roomAvailability[selectedAccommodation]?.[selectedRoom];
    if (!room) return false;
    
    // Check if all days between start and end are available
    for (let day = startDay; day <= endDay; day++) {
      if (!room.available.includes(day)) {
        return false;
      }
    }
    
    return true;
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
      priority: 'medium',
      accommodationType: 'hotel',
      numberOfGuests: 1,
      budgetCurrency: 'USD'
    });
  }
  
  // Form submission
  submitRequest(): void {
    if (this.accommodationForm.valid && this.areSelectedDatesAvailable()) {
      this.isSubmitting = true;
      
      // Submit the form data to the accommodation service
      this.accommodationService.submitAccommodationRequest(this.accommodationForm.value)
        .subscribe(response => {
          if (response.success) {
            this.clearDraft();
            this.isSubmitting = false;
            this.router.navigate(['/requests/success'], { 
              state: { 
                message: 'Accommodation request submitted successfully!',
                reference: response.reference
              } 
            });
          }
        });
    } else {
      // Mark all fields as touched to show validation errors
      this.markFormGroupTouched(this.accommodationForm);
    }
  }
  
  // Helper to mark all controls as touched
  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();
      
      if ((control as FormGroup).controls) {
        this.markFormGroupTouched(control as FormGroup);
      }
    });
  }
  
  // Get progress percentage for the progress bar
  get progressPercentage(): number {
    return (this.currentStep / this.totalSteps) * 100;
  }
  
  // Helper method to get accommodation name for the template
  getAccommodationName(): string {
    const accommodationType = this.accommodationForm.get('accommodationType')?.value;
    const accommodationId = this.accommodationForm.get('selectedAccommodation')?.value;
    
    if (!accommodationType || !accommodationId) {
      return '';
    }
    
    const accommodations = accommodationType === 'ashgabat' ? this.staffHouses : this.camps;
    const accommodation = accommodations.find(a => a.id === accommodationId);
    
    return accommodation ? accommodation.name : '';
  }
  
  // Helper method to get room number for the template
  getRoomNumber(): string {
    const roomId = this.accommodationForm.get('selectedRoom')?.value;
    if (!roomId) {
      return '';
    }
    
    // Extract the room number from the ID (e.g., 'room1' -> '1')
    return roomId.replace('room', '');
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
}
