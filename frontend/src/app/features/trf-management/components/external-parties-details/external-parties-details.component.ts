import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { FormSectionCardComponent } from '../../../../shared/components/form-section-card/form-section-card.component';
import { MealProvisionComponent, DailyMealSelection } from '../../../../shared/components/meal-provision/meal-provision.component';
import { PassportUploadComponent } from '../../../../shared/components/passport-upload/passport-upload.component';
import { ItineraryEditorComponent, ItineraryFieldConfig } from '../../../../shared/components/itinerary-editor/itinerary-editor.component';

export interface PassportUploadDetails {
  file: File | null;
  fileName: string;
  fileUrl: string;
}

export interface MealProvisionDetails {
  dailySelections: DailyMealSelection[];
}

export interface ExternalPartiesDetails {
  purpose: string;
  tripType: 'One Way' | 'Round Trip';
  externalFullName: string;
  externalOrganization: string;
  externalRefToAuthorityLetter?: string;
  externalCostCenter: string;
  itinerary: any[];
  mealProvisions: MealProvisionDetails;
  passportUpload?: PassportUploadDetails;
}

@Component({
  selector: 'app-external-parties-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormSectionCardComponent, MealProvisionComponent, PassportUploadComponent, ItineraryEditorComponent],
  templateUrl: './external-parties-details.component.html',
  styleUrls: ['./external-parties-details.component.scss']
})
export class ExternalPartiesDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<ExternalPartiesDetails> = {};
  @Output() formSubmit = new EventEmitter<ExternalPartiesDetails>();
  @Output() backClick = new EventEmitter<void>();

  externalForm!: FormGroup;

  itineraryFields: ItineraryFieldConfig[] = [
    { key: 'departureDate', label: 'Date', type: 'date', required: true, requiredErrorMessage: 'Date is required', isPrimaryDate: true },
    { key: 'day', label: 'Day', type: 'readonly-text' },
    { key: 'departureTime', label: 'Departure Time', type: 'time' },
    { key: 'departureLocation', label: 'From', type: 'text', required: true, placeholder: 'Origin city/airport', requiredErrorMessage: 'Origin location is required' },
    { key: 'arrivalDate', label: 'Arrival Date', type: 'text', hidden: true },
    { key: 'arrivalTime', label: 'Arrival Time', type: 'time' },
    { key: 'arrivalLocation', label: 'To', type: 'text', required: true, placeholder: 'Destination city/airport', requiredErrorMessage: 'Destination location is required' },
    { key: 'modeOfTransport', label: 'Mode of Transport', type: 'text', required: true, placeholder: 'e.g., Flight, Train, Car', requiredErrorMessage: 'Mode of transport is required' },
    { key: 'remarks', label: 'Remarks', type: 'text', placeholder: 'Any additional information', colSpan: 8 }
  ];
  tripTypeValue: 'One Way' | 'Round Trip' = 'One Way';
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
    if (changes['initialData'] && !changes['initialData'].firstChange && this.externalForm) {
      this.initForm();  // Rebuild form with new data
    }

    // Load existing passport file URL if available
    if (changes['initialData'] && this.initialData?.passportUpload) {
      this.passportFileName = this.initialData.passportUpload.fileName || '';
      this.passportFileUrl = this.initialData.passportUpload.fileUrl || '';
    }
  }

  private initForm(): void {
    this.externalForm = this.fb.group({
      purpose: [this.initialData.purpose || '', [Validators.required, Validators.minLength(10)]],
      tripType: [this.initialData.tripType || 'One Way', Validators.required],
      externalFullName: [this.initialData.externalFullName || '', Validators.required],
      externalOrganization: [this.initialData.externalOrganization || '', Validators.required],
      externalRefToAuthorityLetter: [this.initialData.externalRefToAuthorityLetter || ''],
      externalCostCenter: [this.initialData.externalCostCenter || '', Validators.required]
    });

    this.tripTypeValue = this.initialData.tripType || 'One Way';

    // Watch trip type changes to drive the itinerary editor's add/remove gating
    this.externalForm.get('tripType')?.valueChanges.subscribe(tripType => {
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

  onSubmit(): void {

    if (this.externalForm.valid) {
      const formValue = this.externalForm.getRawValue();
      this.formSubmit.emit({
        ...formValue,
        itinerary: this.itinerarySegments,
        mealProvisions: { dailySelections: this.mealSelections }
      });
    } else {
      this.logFormErrors(this.externalForm);
      this.formUtils.markFormGroupTouched(this.externalForm);
    }
  }

  private logFormErrors(formGroup: FormGroup | FormArray, path: string = ''): void {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      const currentPath = path ? `${path}.${key}` : key;

      if (control instanceof FormGroup || control instanceof FormArray) {
        this.logFormErrors(control, currentPath);
      } else if (control?.invalid) {
      }
    });
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
  getFormData(): ExternalPartiesDetails {
    return {
      ...this.externalForm.getRawValue(),
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
    return this.externalForm.valid;
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.externalForm);
  }

  onBack(): void {
    this.backClick.emit();
  }
}
