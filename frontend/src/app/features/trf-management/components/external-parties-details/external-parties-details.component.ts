import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';

export interface PassportUploadDetails {
  file: File | null;
  fileName: string;
  fileUrl: string;
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
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './external-parties-details.component.html',
  styleUrls: ['./external-parties-details.component.scss']
})
export class ExternalPartiesDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<ExternalPartiesDetails> = {};
  @Output() formSubmit = new EventEmitter<ExternalPartiesDetails>();
  @Output() backClick = new EventEmitter<void>();

  externalForm!: FormGroup;
  weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  dailyMealDates: Date[] = [];
  mealSummary = {
    breakfast: 0,
    lunch: 0,
    dinner: 0,
    supper: 0,
    refreshment: 0
  };

  // Passport upload
  passportFile: File | null = null;
  passportFileName: string = '';
  passportFileUrl: string = '';
  passportFileError: string = '';
  allowedFileTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
  maxFileSize = 10 * 1024 * 1024; // 10MB

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
      externalCostCenter: [this.initialData.externalCostCenter || '', Validators.required],
      itinerary: this.fb.array([]),
      mealProvisions: this.fb.group({
        dailySelections: this.fb.array(
          this.initialData.mealProvisions?.dailySelections?.length
            ? this.initialData.mealProvisions.dailySelections.map(item => this.createDailyMealSelection(item))
            : []
        )
      })
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

    // Watch itinerary changes to auto-generate meal dates
    this.itinerary.valueChanges.subscribe(() => {
      this.updateMealDatesFromItinerary();
    });

    // Initial meal dates generation
    this.updateMealDatesFromItinerary();
  }

  get itinerary(): FormArray {
    return this.externalForm.get('itinerary') as FormArray;
  }

  get dailyMealSelectionsArray(): FormArray {
    return this.externalForm.get('mealProvisions.dailySelections') as FormArray;
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

  // Meal provisions logic
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

  private updateMealDatesFromItinerary(): void {
    const itinerary = this.itinerary.value;
    if (!itinerary || itinerary.length === 0) {
      this.dailyMealDates = [];
      this.dailyMealSelectionsArray.clear();
      this.updateMealSummary();
      return;
    }

    // Extract dates from itinerary
    const dates: Date[] = [];
    itinerary.forEach((segment: any) => {
      if (segment.departureDate) {
        const date = new Date(segment.departureDate);
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

  onSubmit(): void {

    if (this.externalForm.valid) {
      const formValue = this.externalForm.getRawValue();
      this.formSubmit.emit(formValue);
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
  onPassportFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];

      // Validate file type
      if (!this.allowedFileTypes.includes(file.type)) {
        this.passportFileError = 'Please upload a PDF, JPG, or PNG file.';
        this.passportFile = null;
        this.passportFileName = '';
        return;
      }

      // Validate file size
      if (file.size > this.maxFileSize) {
        this.passportFileError = 'File size must not exceed 10MB.';
        this.passportFile = null;
        this.passportFileName = '';
        return;
      }

      this.passportFileError = '';
      this.passportFile = file;
      this.passportFileName = file.name;
    }
  }

  removePassportFile(): void {
    this.passportFile = null;
    this.passportFileName = '';
    this.passportFileUrl = '';
    this.passportFileError = '';
  }

  // Public methods for wizard integration
  getFormData(): ExternalPartiesDetails {
    return {
      ...this.externalForm.getRawValue(),
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
