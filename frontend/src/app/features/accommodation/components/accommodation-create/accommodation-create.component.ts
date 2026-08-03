import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AccommodationService } from '../../services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { TrfService } from '../../../trf-management/services/trf.service';
import { UserFormHelperService } from '../../../../core/utils/user-form-helper.service';
import { ApproverSelectionComponent, SkippedStepsSelection } from '../../../../shared/components/approver-selection/approver-selection.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { ApproverSelection } from '../../../../core/services/workflow.service';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';

@Component({
  selector: 'app-accommodation-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, ApproverSelectionComponent, LoadingSpinnerComponent],
  templateUrl: './accommodation-create.component.html',
  styleUrls: ['./accommodation-create.component.scss']
})
export class AccommodationCreateComponent implements OnInit {
  @ViewChild(ApproverSelectionComponent) approverSelectionComponent?: ApproverSelectionComponent;

  accommodationForm!: FormGroup;
  isEditMode = false;
  requestId: number | null = null;
  loading = false;
  submitting = false;

  // Approver selection properties
  selectedApprovers: ApproverSelection = {};
  skippedSteps: SkippedStepsSelection = {};
  approverSelectionValid: boolean = true;
  showApproverSelection: boolean = true;
  initialApproverSelections: ApproverSelection = {};
  initialSkippedSteps: SkippedStepsSelection = {};
  requesterStaffId?: string; // Original requestor's staff ID for department-based approver filtering

