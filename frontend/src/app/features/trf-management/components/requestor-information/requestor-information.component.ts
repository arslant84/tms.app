import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

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
export class RequestorInformationComponent implements OnInit {
  @Input() initialData: Partial<RequestorInformation> = {};
  @Output() formSubmit = new EventEmitter<RequestorInformation>();
  
  requestorForm!: FormGroup;

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initForm();
  }

  private initForm(): void {
    this.requestorForm = this.fb.group({
      fullName: [this.initialData.fullName || 'Jane Doe (Sample)', Validators.required],
      staffId: [this.initialData.staffId || 'S-12345', Validators.required],
      department: [this.initialData.department || 'Exploration Department / Geologist', Validators.required],
      position: [this.initialData.position || ''],
      costCenter: [this.initialData.costCenter || 'CC-EXPL-001', Validators.required],
      contactNo: [this.initialData.contactNo || 'Ext: 1234', Validators.required],
      email: [this.initialData.email || 'jane.doe@example.com', [Validators.required, Validators.email]]
    });
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
