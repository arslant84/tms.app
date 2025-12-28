/**
 * Transport Request Create Component
 * Redesigned to match React source (pctsb.syntra) exactly
 * NO cost fields - matches new backend structure
 */
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
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
  isEditMode = false;
  requestId: number | null = null;

  transportTypes: TransportType[] = ['Local', 'Intercity', 'Airport Transfer', 'Charter', 'Other'];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private transportService: TransportService,
    private toastService: ToastService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.initForm();

    // Check if we're in edit mode
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.requestId = +params['id'];
        this.loadRequestData(this.requestId);
      } else {
        this.loadUserDetails();
      }
    });
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
      const position = this.authService.getUserPosition(currentUser);


      this.transportForm.patchValue({
        requestorName: currentUser.name || currentUser.email || '',
        staffId: currentUser.staff_id || '',
        department: currentUser.department || '',
        position: position || ''
      });
    }
  }

  loadRequestData(id: number): void {
    this.loading = true;
    this.transportService.getRequestById(id).subscribe({
      next: (request) => {
        // Patch basic form fields
        this.transportForm.patchValue({
          requestorName: request.requestorName,
          staffId: request.staffId,
          department: request.department,
          position: request.position || '',
          purpose: request.purpose,
          tsrReference: request.tsrReference || '',
          additionalComments: request.additionalComments || '',
          confirmPolicy: true,
          confirmManagerApproval: true,
          confirmTermsAndConditions: true
        });

        // Clear default transport detail and load existing ones
        this.transportDetails.clear();
        if (request.transportDetails && request.transportDetails.length > 0) {
          request.transportDetails.forEach((detail: any) => {
            const detailGroup = this.fb.group({
              date: [detail.date, Validators.required],
              day: [detail.day || ''],
              from: [detail.from, Validators.required],
              to: [detail.to, Validators.required],
              departureTime: [detail.departureTime, Validators.required],
              transportType: [detail.transportType || 'Local', Validators.required],
              numberOfPassengers: [detail.numberOfPassengers || 1, [Validators.required, Validators.min(1)]]
            });
            this.transportDetails.push(detailGroup);
          });
        } else {
          // If no transport details, add one default
          this.addTransportDetail();
        }

        this.loading = false;
      },
      error: (error) => {
        this.toastService.error('Failed to load transport request');
        this.loading = false;
        this.router.navigate(['/transport']);
      }
    });
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
      status: 'Pending' // Let workflow system determine actual status
    };

    const backendData = toBackendFormat(formData);

    const saveOperation = this.isEditMode && this.requestId
      ? this.transportService.updateRequest(this.requestId, backendData)
      : this.transportService.createRequest(backendData);

    saveOperation.subscribe({
      next: (response) => {
        this.submitting = false;
        const message = this.isEditMode
          ? 'Transport request updated successfully'
          : 'Transport request submitted successfully and sent for approval';
        this.toastService.success(message);
        // Redirect to transport list instead of detail page to avoid loading issues
        this.router.navigate(['/transport']);
      },
      error: (err) => {
        this.submitting = false;
        const errorMessage = err.error?.message || err.error?.detail || err.message || 'Failed to create transport request';
        this.toastService.error(errorMessage);
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

    const saveOperation = this.isEditMode && this.requestId
      ? this.transportService.updateRequest(this.requestId, backendData)
      : this.transportService.createRequest(backendData);

    saveOperation.subscribe({
      next: () => {
        this.submitting = false;
        this.toastService.success('Draft saved successfully');
        this.router.navigate(['/transport']);
      },
      error: (err) => {
        this.submitting = false;
        const errorMessage = err.error?.message || err.error?.detail || err.message || 'Failed to save draft';
        this.toastService.error(errorMessage);
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
