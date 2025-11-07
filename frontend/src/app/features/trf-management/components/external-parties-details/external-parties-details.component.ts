import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';

export interface ExternalPartiesDetails {
  purpose: string;
  tripType: 'One Way' | 'Round Trip';
  externalFullName: string;
  externalOrganization: string;
  externalRefToAuthorityLetter?: string;
  externalCostCenter: string;
  itinerary: any[];
  accommodation: any[];
  transport: any[];
}

@Component({
  selector: 'app-external-parties-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './external-parties-details.component.html',
  styleUrls: ['./external-parties-details.component.scss']
})
export class ExternalPartiesDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<ExternalPartiesDetails> = {};
  @Output() formSubmit = new EventEmitter<ExternalPartiesDetails>();

  externalForm!: FormGroup;
  weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // When initialData changes (e.g., loaded from API in edit mode), rebuild the form
    if (changes['initialData'] && !changes['initialData'].firstChange && this.externalForm) {
      this.initForm();  // Rebuild form with new data
    }
  }

  private initForm(): void {
    this.externalForm = this.fb.group({
      purpose: [this.initialData.purpose || '', [Validators.required, Validators.minLength(10)]],
      tripType: [this.initialData.tripType || 'One Way', Validators.required],
      externalFullName: [this.initialData.externalFullName || '', Validators.required],
      externalOrganization: [this.initialData.externalOrganization || '', Validators.required],
      externalRefToAuthorityLetter: [this.initialData.externalRefToAuthorityLetter || ''],
      externalCostCenter: [this.initialData.externalCostCenter || '', Validators.required],
      itinerary: this.fb.array([]),
      accommodation: this.fb.array([]),
      transport: this.fb.array([])
    });

    // Watch trip type changes to manage itinerary segments
    this.externalForm.get('tripType')?.valueChanges.subscribe(tripType => {
      const itineraryArray = this.itinerary;
      if (tripType === 'One Way' && itineraryArray.length > 1) {
        // Keep only first segment for one way
        while (itineraryArray.length > 1) {
          itineraryArray.removeAt(itineraryArray.length - 1);
        }
      }
    });

    // Initialize itinerary from initialData or add one empty entry
    if (this.initialData.itinerary && this.initialData.itinerary.length > 0) {
      this.initialData.itinerary.forEach(segment => this.addItinerarySegment(segment));
    } else {
      this.addItinerarySegment();
    }

    // Initialize accommodation from initialData or add one empty entry
    if (this.initialData.accommodation && this.initialData.accommodation.length > 0) {
      this.initialData.accommodation.forEach(acc => this.addAccommodation(acc));
    } else {
      this.addAccommodation();
    }

    // Initialize transport from initialData or add one empty entry
    if (this.initialData.transport && this.initialData.transport.length > 0) {
      this.initialData.transport.forEach(trans => this.addTransport(trans));
    } else {
      this.addTransport();
    }
  }

  get itinerary(): FormArray {
    return this.externalForm.get('itinerary') as FormArray;
  }

  get accommodation(): FormArray {
    return this.externalForm.get('accommodation') as FormArray;
  }

  get transport(): FormArray {
    return this.externalForm.get('transport') as FormArray;
  }

  private createItinerarySegment(data?: any): FormGroup {
    // Auto-calculate day from departureDate if available
    let dayValue = data?.day || '';
    if (!dayValue && data?.departureDate) {
      const date = new Date(data.departureDate);
      if (!isNaN(date.getTime())) {
        dayValue = this.weekdays[date.getDay()];
      }
    }

    return this.fb.group({
      departureDate: [data?.departureDate || '', Validators.required],
      day: [dayValue],
      departureTime: [data?.departureTime || ''],
      departureLocation: [data?.departureLocation || '', Validators.required],
      arrivalDate: [data?.arrivalDate || ''],  // Optional - not displayed in UI
      arrivalTime: [data?.arrivalTime || ''],
      arrivalLocation: [data?.arrivalLocation || '', Validators.required],
      modeOfTransport: [data?.modeOfTransport || '', Validators.required],
      remarks: [data?.remarks || '']
    });
  }

  private createAccommodation(data?: any): FormGroup {
    return this.fb.group({
      fromDate: [data?.fromDate || '', Validators.required],
      toDate: [data?.toDate || '', Validators.required],
      fromLocation: [data?.fromLocation || '', Validators.required],
      toLocation: [data?.toLocation || '', Validators.required],
      accommodationType: [data?.accommodationType || '', Validators.required],
      address: [data?.address || ''],
      remarks: [data?.remarks || '']
    });
  }

  private createTransport(data?: any): FormGroup {
    return this.fb.group({
      date: [data?.date || '', Validators.required],
      fromLocation: [data?.fromLocation || '', Validators.required],
      toLocation: [data?.toLocation || '', Validators.required],
      btNoRequired: [data?.btNoRequired || ''],
      remarks: [data?.remarks || '']
    });
  }

  addItinerarySegment(data?: any): void {
    const tripType = this.externalForm.get('tripType')?.value;
    if (tripType === 'One Way' && this.itinerary.length >= 1) {
      return; // Don't allow more than 1 segment for one way
    }
    this.itinerary.push(this.createItinerarySegment(data));
  }

  onDateChange(index: number, event: any): void {
    const dateValue = event.target.value;
    if (dateValue) {
      const date = new Date(dateValue);
      if (!isNaN(date.getTime())) {
        const dayIndex = date.getDay();
        const dayName = this.weekdays[dayIndex];
        this.itinerary.at(index).get('day')?.setValue(dayName);
      }
    }
  }

  removeItinerarySegment(index: number): void {
    if (this.itinerary.length > 1) {
      this.itinerary.removeAt(index);
    }
  }

  addAccommodation(data?: any): void {
    this.accommodation.push(this.createAccommodation(data));
  }

  removeAccommodation(index: number): void {
    if (this.accommodation.length > 1) {
      this.accommodation.removeAt(index);
    }
  }

  addTransport(data?: any): void {
    this.transport.push(this.createTransport(data));
  }

  removeTransport(index: number): void {
    if (this.transport.length > 1) {
      this.transport.removeAt(index);
    }
  }

  onSubmit(): void {
    console.log('=== EXTERNAL PARTIES FORM SUBMIT ===');
    console.log('Form valid:', this.externalForm.valid);

    if (this.externalForm.valid) {
      const formValue = this.externalForm.getRawValue();
      console.log('Form value:', formValue);
      this.formSubmit.emit(formValue);
    } else {
      console.log('Form is INVALID. Errors:');
      this.logFormErrors(this.externalForm);
      this.markFormGroupTouched(this.externalForm);
    }
  }

  private logFormErrors(formGroup: FormGroup | FormArray, path: string = ''): void {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      const currentPath = path ? `${path}.${key}` : key;

      if (control instanceof FormGroup || control instanceof FormArray) {
        this.logFormErrors(control, currentPath);
      } else if (control?.invalid) {
        console.log(`  - ${currentPath}:`, control.errors);
      }
    });
  }

  // Public methods for wizard integration
  getFormData(): ExternalPartiesDetails {
    return this.externalForm.getRawValue();
  }

  isValid(): boolean {
    return this.externalForm.valid;
  }

  markAllAsTouched(): void {
    this.markFormGroupTouched(this.externalForm);
  }

  private markFormGroupTouched(formGroup: FormGroup | FormArray): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();
      if (control instanceof FormGroup || control instanceof FormArray) {
        this.markFormGroupTouched(control);
      }
    });
  }
}
