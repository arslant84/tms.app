/**
 * Transport Request Create Component
 * Redesigned to match React source (pctsb.syntra) exactly
 * NO cost fields - matches new backend structure
 */
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TransportService } from '../../services/transport.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AuthService } from '../../../../core/services/auth.service';
import { TransportRequestForm, TransportDetail, TransportType, toBackendFormat } from '../../models/transport.model';

@Component({
  selector: 'app-transport-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './transport-create.component.html',
  styleUrls: ['./transport-create.component.scss']
})
export class TransportCreateComponent implements OnInit {
  transportForm!: FormGroup;
  loading = false;
  submitting = false;

  transportTypes: TransportType[] = ['Local', 'Intercity', 'Airport Transfer', 'Charter', 'Other'];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private transportService: TransportService,
    private toastService: ToastService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.initForm();
    this.loadUserDetails();
  }

  initForm(): void {
    this.transportForm = this.fb.group({
      // Requestor information
      requestorName: ['', Validators.required],
      staffId: ['', Validators.required],
      department: ['', Validators.required],
      position: [''],

      // Request details
      purpose: ['', Validators.required],
      tsrReference: [''],

      // Transport details array
      transportDetails: this.fb.array([], Validators.required),

      // Submission data
      additionalComments: [''],
      confirmPolicy: [false, Validators.requiredTrue],
      confirmManagerApproval: [false, Validators.requiredTrue],
      confirmTermsAndConditions: [false]
    });

    // Add first transport detail by default
    this.addTransportDetail();
  }

  loadUserDetails(): void {
    const currentUser = this.authService.getCurrentUser();
    if (currentUser) {
      this.transportForm.patchValue({
        requestorName: currentUser.name || currentUser.email || '',
        staffId: currentUser.staff_id || currentUser.staff_no || '',
        department: currentUser.department || '',
        position: '' // Position not available in User model
      });
    }
  }

  get transportDetails(): FormArray {
    return this.transportForm.get('transportDetails') as FormArray;
  }

  createTransportDetail(): FormGroup {
    return this.fb.group({
      date: [null, Validators.required],
      day: [''],
      from: ['', Validators.required],
      to: ['', Validators.required],
      departureTime: ['', Validators.required],
      transportType: ['Local', Validators.required],
      numberOfPassengers: [1, [Validators.required, Validators.min(1)]]
    });
  }

  addTransportDetail(): void {
    this.transportDetails.push(this.createTransportDetail());
  }

  removeTransportDetail(index: number): void {
    if (this.transportDetails.length > 1) {
      this.transportDetails.removeAt(index);
    } else {
      this.toastService.warning('At least one transport detail is required');
    }
  }

  onDateChange(index: number, event: any): void {
    const date = event.target.value;
    if (date) {
      const dateObj = new Date(date);
      const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
      this.transportDetails.at(index).patchValue({ day: dayName });
    }
  }

  onSubmit(): void {
    if (this.transportForm.invalid) {
      this.markFormGroupTouched(this.transportForm);
      this.toastService.warning('Please fill in all required fields and confirm all checkboxes');
      return;
    }

    this.submitting = true;
    const formData: Partial<TransportRequestForm> = {
      ...this.transportForm.value,
      status: 'Pending Department Focal' // Submit directly to workflow
    };

    const backendData = toBackendFormat(formData);
    console.log('📤 Sending to backend:', JSON.stringify(backendData, null, 2));

    this.transportService.createRequest(backendData).subscribe({
      next: (response) => {
        this.submitting = false;
        this.toastService.success('Transport request submitted successfully');
        this.router.navigate(['/transport', response.id]);
      },
      error: (err) => {
        this.submitting = false;
        console.error('❌ Full error:', err);
        console.error('❌ Error details:', JSON.stringify(err.error, null, 2));
        const errorMessage = err.error?.message || err.error?.detail || err.message || 'Failed to create transport request';
        this.toastService.error(errorMessage);
        console.error('Error creating transport request:', err);
      }
    });
  }

  onSaveDraft(): void {
    if (!this.transportForm.get('purpose')?.value || this.transportDetails.length === 0) {
      this.toastService.warning('Please provide at least a purpose and one transport detail to save as draft');
      return;
    }

    this.submitting = true;
    const formData: Partial<TransportRequestForm> = {
      ...this.transportForm.value,
      status: 'Draft'
    };

    const backendData = toBackendFormat(formData);

    this.transportService.createRequest(backendData).subscribe({
      next: () => {
        this.submitting = false;
        this.toastService.success('Draft saved successfully');
        this.router.navigate(['/transport']);
      },
      error: (err) => {
        this.submitting = false;
        const errorMessage = err.error?.message || err.error?.detail || err.message || 'Failed to save draft';
        this.toastService.error(errorMessage);
        console.error('Error saving draft:', err);
      }
    });
  }

  onCancel(): void {
    if (confirm('Are you sure you want to cancel? All unsaved changes will be lost.')) {
      this.router.navigate(['/transport']);
    }
  }

  private markFormGroupTouched(formGroup: FormGroup | FormArray): void {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      control?.markAsTouched();

      if (control instanceof FormGroup || control instanceof FormArray) {
        this.markFormGroupTouched(control);
      }
    });
  }

  // Helper methods for template
  isFieldInvalid(fieldName: string): boolean {
    const field = this.transportForm.get(fieldName);
    return !!(field && field.invalid && field.touched);
  }

  isDetailFieldInvalid(detailIndex: number, fieldName: string): boolean {
    const field = this.transportDetails.at(detailIndex)?.get(fieldName);
    return !!(field && field.invalid && field.touched);
  }
}