  // TRF/TSR selection
  availableTrfs: any[] = [];
  loadingTrfs = false;
  selectedTrfDetails: any = null;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private accommodationService: AccommodationService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private trfService: TrfService,
    private formUtils: FormUtilsService,
    private userFormHelper: UserFormHelperService,
    private errorHandler: HttpErrorHandlerService
  ) {}

  ngOnInit(): void {
    this.initForm();

    // Check if we're in edit mode
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.requestId = +params['id'];
        // Load TRFs first, then load request data in the callback
        this.loadAvailableTrfsAndRequestData(this.requestId);
      } else {
        // In create mode, just load TRFs and populate user details
        this.loadAvailableTrfs();
        this.populateUserDetails();
      }
    });
  }

  loadAvailableTrfs(): void {
    this.loadingTrfs = true;
    this.trfService.getAllTrfs({ page_size: 1000 }).subscribe({
      next: (response: any) => {
        // Handle both paginated and non-paginated responses
        const trfs = response.results || response;
        this.availableTrfs = Array.isArray(trfs) ? trfs : [];
        this.loadingTrfs = false;
      },
      error: (err) => {
        this.availableTrfs = [];
        this.loadingTrfs = false;
      }
    });
  }

  loadAvailableTrfsAndRequestData(requestId: number): void {
    this.loadingTrfs = true;
    this.trfService.getAllTrfs({ page_size: 1000 }).subscribe({
      next: (response: any) => {
        // Handle both paginated and non-paginated responses
        const trfs = response.results || response;
        this.availableTrfs = Array.isArray(trfs) ? trfs : [];
        this.loadingTrfs = false;
        // Now that TRFs are loaded, load the request data
        this.loadRequestData(requestId);
      },
      error: (err) => {
        this.availableTrfs = [];
        this.loadingTrfs = false;
        // Still try to load request data even if TRFs failed
        this.loadRequestData(requestId);
      }
    });
  }

  onTrfChange(event: any): void {
    const trfId = event.target.value;
    if (trfId) {
      this.selectedTrfDetails = this.availableTrfs.find(trf => trf.id === +trfId);

      // Check accommodation availability and auto-populate dates
      this.checkTsrAvailability(+trfId);
    } else {
      this.selectedTrfDetails = null;
      // Clear the date fields if TSR is deselected
      this.accommodationForm.patchValue({
        requestedCheckInDate: '',
        requestedCheckOutDate: ''
      });
    }
  }

  checkTsrAvailability(trfId: number): void {
    this.trfService.checkAccommodationAvailability(trfId).subscribe({
      next: (response: any) => {
        if (!response.is_available) {
          // TSR is already linked to another accommodation request
          const existingAccom = response.existing_accommodation;

          // Check if this is the current request being edited (in edit mode)
          const isCurrentRequest = this.isEditMode && existingAccom && this.requestId === existingAccom.id;

          if (!isCurrentRequest && existingAccom) {
            // Show warning only if it's linked to a DIFFERENT accommodation request
            this.toastService.warning(
              `This TSR (${response.tsr_request_number || 'Unknown'}) is already linked to accommodation request ${existingAccom.request_number || existingAccom.id} by ${existingAccom.requestor_name || 'Unknown'}. Please select a different TSR.`
            );

            // Clear the TSR selection
            this.accommodationForm.patchValue({
              trfId: ''
            });
            this.selectedTrfDetails = null;
          } else if (!isCurrentRequest && !existingAccom) {
            // TSR is not available but no existing accommodation info provided
            this.toastService.warning('This TSR is already linked to another accommodation request.');
            this.accommodationForm.patchValue({ trfId: '' });
            this.selectedTrfDetails = null;
          } else {
            // In edit mode, auto-populate dates from TSR even if it's already linked to this request
            if (response.date_range) {
              this.accommodationForm.patchValue({
                requestedCheckInDate: response.date_range.start_date,
                requestedCheckOutDate: response.date_range.end_date
              });
            }
          }
        } else {
          // TSR is available - auto-populate dates if available
          if (response.date_range) {
            this.accommodationForm.patchValue({
              requestedCheckInDate: response.date_range.start_date,
              requestedCheckOutDate: response.date_range.end_date
            });

            this.toastService.success(
              `Check-in and check-out dates have been auto-populated from TSR itinerary. You can adjust them within the TSR date range (${response.date_range.start_date} to ${response.date_range.end_date}).`
            );
          }
        }
      },
      error: (err) => {
        this.toastService.error('Failed to check TSR availability');
      }
    });
  }

  private populateUserDetails(): void {
    // Auto-populate user details using helper service
    const userDefaults = this.userFormHelper.getUserFormDefaults();
    this.accommodationForm.patchValue({
      requestorName: userDefaults.fullName,
      requestorId: userDefaults.staffId,
      department: userDefaults.department
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
        // Check if request can be edited based on status
        // Allow editing for Draft, Rejected, or any Pending status
        const status = request.status || '';
        const canEdit = status === 'Draft' ||
                        status === 'Rejected' ||
                        status.startsWith('Pending');

        if (status && !canEdit) {
          const errorMsg = `This accommodation request cannot be edited because its status is "${status}". Only Draft, Rejected, or Pending requests can be edited.`;
          this.loading = false;

          // Show error toast and redirect back to list
          this.toastService.error(errorMsg);
          setTimeout(() => {
            this.router.navigate(['/accommodation']);
          }, 3000);
          return;
        }

        const trfValue = request.trf || request.additional_data?.trf_id || request.additional_data?.trf;

        this.accommodationForm.patchValue({
          requestorName: request.requestor_name,
          requestorId: request.staff_id,
          requestorGender: request.requestor_gender || request.additional_data?.requestor_gender,
          department: request.department,
          location: request.location || request.additional_data?.location,
          trfId: trfValue,
          requestedCheckInDate: request.requested_check_in_date || request.additional_data?.requested_check_in_date,
          requestedCheckOutDate: request.requested_check_out_date || request.additional_data?.requested_check_out_date,
          requestedRoomType: request.requested_room_type || request.additional_data?.requested_room_type,
          flightArrivalTime: request.flight_arrival_time || request.additional_data?.flight_arrival_time,
          flightDepartureTime: request.flight_departure_time || request.additional_data?.flight_departure_time,
          specialRequests: request.special_requests || request.additional_data?.special_requests
        });

        // Set selected TRF details for display
        if (trfValue && this.availableTrfs.length > 0) {
          this.selectedTrfDetails = this.availableTrfs.find(trf => trf.id === +trfValue);
        }

        // Set the staff ID for proper department-based approver filtering
        // This ensures approvers are filtered by the original requester's department
        if (request.staff_id) {
          this.requesterStaffId = request.staff_id;
        }

        // Load saved approver selections for edit mode
        if (request.selected_approvers) {
          this.initialApproverSelections = request.selected_approvers;
          this.selectedApprovers = request.selected_approvers;
        }

        // Load saved skipped steps for edit mode
        if (request.skipped_steps) {
          this.initialSkippedSteps = request.skipped_steps;
          this.skippedSteps = request.skipped_steps;
        }

        this.loading = false;
      },
      error: (err) => {
        this.toastService.error('Failed to load request data');
        this.loading = false;
        this.router.navigate(['/accommodation']);
      }
    });
  }

  // Approver selection event handlers
  onApproverSelectionChange(selection: ApproverSelection): void {
    this.selectedApprovers = selection;
  }

  onApproverValidityChange(isValid: boolean): void {
    this.approverSelectionValid = isValid;
  }

  onSkippedStepsChange(skippedSteps: SkippedStepsSelection): void {
    this.skippedSteps = skippedSteps;
  }

  onSubmit(): void {
    if (this.accommodationForm.invalid) {
      this.formUtils.markFormGroupTouched(this.accommodationForm);
      this.toastService.warning('Please fill in all required fields');
      return;
    }

    this.submitting = true;
    const formData = this.prepareFormData();
    // Remove skipped_steps from formData - it will be sent via submit endpoint
    const skippedStepsForSubmit = this.skippedSteps;
    const selectedApproversForSubmit = this.selectedApprovers;
    delete formData.skipped_steps;
    delete formData.selected_approvers;
    // Save as draft first, then submit to properly trigger workflow
    formData.status = 'Draft';

    const saveOperation = this.isEditMode && this.requestId
      ? this.accommodationService.updateRequest(this.requestId, formData)
      : this.accommodationService.createRequest(formData);

    saveOperation.subscribe({
      next: (response) => {
        // Now submit for approval with approver selections
        this.accommodationService.submitRequest(response.id, selectedApproversForSubmit, skippedStepsForSubmit).subscribe({
          next: () => {
            this.submitting = false;
            this.toastService.success('Accommodation request submitted successfully');
            // Redirect to detail page to see workflow status
            this.router.navigate(['/accommodation', response.id]);
          },
          error: (submitErr) => {
            this.submitting = false;
            this.toastService.error(submitErr.error?.error || 'Failed to submit accommodation request');
          }
        });
      },
      error: (err) => {
        this.submitting = false;
        const action = this.isEditMode ? 'update' : 'create';
        this.toastService.error(this.errorHandler.getErrorMessage(err, `Failed to ${action} request`));
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

    const data: any = {
      requestor_name: formValue.requestorName,
      staff_id: formValue.requestorId,
      department: formValue.department,
      trf: formValue.trfId ? parseInt(formValue.trfId) : null,
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

    // Include selected approvers if any were selected
    if (Object.keys(this.selectedApprovers).length > 0) {
      data.selected_approvers = this.selectedApprovers;
    }

    // Include skipped steps if any were skipped
    if (Object.keys(this.skippedSteps).length > 0) {
      data.skipped_steps = this.skippedSteps;
    }

    return data;
  }
}
