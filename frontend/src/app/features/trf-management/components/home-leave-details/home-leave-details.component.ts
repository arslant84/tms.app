import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';

export interface PassportDetails {
  fullName: string;
  passportNumber: string;
  nationality: string;
  dateOfBirth: string;
  placeOfBirth?: string;
  passportIssueDate: string;
  passportExpiryDate: string;
}

export interface HomeLeaveDetails {
  purpose: string;
  tripType: 'One Way' | 'Round Trip';
  itinerary: any[];
  passportDetails: PassportDetails;
  advanceBankDetails?: any;
}

@Component({
  selector: 'app-home-leave-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './home-leave-details.component.html',
  styleUrls: ['./home-leave-details.component.scss']
})
export class HomeLeaveDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<HomeLeaveDetails> = {};
  @Output() formSubmit = new EventEmitter<HomeLeaveDetails>();

  homeLeaveForm!: FormGroup;
  weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // When initialData changes (e.g., loaded from API in edit mode), rebuild the form
    if (changes['initialData'] && !changes['initialData'].firstChange && this.homeLeaveForm) {
      this.initForm();  // Rebuild form with new data
    }
  }

  private initForm(): void {
    this.homeLeaveForm = this.fb.group({
      purpose: [this.initialData.purpose || '', [Validators.required, Validators.minLength(10)]],
      tripType: [this.initialData.tripType || 'Round Trip', Validators.required],
      itinerary: this.fb.array([]),
      passportDetails: this.fb.group({
        fullName: ['', Validators.required],
        passportNumber: ['', Validators.required],
        nationality: ['', Validators.required],
        dateOfBirth: ['', Validators.required],
        placeOfBirth: [''],
        passportIssueDate: ['', Validators.required],
        passportExpiryDate: ['', Validators.required]
      }),
      advanceBankDetails: this.fb.group({
        bankName: [''],
        accountNumber: ['']
      })
    });

    // Watch trip type changes to manage itinerary segments
    this.homeLeaveForm.get('tripType')?.valueChanges.subscribe(tripType => {
      const itineraryArray = this.itinerary;
      if (tripType === 'One Way' && itineraryArray.length > 1) {
        // Keep only first segment for one way
        while (itineraryArray.length > 1) {
          itineraryArray.removeAt(itineraryArray.length - 1);
        }
      }
    });

    // Initialize with one itinerary segment
    if (this.initialData.itinerary && this.initialData.itinerary.length > 0) {
      this.initialData.itinerary.forEach(segment => this.addItinerarySegment(segment));
    } else {
      this.addItinerarySegment();
    }

    // Set passport details if provided
    if (this.initialData.passportDetails) {
      this.homeLeaveForm.get('passportDetails')?.patchValue({
        fullName: this.initialData.passportDetails.fullName || '',
        passportNumber: this.initialData.passportDetails.passportNumber || '',
        nationality: this.initialData.passportDetails.nationality || '',
        dateOfBirth: this.initialData.passportDetails.dateOfBirth || '',
        placeOfBirth: this.initialData.passportDetails.placeOfBirth || '',
        passportIssueDate: this.initialData.passportDetails.passportIssueDate || '',
        passportExpiryDate: this.initialData.passportDetails.passportExpiryDate || ''
      });
    }

    // Set bank details if provided
    if (this.initialData.advanceBankDetails) {
      this.homeLeaveForm.get('advanceBankDetails')?.patchValue({
        bankName: this.initialData.advanceBankDetails.bankName || '',
        accountNumber: this.initialData.advanceBankDetails.accountNumber || ''
      });
    }
  }

  get itinerary(): FormArray {
    return this.homeLeaveForm.get('itinerary') as FormArray;
  }

  private createItinerarySegment(data?: any): FormGroup {
    return this.fb.group({
      date: [data?.date || '', Validators.required],
      day: [data?.day || ''],
      from: [data?.from || '', Validators.required],
      to: [data?.to || '', Validators.required],
      flightNumber: [data?.flightNumber || ''],
      remarks: [data?.remarks || '']
    });
  }

  addItinerarySegment(data?: any): void {
    const tripType = this.homeLeaveForm.get('tripType')?.value;
    if (tripType === 'One Way' && this.itinerary.length >= 1) {
      return; // Don't allow more than 1 segment for one way
    }
    this.itinerary.push(this.createItinerarySegment(data));
  }

  onDateChange(index: number, event: any): void {
    const date = new Date(event.target.value);
    const dayIndex = date.getDay();
    const dayName = this.weekdays[dayIndex];
    this.itinerary.at(index).get('day')?.setValue(dayName);
  }

  removeItinerarySegment(index: number): void {
    if (this.itinerary.length > 1) {
      this.itinerary.removeAt(index);
    }
  }

  onSubmit(): void {
    if (this.homeLeaveForm.valid) {
      const formValue = this.homeLeaveForm.getRawValue();
      this.formSubmit.emit(formValue);
    } else {
      this.markFormGroupTouched(this.homeLeaveForm);
    }
  }

  // Public methods for wizard integration
  getFormData(): HomeLeaveDetails {
    return this.homeLeaveForm.getRawValue();
  }

  isValid(): boolean {
    return this.homeLeaveForm.valid;
  }

  markAllAsTouched(): void {
    this.markFormGroupTouched(this.homeLeaveForm);
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
