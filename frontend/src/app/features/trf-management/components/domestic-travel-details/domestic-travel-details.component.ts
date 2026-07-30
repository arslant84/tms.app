import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { FormSectionCardComponent } from '../../../../shared/components/form-section-card/form-section-card.component';
import { MealProvisionComponent, DailyMealSelection } from '../../../../shared/components/meal-provision/meal-provision.component';
import { PassportUploadComponent } from '../../../../shared/components/passport-upload/passport-upload.component';

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
  dailySelections: DailyMealSelection[];
}

export interface PassportUploadDetails {
  file: File | null;
  fileName: string;
  fileUrl: string;
}

export interface DomesticTravelSpecificDetails {
  purposeOfTravel: string;
  tripType: 'One Way' | 'Round Trip';
  itinerary: ItinerarySegment[];
  mealProvisions: MealProvisionDetails;
  passportUpload?: PassportUploadDetails;
}

@Component({
  selector: 'app-domestic-travel-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormSectionCardComponent, MealProvisionComponent, PassportUploadComponent],
  templateUrl: './domestic-travel-details.component.html',
  styleUrls: ['./domestic-travel-details.component.scss']
})
export class DomesticTravelDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<DomesticTravelSpecificDetails> = {};
  @Output() formSubmit = new EventEmitter<DomesticTravelSpecificDetails>();
  @Output() backClick = new EventEmitter<void>();

  travelForm!: FormGroup;

  itineraryDates: (string | null)[] = [];
  mealSelections: DailyMealSelection[] = [];

  // Passport upload
  passportFile: File | null = null;
  passportFileName: string = '';
  passportFileUrl: string = '';

  constructor(
    private fb: FormBuilder,
    private formUtils: FormUtilsService,
    public dateUtils: DateUtilsService
  ) {}

  ngOnInit(): void {
    this.initForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // When initialData changes (e.g., loaded from API in edit mode), rebuild the form
    if (changes['initialData'] && !changes['initialData'].firstChange && this.travelForm) {
      this.initForm();  // Rebuild form with new data
    }

    // Load existing passport file URL if available
    if (changes['initialData'] && this.initialData?.passportUpload) {
      this.passportFileName = this.initialData.passportUpload.fileName || '';
      this.passportFileUrl = this.initialData.passportUpload.fileUrl || '';
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
      )
    });

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

    // Watch itinerary changes to keep the meal-provision component's dates in sync
    this.itineraryArray.valueChanges.subscribe(() => {
      this.updateItineraryDates();
    });

    // Initial itinerary dates
    this.updateItineraryDates();
    this.mealSelections = this.initialData.mealProvisions?.dailySelections || [];
  }

  // Form array getters
  get itineraryArray(): FormArray {
    return this.travelForm.get('itinerary') as FormArray;
  }

  // Check if trip type allows adding itinerary segments (only Round Trip)
  get canAddItinerarySegment(): boolean {
    return this.travelForm.get('tripType')?.value === 'Round Trip';
  }

  // Form group creators
  createItinerarySegment(data?: Partial<ItinerarySegment>): FormGroup {
    return this.fb.group({
      date: [data?.date || null, Validators.required],
      day: [data?.day || '', Validators.required],
      from: [data?.from || '', Validators.required],
      to: [data?.to || '', Validators.required],
      etd: [data?.etd || ''],
      eta: [data?.eta || ''],
      flightNumber: [data?.flightNumber || ''],
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

  // Date change handlers to auto-fill day of week
  onItineraryDateChange(index: number, event: any): void {
    const dateValue = event.target.value;
    if (dateValue) {
      const dayName = this.dateUtils.getDayOfWeek(dateValue);
      this.itineraryArray.at(index).get('day')?.setValue(dayName);
    }
  }

  // Meal provisions logic
  private updateItineraryDates(): void {
    this.itineraryDates = this.itineraryArray.value.map((segment: ItinerarySegment) => segment.date as unknown as string);
  }

  onMealSelectionsChange(selections: DailyMealSelection[]): void {
    this.mealSelections = selections;
  }

  // Form submission
  onSubmit(): void {
    if (this.travelForm.valid) {
      this.formSubmit.emit({
        ...this.travelForm.value,
        mealProvisions: { dailySelections: this.mealSelections }
      });
    } else {
      this.formUtils.markFormGroupTouched(this.travelForm);
    }
  }

  // Navigation
  onBack(): void {
    this.backClick.emit();
  }

  // Passport file handling
  onPassportFileSelected(file: File): void {
    this.passportFile = file;
    this.passportFileName = file.name;
  }

  onPassportFileRemoved(): void {
    this.passportFile = null;
    this.passportFileName = '';
    this.passportFileUrl = '';
  }

  // Public methods for wizard integration
  getFormData(): DomesticTravelSpecificDetails {
    return {
      ...this.travelForm.value,
      mealProvisions: { dailySelections: this.mealSelections },
      passportUpload: {
        file: this.passportFile,
        fileName: this.passportFileName,
        fileUrl: this.passportFileUrl
      }
    };
  }

  getPassportFile(): File | null {
    return this.passportFile;
  }

  isValid(): boolean {
    return this.travelForm.valid;
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.travelForm);
  }
}
