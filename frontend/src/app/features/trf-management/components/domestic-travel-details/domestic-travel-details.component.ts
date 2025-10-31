import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

export interface ItinerarySegment {
  date: Date | null;
  day: string;
  from: string;
  to: string;
  etd: string;
  eta: string;
  flightNumber: string;
  remarks?: string;
}

export interface DailyMealSelection {
  date: Date | string;
  breakfast: boolean;
  lunch: boolean;
  dinner: boolean;
  supper: boolean;
  refreshment: boolean;
}

export interface MealProvisionDetails {
  dailySelections: DailyMealSelection[];
}

export type AccommodationType = 'Hotel/Otels' | 'Staff House/PKC Kampung/Kinyahli camp' | 'Other';

export interface AccommodationDetail {
  accommodationType: AccommodationType;
  otherTypeDescription?: string;
  checkInDate: Date | null;
  checkInTime: string;
  checkOutDate: Date | null;
  checkOutTime: string;
  remarks?: string;
}

export interface CompanyTransportDetail {
  date: Date | null;
  day: string;
  from: string;
  to: string;
  etd: string;
  accommodationType: string;
  address: string;
  remarks?: string;
}

export interface DomesticTravelSpecificDetails {
  purposeOfTravel: string;
  tripType: 'One Way' | 'Round Trip';
  itinerary: ItinerarySegment[];
  mealProvisions: MealProvisionDetails;
  accommodation: AccommodationDetail;
  companyTransportation: CompanyTransportDetail[];
}

