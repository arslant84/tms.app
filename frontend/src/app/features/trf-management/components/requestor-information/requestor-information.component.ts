import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../../../core/services/auth.service';

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
    private authService: AuthService
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
    // Get current user data for auto-population
    const currentUser = this.authService.getCurrentUser();
    const position = this.authService.getUserPosition(currentUser);

    // Use initialData if provided (edit mode), otherwise use current user data (create mode)
    this.requestorForm = this.fb.group({
      fullName: [this.initialData.fullName || currentUser?.name || '', Validators.required],
      staffId: [this.initialData.staffId || currentUser?.staff_id || '', Validators.required],
      department: [this.initialData.department || currentUser?.department || '', Validators.required],
      position: [this.initialData.position || position || ''],
      costCenter: [this.initialData.costCenter || '', Validators.required],
      contactNo: [this.initialData.contactNo || currentUser?.phone || '', Validators.required],
      email: [this.initialData.email || currentUser?.email || '', [Validators.required, Validators.email]]
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
      this.markFormGroupTouched(this.requestorForm);
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
    this.markFormGroupTouched(this.requestorForm);
  }

  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();
      if (control instanceof FormGroup) {
        this.markFormGroupTouched(control);
      }
    });
  }
}
