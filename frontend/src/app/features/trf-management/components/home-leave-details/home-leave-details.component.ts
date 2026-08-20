import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { FormSectionCardComponent } from '../../../../shared/components/form-section-card/form-section-card.component';
import { PassportUploadComponent } from '../../../../shared/components/passport-upload/passport-upload.component';
import { ItineraryEditorComponent, ItineraryFieldConfig } from '../../../../shared/components/itinerary-editor/itinerary-editor.component';
import { AdvanceAmountEditorComponent } from '../../../../shared/components/advance-amount-editor/advance-amount-editor.component';

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
  advanceAmountRequested?: any[];
  advanceConsentAccepted?: boolean;
  passportUpload?: PassportUploadDetails;
}

@Component({
  selector: 'app-home-leave-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormSectionCardComponent, PassportUploadComponent, ItineraryEditorComponent, AdvanceAmountEditorComponent],
  templateUrl: './home-leave-details.component.html',
  styleUrls: ['./home-leave-details.component.scss']
})
export class HomeLeaveDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<HomeLeaveDetails> = {};
  @Output() formSubmit = new EventEmitter<HomeLeaveDetails>();
  @Output() backClick = new EventEmitter<void>();

  homeLeaveForm!: FormGroup;

  itineraryFields: ItineraryFieldConfig[] = [
    { key: 'date', label: 'Date / Дата', type: 'date', required: true, requiredErrorMessage: 'Date is required', isPrimaryDate: true },
    { key: 'day', label: 'Day / День', type: 'readonly-text' },
    { key: 'from', label: 'From / Откуда', type: 'text', required: true, placeholder: 'Origin city/airport', requiredErrorMessage: 'Origin is required', isOrigin: true },
    { key: 'to', label: 'To / Куда', type: 'text', required: true, placeholder: 'Destination city/airport', requiredErrorMessage: 'Destination is required', isDestination: true },
    { key: 'flightNumber', label: 'Flight/Transport Number', type: 'text', placeholder: 'e.g., LH1234, Train 45' },
    { key: 'remarks', label: 'Remarks / Примечания', type: 'text', placeholder: 'Any additional information', colSpan: 8 }
  ];
  tripTypeValue: 'One Way' | 'Round Trip' = 'Round Trip';
  itinerarySegments: Record<string, any>[] = [];
  itineraryDates: (string | null)[] = [];
  advanceAmounts: Record<string, any>[] = [];
  advanceAmountEditorValid = false;
  advanceConsentAccepted = false;

  @ViewChild(AdvanceAmountEditorComponent) advanceAmountEditor?: AdvanceAmountEditorComponent;
  @ViewChild(ItineraryEditorComponent) itineraryEditorRef?: ItineraryEditorComponent;

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
      advanceBankDetails: this.fb.group({
        bankName: [''],
        accountNumber: [''],
        accountName: [''],
        branchAddress: [''],
        currency: ['USD']
      })
    });

    this.tripTypeValue = this.initialData.tripType || 'Round Trip';

    // Watch trip type changes to drive the itinerary editor's add/remove gating
    this.homeLeaveForm.get('tripType')?.valueChanges.subscribe(tripType => {
      this.tripTypeValue = tripType;
    });

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

  onItinerarySegmentsChange(segments: Record<string, any>[]): void {
    this.itinerarySegments = segments;
  }

  onItineraryDatesChange(dates: (string | null)[]): void {
    this.itineraryDates = dates;
  }

  onAdvanceAmountsChange(items: Record<string, any>[]): void {
    this.advanceAmounts = items;
  }

  onAdvanceValidityChange(valid: boolean): void {
    this.advanceAmountEditorValid = valid;
  }

  onAdvanceConsentChange(accepted: boolean): void {
    this.advanceConsentAccepted = accepted;
  }

  onSubmit(): void {
    if (this.homeLeaveForm.valid && this.advanceAmountEditorValid) {
      const formValue = this.homeLeaveForm.getRawValue();
      this.formSubmit.emit({
        ...formValue,
        itinerary: this.itinerarySegments,
        advanceAmountRequested: this.advanceAmounts,
        advanceConsentAccepted: this.advanceConsentAccepted
      });
    } else {
      this.formUtils.markFormGroupTouched(this.homeLeaveForm);
      this.advanceAmountEditor?.markConsentTouched();
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
      itinerary: this.itinerarySegments,
      advanceAmountRequested: this.advanceAmounts,
      advanceConsentAccepted: this.advanceConsentAccepted,
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

  get isItineraryIncomplete(): boolean {
    return this.tripTypeValue === 'Round Trip' && this.itinerarySegments.length < 2;
  }

  get isItineraryOutOfOrder(): boolean {
    return !this.dateUtils.isChronological(this.itineraryDates);
  }

  isValid(): boolean {
    return this.homeLeaveForm.valid && this.advanceAmountEditorValid && !this.isItineraryIncomplete && !this.isItineraryOutOfOrder
      && (!this.itineraryEditorRef || this.itineraryEditorRef.form.valid);
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.homeLeaveForm);
    this.advanceAmountEditor?.markConsentTouched();
    this.itineraryEditorRef?.markAllAsTouched();
  }

  onBack(): void {
    this.backClick.emit();
  }
}