@Component({
  selector: 'app-domestic-travel-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './domestic-travel-details.component.html',
  styleUrls: ['./domestic-travel-details.component.scss']
})
export class DomesticTravelDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<DomesticTravelSpecificDetails> = {};
  @Output() formSubmit = new EventEmitter<DomesticTravelSpecificDetails>();
  @Output() backClick = new EventEmitter<void>();

  travelForm!: FormGroup;
  timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
  accommodationTypes: AccommodationType[] = ['Hotel/Otels', 'Staff House/PKC Kampung/Kinyahli camp', 'Other'];
  weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  dailyMealDates: Date[] = [];
  mealSummary = {
    breakfast: 0,
    lunch: 0,
    dinner: 0,
    supper: 0,
    refreshment: 0
  };

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // When initialData changes (e.g., loaded from API in edit mode), rebuild the form
    if (changes['initialData'] && !changes['initialData'].firstChange && this.travelForm) {
      this.initForm();  // Rebuild form with new data
    }
  }

  private initForm(): void {
    this.travelForm = this.fb.group({
      purposeOfTravel: [this.initialData.purposeOfTravel || '', Validators.required],
      tripType: [this.initialData.tripType || 'Round Trip', Validators.required],
      itinerary: this.fb.array(
        this.initialData.itinerary?.length
          ? this.initialData.itinerary.map(item => this.createItinerarySegment(item))
          : [this.createItinerarySegment()]
      ),
      mealProvisions: this.fb.group({
        dailySelections: this.fb.array([])
      }),
      accommodation: this.fb.group({
        accommodationType: [
          this.initialData.accommodation?.accommodationType || 'Hotel/Otels',
          Validators.required
        ],
        otherTypeDescription: [this.initialData.accommodation?.otherTypeDescription || ''],
        checkInDate: [this.initialData.accommodation?.checkInDate || null, Validators.required],
        checkInTime: [
          this.initialData.accommodation?.checkInTime || '',
          [Validators.required, Validators.pattern(this.timeRegex)]
        ],
        checkOutDate: [this.initialData.accommodation?.checkOutDate || null, Validators.required],
        checkOutTime: [
          this.initialData.accommodation?.checkOutTime || '',
          [Validators.required, Validators.pattern(this.timeRegex)]
        ],
        remarks: [this.initialData.accommodation?.remarks || '']
      }),
      companyTransportation: this.fb.array(
        this.initialData.companyTransportation?.length
          ? this.initialData.companyTransportation.map(item => this.createTransportationDetail(item))
          : [this.createTransportationDetail()]
      )
    });

    // Add validator for otherTypeDescription when accommodationType is 'Other'
    this.travelForm.get('accommodation.accommodationType')?.valueChanges.subscribe(
      (value: AccommodationType) => {
        const otherTypeControl = this.travelForm.get('accommodation.otherTypeDescription');
        if (value === 'Other') {
          otherTypeControl?.setValidators([Validators.required]);
        } else {
          otherTypeControl?.clearValidators();
        }
        otherTypeControl?.updateValueAndValidity();
      }
    );

    // Watch trip type changes to manage itinerary segments
    this.travelForm.get('tripType')?.valueChanges.subscribe(tripType => {
      const itineraryArray = this.itineraryArray;
      if (tripType === 'One Way' && itineraryArray.length > 1) {
        // Keep only first segment for one way
        while (itineraryArray.length > 1) {
          itineraryArray.removeAt(itineraryArray.length - 1);
        }
      }
    });

    // Watch itinerary changes to auto-generate meal dates
    this.itineraryArray.valueChanges.subscribe(() => {
      this.updateMealDatesFromItinerary();
    });

    // Initial meal dates generation
    this.updateMealDatesFromItinerary();
  }

  // Form array getters
  get itineraryArray(): FormArray {
    return this.travelForm.get('itinerary') as FormArray;
  }

  get dailyMealSelectionsArray(): FormArray {
    return this.travelForm.get('mealProvisions.dailySelections') as FormArray;
  }

  get transportationArray(): FormArray {
    return this.travelForm.get('companyTransportation') as FormArray;
  }

  // Form group creators
  createItinerarySegment(data?: Partial<ItinerarySegment>): FormGroup {
    return this.fb.group({
      date: [data?.date || null, Validators.required],
      day: [data?.day || '', Validators.required],
      from: [data?.from || '', Validators.required],
      to: [data?.to || '', Validators.required],
      etd: [data?.etd || '', Validators.pattern(this.timeRegex)],
      eta: [data?.eta || '', Validators.pattern(this.timeRegex)],
      flightNumber: [data?.flightNumber || '', Validators.required],
      remarks: [data?.remarks || '']
    });
  }

  createDailyMealSelection(data?: Partial<DailyMealSelection>): FormGroup {
    const formGroup = this.fb.group({
      date: [data?.date || null, Validators.required],
      breakfast: [data?.breakfast || false],
      lunch: [data?.lunch || false],
      dinner: [data?.dinner || false],
      supper: [data?.supper || false],
      refreshment: [data?.refreshment || false]
    });

    // Watch changes to update summary
    formGroup.valueChanges.subscribe(() => {
      this.updateMealSummary();
    });

    return formGroup;
  }

  createTransportationDetail(data?: Partial<CompanyTransportDetail>): FormGroup {
    return this.fb.group({
      date: [data?.date || null, Validators.required],
      day: [data?.day || '', Validators.required],
      from: [data?.from || '', Validators.required],
      to: [data?.to || '', Validators.required],
      etd: [data?.etd || '', [Validators.required, Validators.pattern(this.timeRegex)]],
      accommodationType: [data?.accommodationType || ''],
      address: [data?.address || ''],
      remarks: [data?.remarks || '']
    });
  }

  // Array manipulation methods
  addItinerarySegment(): void {
    this.itineraryArray.push(this.createItinerarySegment());
  }

  removeItinerarySegment(index: number): void {
    if (this.itineraryArray.length > 1) {
      this.itineraryArray.removeAt(index);
    }
  }

  addTransportationDetail(): void {
    this.transportationArray.push(this.createTransportationDetail());
  }

  removeTransportationDetail(index: number): void {
    if (this.transportationArray.length > 1) {
      this.transportationArray.removeAt(index);
    }
  }

  // Date change handlers to auto-fill day of week
  onItineraryDateChange(index: number, event: any): void {
    const dateValue = event.target.value;
    if (dateValue) {
      const date = new Date(dateValue);
      const dayIndex = date.getDay();
      const dayName = this.weekdays[dayIndex];
      this.itineraryArray.at(index).get('day')?.setValue(dayName);
    }
  }

  onTransportDateChange(index: number, event: any): void {
    const dateValue = event.target.value;
    if (dateValue) {
      const date = new Date(dateValue);
      const dayIndex = date.getDay();
      const dayName = this.weekdays[dayIndex];
      this.transportationArray.at(index).get('day')?.setValue(dayName);
    }
  }

  // Meal provisions logic
  private updateMealDatesFromItinerary(): void {
    const itinerary = this.itineraryArray.value;
    if (!itinerary || itinerary.length === 0) {
      this.dailyMealDates = [];
      this.dailyMealSelectionsArray.clear();
      this.updateMealSummary();
      return;
    }

    // Extract dates from itinerary
    const dates: Date[] = [];
    itinerary.forEach((segment: ItinerarySegment) => {
      if (segment.date) {
        const date = new Date(segment.date);
        if (!isNaN(date.getTime())) {
          dates.push(date);
        }
      }
    });

    if (dates.length === 0) {
      this.dailyMealDates = [];
      this.dailyMealSelectionsArray.clear();
      this.updateMealSummary();
      return;
    }

    // Sort dates
    dates.sort((a, b) => a.getTime() - b.getTime());

    // Generate all dates between first and last date (inclusive)
    const startDate = dates[0];
    const endDate = dates[dates.length - 1];
    const allDates: Date[] = [];

    for (let date = new Date(startDate); date <= endDate; date.setDate(date.getDate() + 1)) {
      allDates.push(new Date(date));
    }

    this.dailyMealDates = allDates;

    // Update form array to match dates
    const currentSelections = this.dailyMealSelectionsArray.value;
    this.dailyMealSelectionsArray.clear();

    allDates.forEach(date => {
      // Check if we have existing selection for this date
      const existing = currentSelections.find((sel: DailyMealSelection) => {
        const selDate = new Date(sel.date);
        return selDate.toDateString() === date.toDateString();
      });

      if (existing) {
        this.dailyMealSelectionsArray.push(this.createDailyMealSelection(existing));
      } else {
        this.dailyMealSelectionsArray.push(this.createDailyMealSelection({ date: date.toISOString() }));
      }
    });

    this.updateMealSummary();
  }

  private updateMealSummary(): void {
    const selections = this.dailyMealSelectionsArray.value;
    this.mealSummary = {
      breakfast: selections.filter((s: DailyMealSelection) => s.breakfast).length,
      lunch: selections.filter((s: DailyMealSelection) => s.lunch).length,
      dinner: selections.filter((s: DailyMealSelection) => s.dinner).length,
      supper: selections.filter((s: DailyMealSelection) => s.supper).length,
      refreshment: selections.filter((s: DailyMealSelection) => s.refreshment).length
    };
  }

  selectAllMealType(mealType: 'breakfast' | 'lunch' | 'dinner' | 'supper' | 'refreshment'): void {
    this.dailyMealSelectionsArray.controls.forEach(control => {
      control.patchValue({ [mealType]: true });
    });
  }

  resetMealType(mealType: 'breakfast' | 'lunch' | 'dinner' | 'supper' | 'refreshment'): void {
    this.dailyMealSelectionsArray.controls.forEach(control => {
      control.patchValue({ [mealType]: false });
    });
  }

  formatDate(date: Date | string): string {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  }

  // Form submission
  onSubmit(): void {
    if (this.travelForm.valid) {
      this.formSubmit.emit(this.travelForm.value);
    } else {
      this.markFormGroupTouched(this.travelForm);
    }
  }

  // Navigation
  onBack(): void {
    this.backClick.emit();
  }

  // Public methods for wizard integration
  getFormData(): DomesticTravelSpecificDetails {
    return this.travelForm.value;
  }

  isValid(): boolean {
    return this.travelForm.valid;
  }

  markAllAsTouched(): void {
    this.markFormGroupTouched(this.travelForm);
  }

  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();

      if (control instanceof FormGroup) {
        this.markFormGroupTouched(control);
      } else if (control instanceof FormArray) {
        control.controls.forEach(arrayControl => {
          if (arrayControl instanceof FormGroup) {
            this.markFormGroupTouched(arrayControl);
          }
        });
      }
    });
  }
}
