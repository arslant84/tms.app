import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AccommodationService } from '../../services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';

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
    private toastService: ToastService,
    private confirmationService: ConfirmationService
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
      requestorName: ['', Validators.required],
      requestorId: [''],
      requestorGender: ['', Validators.required],
      department: [''],
      location: ['', Validators.required],
      trfId: [''],
      requestedCheckInDate: ['', Validators.required],
      requestedCheckOutDate: ['', Validators.required],
      requestedRoomType: [''],
      flightArrivalTime: [''],
      flightDepartureTime: [''],
      specialRequests: ['']
    });
  }

  loadRequestData(id: number): void {
    this.loading = true;
    this.accommodationService.getRequestById(id).subscribe({
      next: (request: any) => {
        this.accommodationForm.patchValue({
          requestorName: request.requestor_name,
          requestorId: request.staff_id,
          requestorGender: request.requestor_gender || request.additional_data?.requestor_gender,
          department: request.department,
          location: request.location || request.additional_data?.location,
          trfId: request.trf,
          requestedCheckInDate: request.requested_check_in_date || request.additional_data?.requested_check_in_date,
          requestedCheckOutDate: request.requested_check_out_date || request.additional_data?.requested_check_out_date,
          requestedRoomType: request.requested_room_type || request.additional_data?.requested_room_type,
          flightArrivalTime: request.flight_arrival_time || request.additional_data?.flight_arrival_time,
          flightDepartureTime: request.flight_departure_time || request.additional_data?.flight_departure_time,
          specialRequests: request.special_requests || request.additional_data?.special_requests
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
    // Set status to Pending to trigger workflow on submit
    formData.status = 'Pending';

    const saveOperation = this.isEditMode && this.requestId
      ? this.accommodationService.updateRequest(this.requestId, formData)
      : this.accommodationService.createRequest(formData);

    saveOperation.subscribe({
      next: (response) => {
        this.submitting = false;
        const message = this.isEditMode
          ? 'Accommodation request updated and submitted successfully'
          : 'Accommodation request created and submitted successfully';
        this.toastService.success(message);
        // Redirect to detail page to see workflow status
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
    // Explicitly set status to Draft - workflow will not be triggered
    formData.status = 'Draft';

    const saveOperation = this.isEditMode && this.requestId
      ? this.accommodationService.updateRequest(this.requestId, formData)
      : this.accommodationService.createRequest(formData);

    saveOperation.subscribe({
      next: (response) => {
        this.submitting = false;
        this.toastService.success('Draft saved successfully');
        // Redirect to detail page to view the draft
        this.router.navigate(['/accommodation', response.id]);
      },
      error: (err) => {
        this.submitting = false;
        this.toastService.error('Failed to save draft');
        console.error('Error saving draft:', err);
      }
    });
  }

  onCancel(): void {
    this.confirmationService.confirmCancel().subscribe(confirmed => {
      if (confirmed) {
        this.router.navigate(['/accommodation']);
      }
    });
  }

  prepareFormData(): any {
    const formValue = this.accommodationForm.value;

    return {
      requestor_name: formValue.requestorName,
      staff_id: formValue.requestorId,
      requestor_gender: formValue.requestorGender,
      department: formValue.department,
      location: formValue.location,
      trf: formValue.trfId ? parseInt(formValue.trfId) : null,
      requested_check_in_date: formValue.requestedCheckInDate,
      requested_check_out_date: formValue.requestedCheckOutDate,
      requested_room_type: formValue.requestedRoomType,
      flight_arrival_time: formValue.flightArrivalTime,
      flight_departure_time: formValue.flightDepartureTime,
      special_requests: formValue.specialRequests,
      additional_data: {
        requestor_gender: formValue.requestorGender,
        location: formValue.location,
        requested_check_in_date: formValue.requestedCheckInDate,
        requested_check_out_date: formValue.requestedCheckOutDate,
        requested_room_type: formValue.requestedRoomType,
        flight_arrival_time: formValue.flightArrivalTime,
        flight_departure_time: formValue.flightDepartureTime,
        special_requests: formValue.specialRequests
      }
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
