import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { FormSectionCardComponent } from '../../../../shared/components/form-section-card/form-section-card.component';
import { MealProvisionComponent, DailyMealSelection } from '../../../../shared/components/meal-provision/meal-provision.component';
import { PassportUploadComponent } from '../../../../shared/components/passport-upload/passport-upload.component';
import { ItineraryEditorComponent, ItineraryFieldConfig } from '../../../../shared/components/itinerary-editor/itinerary-editor.component';

export const DOMESTIC_CITIES = ['Ashgabat', 'Turkmenbashi', 'Turkmenabat', 'Dashoguz', 'Mary'];

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
  imports: [CommonModule, ReactiveFormsModule, FormSectionCardComponent, MealProvisionComponent, PassportUploadComponent, ItineraryEditorComponent],
  templateUrl: './domestic-travel-details.component.html',
  styleUrls: ['./domestic-travel-details.component.scss']
})
export class DomesticTravelDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<DomesticTravelSpecificDetails> = {};
  @Output() formSubmit = new EventEmitter<DomesticTravelSpecificDetails>();
  @Output() backClick = new EventEmitter<void>();

  travelForm!: FormGroup;

  itineraryFields: ItineraryFieldConfig[] = [
    { key: 'date', label: 'Date', type: 'date', required: true, requiredErrorMessage: 'Date is required', isPrimaryDate: true },
    { key: 'day', label: 'Day', type: 'readonly-text' },
    { key: 'from', label: 'From', type: 'select', options: DOMESTIC_CITIES, required: true, requiredErrorMessage: 'Origin is required' },
    { key: 'to', label: 'To', type: 'select', options: DOMESTIC_CITIES, required: true, requiredErrorMessage: 'Destination is required' },
    { key: 'etd', label: 'ETD', type: 'text', placeholder: 'e.g. 14:30 or Morning' },
    { key: 'eta', label: 'ETA', type: 'text', placeholder: 'e.g. 14:30 or Morning' },
    { key: 'flightNumber', label: 'Flight', type: 'text' },
    { key: 'remarks', label: 'Remarks', type: 'text', colSpan: 8 }
  ];
  tripTypeValue: 'One Way' | 'Round Trip' = 'Round Trip';
  itinerarySegments: Record<string, any>[] = [];
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
      tripType: [this.initialData.tripType || 'Round Trip', Validators.required]
    });

    this.tripTypeValue = this.initialData.tripType || 'Round Trip';

    // Watch trip type changes to drive the itinerary editor's add/remove gating
    this.travelForm.get('tripType')?.valueChanges.subscribe(tripType => {
      this.tripTypeValue = tripType;
    });

    this.mealSelections = this.initialData.mealProvisions?.dailySelections || [];
  }

  onItinerarySegmentsChange(segments: Record<string, any>[]): void {
    this.itinerarySegments = segments;
  }

  onItineraryDatesChange(dates: (string | null)[]): void {
    this.itineraryDates = dates;
  }

  onMealSelectionsChange(selections: DailyMealSelection[]): void {
    this.mealSelections = selections;
  }

  // Form submission
  onSubmit(): void {
    if (this.travelForm.valid) {
      this.formSubmit.emit({
        ...this.travelForm.value,
        itinerary: this.itinerarySegments,
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
      itinerary: this.itinerarySegments,
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
