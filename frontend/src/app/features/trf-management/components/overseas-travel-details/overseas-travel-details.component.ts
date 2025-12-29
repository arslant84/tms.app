import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';

export interface ItinerarySegment {
  date: string;
  day: string;
  from: string;
  to: string;
  etd: string;
  eta: string;
  flightNumber: string;
  remarks?: string;
}

export interface AdvanceBankDetails {
  bankName: string;
  accountNumber: string;
}

export interface AdvanceAmountItem {
  dateFrom: string;
  dateTo: string;
  lh: number;
  ma: number;
  oa: number;
  tr: number;
  oe: number;
  usd: number;
  remarks?: string;
}

export interface OverseasTravelDetails {
  purpose: string;
  tripType: 'One Way' | 'Round Trip';
  itinerary: ItinerarySegment[];
  advanceBankDetails?: AdvanceBankDetails;
  advanceAmountRequested?: AdvanceAmountItem[];
}

@Component({
  selector: 'app-overseas-travel-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './overseas-travel-details.component.html',
  styleUrls: ['./overseas-travel-details.component.scss']
})
export class OverseasTravelDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<OverseasTravelDetails> = {};
  @Output() formSubmit = new EventEmitter<OverseasTravelDetails>();

  overseasForm!: FormGroup;
  weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  constructor(private fb: FormBuilder, private formUtils: FormUtilsService) {}

  ngOnInit(): void {
    this.initForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // When initialData changes (e.g., loaded from API in edit mode), rebuild the form
    if (changes['initialData'] && !changes['initialData'].firstChange && this.overseasForm) {
      this.initForm();  // Rebuild form with new data
    }
  }

  private initForm(): void {
    this.overseasForm = this.fb.group({
      purpose: [this.initialData.purpose || '', [Validators.required, Validators.minLength(10)]],
      tripType: [this.initialData.tripType || 'One Way', Validators.required],
      itinerary: this.fb.array([]),
      advanceBankDetails: this.fb.group({
        bankName: ['', Validators.required],
        accountNumber: ['', Validators.required]
      }),
      advanceAmountRequested: this.fb.array([])
    });

    // Initialize with one itinerary segment
    if (this.initialData.itinerary && this.initialData.itinerary.length > 0) {
      this.initialData.itinerary.forEach(segment => this.addItinerarySegment(segment));
    } else {
      this.addItinerarySegment();
    }

    // Initialize with one advance amount item
    if (this.initialData.advanceAmountRequested && this.initialData.advanceAmountRequested.length > 0) {
      this.initialData.advanceAmountRequested.forEach(item => this.addAdvanceAmountItem(item));
    } else {
      this.addAdvanceAmountItem();
    }

    // Set bank details if provided
    if (this.initialData.advanceBankDetails) {
      this.overseasForm.get('advanceBankDetails')?.patchValue({
        bankName: this.initialData.advanceBankDetails.bankName || '',
        accountNumber: this.initialData.advanceBankDetails.accountNumber || ''
      });
    }

    // Watch trip type changes
    this.overseasForm.get('tripType')?.valueChanges.subscribe(tripType => {
      const itineraryArray = this.itinerary;
      if (tripType === 'One Way' && itineraryArray.length > 1) {
        // Keep only first segment for one way
        while (itineraryArray.length > 1) {
          itineraryArray.removeAt(itineraryArray.length - 1);
        }
      }
    });
  }

  get itinerary(): FormArray {
    return this.overseasForm.get('itinerary') as FormArray;
  }

  get advanceAmountRequested(): FormArray {
    return this.overseasForm.get('advanceAmountRequested') as FormArray;
  }

  private createItinerarySegment(data?: Partial<ItinerarySegment>): FormGroup {
    return this.fb.group({
      date: [data?.date || '', Validators.required],
      day: [data?.day || ''],
      from: [data?.from || '', Validators.required],
      to: [data?.to || '', Validators.required],
      etd: [data?.etd || '', Validators.pattern(/^([01]\d|2[0-3]):([0-5]\d)$/)],
      eta: [data?.eta || '', Validators.pattern(/^([01]\d|2[0-3]):([0-5]\d)$/)],
      flightNumber: [data?.flightNumber || '', Validators.required],
      remarks: [data?.remarks || '']
    });
  }

  private createAdvanceAmountItem(data?: Partial<AdvanceAmountItem>): FormGroup {
    const formGroup = this.fb.group({
      dateFrom: [data?.dateFrom || '', Validators.required],
      dateTo: [data?.dateTo || '', Validators.required],
      lh: [data?.lh || 0, [Validators.min(0)]],
      ma: [data?.ma || 0, [Validators.min(0)]],
      oa: [data?.oa || 0, [Validators.min(0)]],
      tr: [data?.tr || 0, [Validators.min(0)]],
      oe: [data?.oe || 0, [Validators.min(0)]],
      usd: [{ value: data?.usd || 0, disabled: true }],
      remarks: [data?.remarks || '']
    });

    // Calculate USD when amount fields change
    ['lh', 'ma', 'oa', 'tr', 'oe'].forEach(field => {
      formGroup.get(field)?.valueChanges.subscribe(() => {
        this.calculateUSD(formGroup);
      });
    });

    return formGroup;
  }

  private calculateUSD(formGroup: FormGroup): void {
    const lh = Number(formGroup.get('lh')?.value) || 0;
    const ma = Number(formGroup.get('ma')?.value) || 0;
    const oa = Number(formGroup.get('oa')?.value) || 0;
    const tr = Number(formGroup.get('tr')?.value) || 0;
    const oe = Number(formGroup.get('oe')?.value) || 0;
    const total = lh + ma + oa + tr + oe;
    formGroup.get('usd')?.setValue(total, { emitEvent: false });
  }

  addItinerarySegment(data?: Partial<ItinerarySegment>): void {
    const tripType = this.overseasForm.get('tripType')?.value;
    if (tripType === 'One Way' && this.itinerary.length >= 1) {
      return; // Don't allow more than 1 segment for one way
    }
    this.itinerary.push(this.createItinerarySegment(data));
  }

  removeItinerarySegment(index: number): void {
    if (this.itinerary.length > 1) {
      this.itinerary.removeAt(index);
    }
  }

  addAdvanceAmountItem(data?: Partial<AdvanceAmountItem>): void {
    this.advanceAmountRequested.push(this.createAdvanceAmountItem(data));
  }

  removeAdvanceAmountItem(index: number): void {
    if (this.advanceAmountRequested.length > 1) {
      this.advanceAmountRequested.removeAt(index);
    }
  }

  onDateChange(index: number, event: any): void {
    const date = new Date(event.target.value);
    const dayIndex = date.getDay();
    const dayName = this.weekdays[dayIndex];
    this.itinerary.at(index).get('day')?.setValue(dayName);
  }

  onSubmit(): void {
    if (this.overseasForm.valid) {
      const formValue = this.overseasForm.getRawValue();
      this.formSubmit.emit(formValue);
    } else {
      this.formUtils.markFormGroupTouched(this.overseasForm);
    }
  }

  // Public methods for wizard integration
  getFormData(): OverseasTravelDetails {
    return this.overseasForm.getRawValue();
  }

  isValid(): boolean {
    return this.overseasForm.valid;
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.overseasForm);
  }
}
