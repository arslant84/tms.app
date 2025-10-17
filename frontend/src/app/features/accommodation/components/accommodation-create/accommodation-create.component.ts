import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AccommodationService } from '../../services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-accommodation-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './accommodation-create.component.html',
  styleUrls: ['./accommodation-create.component.scss']
})
export class AccommodationCreateComponent implements OnInit {
  accommodationForm!: FormGroup;
  isEditMode = false;
  requestId: number | null = null;
  loading = false;
  submitting = false;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private accommodationService: AccommodationService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.initForm();

    // Check if we're in edit mode
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.requestId = +params['id'];
        this.loadRequestData(this.requestId);
      }
    });
  }

  initForm(): void {
    this.accommodationForm = this.fb.group({
      requestor_name: ['', Validators.required],
      staff_id: [''],
      department: [''],
      position: [''],
      cost_center: [''],
      tel_email: [''],
      email: ['', Validators.email],
      estimated_cost: [0],
      additional_comments: ['']
    });
  }

  loadRequestData(id: number): void {
    this.loading = true;
    this.accommodationService.getRequestById(id).subscribe({
      next: (request) => {
        this.accommodationForm.patchValue({
          requestor_name: request.requestor_name,
          staff_id: request.staff_id,
          department: request.department,
          position: request.position,
          cost_center: request.cost_center,
          tel_email: request.tel_email,
          email: request.email,
          estimated_cost: request.estimated_cost,
          additional_comments: request.additional_comments
        });
        this.loading = false;
      },
      error: (err) => {
        this.toastService.error('Failed to load request data');
        this.loading = false;
        console.error('Error loading request:', err);
        this.router.navigate(['/accommodation']);
      }
    });
  }

  onSubmit(): void {
    if (this.accommodationForm.invalid) {
      this.markFormGroupTouched(this.accommodationForm);
      this.toastService.warning('Please fill in all required fields');
      return;
    }

    this.submitting = true;
    const formData = this.prepareFormData();
    formData.status = 'Pending'; // Set status to Pending on submit

    const saveOperation = this.isEditMode && this.requestId
      ? this.accommodationService.updateRequest(this.requestId, formData)
      : this.accommodationService.createRequest(formData);

    saveOperation.subscribe({
      next: (response) => {
        this.submitting = false;
        const message = this.isEditMode
          ? 'Accommodation request updated successfully'
          : 'Accommodation request created successfully';
        this.toastService.success(message);
        this.router.navigate(['/accommodation', response.id]);
      },
      error: (err) => {
        this.submitting = false;
        const action = this.isEditMode ? 'update' : 'create';
        this.toastService.error(`Failed to ${action} request`);
        console.error(`Error ${action}ing request:`, err);
      }
    });
  }

  onSaveDraft(): void {
    this.submitting = true;
    const formData = this.prepareFormData();
    formData.status = 'Draft';

    const saveOperation = this.isEditMode && this.requestId
      ? this.accommodationService.updateRequest(this.requestId, formData)
      : this.accommodationService.createRequest(formData);

    saveOperation.subscribe({
      next: () => {
        this.submitting = false;
        this.toastService.success('Draft saved successfully');
        this.router.navigate(['/accommodation']);
      },
      error: (err) => {
        this.submitting = false;
        this.toastService.error('Failed to save draft');
        console.error('Error saving draft:', err);
      }
    });
  }

  onCancel(): void {
    if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
      this.router.navigate(['/accommodation']);
    }
  }

  prepareFormData(): any {
    const formValue = this.accommodationForm.value;

    return {
      requestor_name: formValue.requestor_name,
      staff_id: formValue.staff_id,
      department: formValue.department,
      position: formValue.position,
      cost_center: formValue.cost_center,
      tel_email: formValue.tel_email,
      email: formValue.email,
      estimated_cost: parseFloat(formValue.estimated_cost || 0),
      additional_comments: formValue.additional_comments
    };
  }

  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();

      if ((control as FormGroup).controls) {
        this.markFormGroupTouched(control as FormGroup);
      }
    });
  }
}
