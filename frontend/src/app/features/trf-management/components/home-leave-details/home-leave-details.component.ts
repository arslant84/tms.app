import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
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
    { key: 'from', label: 'From / Откуда', type: 'text', required: true, placeholder: 'Origin city/airport', requiredErrorMessage: 'Origin is required' },
    { key: 'to', label: 'To / Куда', type: 'text', required: true, placeholder: 'Destination city/airport', requiredErrorMessage: 'Destination is required' },
    { key: 'flightNumber', label: 'Flight/Transport Number', type: 'text', placeholder: 'e.g., LH1234, Train 45' },
    { key: 'remarks', label: 'Remarks / Примечания', type: 'text', placeholder: 'Any additional information', colSpan: 8 }
  ];
  tripTypeValue: 'One Way' | 'Round Trip' = 'Round Trip';
  itinerarySegments: Record<string, any>[] = [];
  advanceAmounts: Record<string, any>[] = [];
  advanceAmountEditorValid = false;

  @ViewChild(AdvanceAmountEditorComponent) advanceAmountEditor?: AdvanceAmountEditorComponent;

  // Passport upload
  passportFile: File | null = null;
  passportFileName: string = '';
  passportFileUrl: string = '';

  constructor(
    private fb: FormBuilder,
    private formUtils: FormUtilsService
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

  onAdvanceAmountsChange(items: Record<string, any>[]): void {
    this.advanceAmounts = items;
  }

  onAdvanceValidityChange(valid: boolean): void {
    this.advanceAmountEditorValid = valid;
  }

  onSubmit(): void {
    if (this.homeLeaveForm.valid && this.advanceAmountEditorValid) {
      const formValue = this.homeLeaveForm.getRawValue();
      this.formSubmit.emit({
        ...formValue,
        itinerary: this.itinerarySegments,
        advanceAmountRequested: this.advanceAmounts
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
    return this.homeLeaveForm.valid && this.advanceAmountEditorValid;
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.homeLeaveForm);
    this.advanceAmountEditor?.markConsentTouched();
  }

  onBack(): void {
    this.backClick.emit();
  }
}
