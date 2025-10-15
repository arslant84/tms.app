import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
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

export interface MealProvisionDetails {
  dateFromTo: string;
  breakfast?: number;
  lunch?: number;
  dinner?: number;
  supper?: number;
  refreshment?: number;
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
  itinerary: ItinerarySegment[];
  mealProvisions: MealProvisionDetails[];
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
export class DomesticTravelDetailsComponent implements OnInit {
  @Input() initialData: Partial<DomesticTravelSpecificDetails> = {};
  @Output() formSubmit = new EventEmitter<DomesticTravelSpecificDetails>();
  
  travelForm!: FormGroup;
  timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
  accommodationTypes: AccommodationType[] = ['Hotel/Otels', 'Staff House/PKC Kampung/Kinyahli camp', 'Other'];

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initForm();
  }

  private initForm(): void {
    this.travelForm = this.fb.group({
      purposeOfTravel: [this.initialData.purposeOfTravel || '', Validators.required],
      itinerary: this.fb.array(
        this.initialData.itinerary?.length 
          ? this.initialData.itinerary.map(item => this.createItinerarySegment(item))
          : [this.createItinerarySegment()]
      ),
      mealProvisions: this.fb.array(
        this.initialData.mealProvisions?.length
          ? this.initialData.mealProvisions.map(item => this.createMealProvision(item))
          : [this.createMealProvision()]
      ),
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
  }

  // Form array getters
  get itineraryArray(): FormArray {
    return this.travelForm.get('itinerary') as FormArray;
  }

  get mealProvisionsArray(): FormArray {
    return this.travelForm.get('mealProvisions') as FormArray;
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

  createMealProvision(data?: Partial<MealProvisionDetails>): FormGroup {
    return this.fb.group({
      dateFromTo: [data?.dateFromTo || '', Validators.required],
      breakfast: [data?.breakfast || 0, [Validators.min(0)]],
      lunch: [data?.lunch || 0, [Validators.min(0)]],
      dinner: [data?.dinner || 0, [Validators.min(0)]],
      supper: [data?.supper || 0, [Validators.min(0)]],
      refreshment: [data?.refreshment || 0, [Validators.min(0)]]
    });
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

  addMealProvision(): void {
    this.mealProvisionsArray.push(this.createMealProvision());
  }

  removeMealProvision(index: number): void {
    if (this.mealProvisionsArray.length > 1) {
      this.mealProvisionsArray.removeAt(index);
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

  // Form submission
  onSubmit(): void {
    if (this.travelForm.valid) {
      this.formSubmit.emit(this.travelForm.value);
    } else {
      this.markFormGroupTouched(this.travelForm);
    }
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
