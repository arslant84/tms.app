import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TransportService } from '../../services/transport.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-transport-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './transport-create.component.html',
  styleUrls: ['./transport-create.component.scss']
})
export class TransportCreateComponent implements OnInit {
  transportForm!: FormGroup;
  isEditMode = false;
  requestId: number | null = null;
  loading = false;
  submitting = false;

  transportTypes = ['Company Vehicle', 'Hired Vehicle', 'Personal Vehicle', 'Public Transport'];

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private transportService: TransportService,
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
    this.transportForm = this.fb.group({
      title: ['', Validators.required],
      purpose: ['', Validators.required],
      transport_type: ['', Validators.required],
      number_of_passengers: [1, [Validators.required, Validators.min(1)]],
      passenger_names: [''],
      vehicle_type: [''],
      special_requirements: [''],
      estimated_cost: [0],
      currency: ['USD'],
      additional_comments: [''],
      segments: this.fb.array([this.createSegment()])
    });
  }

  createSegment(): FormGroup {
    return this.fb.group({
      from_location: ['', Validators.required],
      to_location: ['', Validators.required],
      departure_date: ['', Validators.required],
      departure_time: ['', Validators.required],
      arrival_date: [''],
      arrival_time: [''],
      distance_km: [0],
      estimated_duration_hours: [0],
      route_description: [''],
      segment_cost: [0],
      remarks: ['']
    });
  }

  get segments(): FormArray {
    return this.transportForm.get('segments') as FormArray;
  }

  addSegment(): void {
    this.segments.push(this.createSegment());
  }

  removeSegment(index: number): void {
    if (this.segments.length > 1) {
      this.segments.removeAt(index);
    }
  }

  loadRequestData(id: number): void {
    this.loading = true;
    this.transportService.getRequestById(id).subscribe({
      next: (request) => {
        this.transportForm.patchValue({
          title: request.title,
          purpose: request.purpose,
          transport_type: request.transport_type,
          number_of_passengers: request.number_of_passengers,
          passenger_names: request.passenger_names,
          vehicle_type: request.vehicle_type,
          special_requirements: request.special_requirements,
          estimated_cost: request.estimated_cost,
          currency: request.currency,
          additional_comments: request.additional_comments
        });

        // Load segments
        if (request.segments && request.segments.length > 0) {
          this.segments.clear();
          request.segments.forEach(segment => {
            this.segments.push(this.fb.group({
              from_location: [segment.from_location],
              to_location: [segment.to_location],
              departure_date: [segment.departure_date],
              departure_time: [segment.departure_time],
              arrival_date: [segment.arrival_date],
              arrival_time: [segment.arrival_time],
              distance_km: [segment.distance_km],
              estimated_duration_hours: [segment.estimated_duration_hours],
              route_description: [segment.route_description],
              segment_cost: [segment.segment_cost],
              remarks: [segment.remarks]
            }));
          });
        }

        this.loading = false;
      },
      error: (err) => {
        this.toastService.error('Failed to load request data: ' + (err.error?.message || err.message));
        this.loading = false;
        console.error('Error loading request:', err);
      }
    });
  }

  onSubmit(): void {
    if (this.transportForm.invalid) {
      this.markFormGroupTouched(this.transportForm);
      this.toastService.warning('Please fill in all required fields');
      return;
    }

    this.submitting = true;
    const formData = this.prepareFormData();
    formData.status = 'Pending'; // Set status to Pending on submit

    const saveOperation = this.isEditMode && this.requestId
      ? this.transportService.updateRequest(this.requestId, formData)
      : this.transportService.createRequest(formData);

    saveOperation.subscribe({
      next: (response) => {
        this.submitting = false;
        const message = this.isEditMode ? 'Transport request updated successfully' : 'Transport request created successfully';
        this.toastService.success(message);
        this.router.navigate(['/transport', response.id]);
      },
      error: (err) => {
        this.submitting = false;
        const action = this.isEditMode ? 'update' : 'create';
        this.toastService.error(`Failed to ${action} request: ` + (err.error?.message || err.message));
        console.error(`Error ${action}ing request:`, err);
      }
    });
  }

  onSaveDraft(): void {
    this.submitting = true;
    const formData = this.prepareFormData();
    formData.status = 'Draft';

    const saveOperation = this.isEditMode && this.requestId
      ? this.transportService.updateRequest(this.requestId, formData)
      : this.transportService.createRequest(formData);

    saveOperation.subscribe({
      next: () => {
        this.submitting = false;
        this.toastService.success('Draft saved successfully');
        this.router.navigate(['/transport']);
      },
      error: (err) => {
        this.submitting = false;
        this.toastService.error('Failed to save draft: ' + (err.error?.message || err.message));
        console.error('Error saving draft:', err);
      }
    });
  }

  onCancel(): void {
    if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
      this.router.navigate(['/transport']);
    }
  }

  prepareFormData(): any {
    const formValue = this.transportForm.value;

    return {
      title: formValue.title,
      purpose: formValue.purpose,
      transport_type: formValue.transport_type,
      number_of_passengers: parseInt(formValue.number_of_passengers),
      passenger_names: formValue.passenger_names,
      vehicle_type: formValue.vehicle_type,
      special_requirements: formValue.special_requirements,
      estimated_cost: parseFloat(formValue.estimated_cost || 0),
      currency: formValue.currency,
      additional_comments: formValue.additional_comments,
      segments: formValue.segments.map((segment: any) => ({
        from_location: segment.from_location,
        to_location: segment.to_location,
        departure_date: segment.departure_date,
        departure_time: segment.departure_time,
        arrival_date: segment.arrival_date,
        arrival_time: segment.arrival_time,
        distance_km: parseFloat(segment.distance_km || 0),
        estimated_duration_hours: parseFloat(segment.estimated_duration_hours || 0),
        route_description: segment.route_description,
        segment_cost: parseFloat(segment.segment_cost || 0),
        remarks: segment.remarks
      }))
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
