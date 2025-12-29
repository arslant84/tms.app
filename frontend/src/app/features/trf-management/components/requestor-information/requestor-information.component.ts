import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { UserFormHelperService } from '../../../../core/utils/user-form-helper.service';

export interface RequestorInformation {
  fullName: string;
  staffId: string;
  department: string;
  position?: string;
  costCenter: string;
  contactNo: string;
  email: string;
}

@Component({
  selector: 'app-requestor-information',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './requestor-information.component.html',
  styleUrls: ['./requestor-information.component.scss']
})
export class RequestorInformationComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<RequestorInformation> = {};
  @Output() formSubmit = new EventEmitter<RequestorInformation>();

  requestorForm!: FormGroup;

  constructor(
    private fb: FormBuilder,
    private formUtils: FormUtilsService,
    private userFormHelper: UserFormHelperService
  ) {}

  ngOnInit(): void {
    this.initForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // When initialData changes (e.g., loaded from API in edit mode), update the form
    if (changes['initialData'] && !changes['initialData'].firstChange && this.requestorForm) {
      this.patchFormWithInitialData();
    }
  }

  private initForm(): void {
    // Merge initial data with user defaults
    const formDefaults = this.userFormHelper.mergeWithUserDefaults({
      fullName: this.initialData.fullName,
      staffId: this.initialData.staffId,
      department: this.initialData.department,
      position: this.initialData.position,
      email: this.initialData.email,
      phone: this.initialData.contactNo
    });

    // Use merged data for form initialization
    this.requestorForm = this.fb.group({
      fullName: [formDefaults.fullName, Validators.required],
      staffId: [formDefaults.staffId, Validators.required],
      department: [formDefaults.department, Validators.required],
      position: [formDefaults.position],
      costCenter: [this.initialData.costCenter || '', Validators.required],
      contactNo: [formDefaults.phone, Validators.required],
      email: [formDefaults.email, [Validators.required, Validators.email]]
    });
  }

  private patchFormWithInitialData(): void {
    if (this.initialData) {
      this.requestorForm.patchValue({
        fullName: this.initialData.fullName || '',
        staffId: this.initialData.staffId || '',
        department: this.initialData.department || '',
        position: this.initialData.position || '',
        costCenter: this.initialData.costCenter || '',
        contactNo: this.initialData.contactNo || '',
        email: this.initialData.email || ''
      });
    }
  }

  onSubmit(): void {
    if (this.requestorForm.valid) {
      this.formSubmit.emit(this.requestorForm.value);
    } else {
      this.formUtils.markFormGroupTouched(this.requestorForm);
    }
  }

  // Public methods for wizard integration
  getFormData(): RequestorInformation {
    return this.requestorForm.value;
  }

  isValid(): boolean {
    return this.requestorForm.valid;
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.requestorForm);
  }
}
