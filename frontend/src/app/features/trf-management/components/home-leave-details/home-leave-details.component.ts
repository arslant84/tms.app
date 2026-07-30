import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { FormSectionCardComponent } from '../../../../shared/components/form-section-card/form-section-card.component';
import { PassportUploadComponent } from '../../../../shared/components/passport-upload/passport-upload.component';

export interface PassportUploadDetails {
  file: File | null;
  fileName: string;
  fileUrl: string;
}

export interface HomeLeaveDetails {
  purpose: string;
  tripType: 'One Way' | 'Round Trip';
  itinerary: any[];
  advanceBankDetails?: any;
  passportUpload?: PassportUploadDetails;
}

@Component({
  selector: 'app-home-leave-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormSectionCardComponent, PassportUploadComponent],
  templateUrl: './home-leave-details.component.html',
  styleUrls: ['./home-leave-details.component.scss']
})
export class HomeLeaveDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<HomeLeaveDetails> = {};
  @Output() formSubmit = new EventEmitter<HomeLeaveDetails>();
  @Output() backClick = new EventEmitter<void>();

  homeLeaveForm!: FormGroup;

  // Passport upload
  passportFile: File | null = null;
  passportFileName: string = '';
  passportFileUrl: string = '';

  constructor(
    private fb: FormBuilder,
    private formUtils: FormUtilsService,
    private dateUtils: DateUtilsService
  ) {}

  ngOnInit(): void {
    this.initForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // When initialData changes (e.g., loaded from API in edit mode), rebuild the form
    if (changes['initialData'] && !changes['initialData'].firstChange && this.homeLeaveForm) {
      this.initForm();  // Rebuild form with new data
    }

    // Load existing passport file URL if available
    if (changes['initialData'] && this.initialData?.passportUpload) {
      this.passportFileName = this.initialData.passportUpload.fileName || '';
      this.passportFileUrl = this.initialData.passportUpload.fileUrl || '';
    }
  }

  private initForm(): void {
    this.homeLeaveForm = this.fb.group({
      purpose: [this.initialData.purpose || '', [Validators.required, Validators.minLength(10)]],
      tripType: [this.initialData.tripType || 'Round Trip', Validators.required],
      itinerary: this.fb.array([]),
      advanceBankDetails: this.fb.group({
        bankName: [''],
        accountNumber: [''],
        accountName: [''],
        branchAddress: [''],
        currency: ['USD']
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

    // Set bank details if provided
    if (this.initialData.advanceBankDetails) {
      this.homeLeaveForm.get('advanceBankDetails')?.patchValue({
        bankName: this.initialData.advanceBankDetails.bankName || '',
        accountNumber: this.initialData.advanceBankDetails.accountNumber || '',
        accountName: this.initialData.advanceBankDetails.accountName || '',
        branchAddress: this.initialData.advanceBankDetails.branchAddress || '',
        currency: this.initialData.advanceBankDetails.currency || 'USD'
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
    const dayName = this.dateUtils.getDayOfWeek(event.target.value);
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
      this.formUtils.markFormGroupTouched(this.homeLeaveForm);
    }
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
  getFormData(): HomeLeaveDetails {
    return {
      ...this.homeLeaveForm.getRawValue(),
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
    return this.homeLeaveForm.valid;
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.homeLeaveForm);
  }

  onBack(): void {
    this.backClick.emit();
  }
}
