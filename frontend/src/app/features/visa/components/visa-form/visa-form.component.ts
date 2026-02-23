import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { VisaService, VisaApplication } from '../../services/visa.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { UserFormHelperService } from '../../../../core/utils/user-form-helper.service';

@Component({
  selector: 'app-visa-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './visa-form.component.html',
  styleUrl: './visa-form.component.scss'
})
export class VisaFormComponent implements OnInit {
  visaForm!: FormGroup;
  isEditMode = false;
  applicationId: number | null = null;
  isLoading = false;
  isSubmitting = false;

  // Passport file upload properties
  passportFile: File | null = null;
  passportFileName: string | null = null;
  passportFileUrl: string | null = null;
  passportFileError: string | null = null;

  visaTypes = ['Tourist', 'Business', 'Work', 'Student', 'Transit', 'Diplomatic', 'Official', 'Other'];
  entryTypes = ['Single Entry', 'Multiple Entry', 'Transit'];
  maritalStatuses = ['Single', 'Married', 'Divorced', 'Widowed'];

  // Field labels for better error messages
  fieldLabels: { [key: string]: string } = {
    requestor_name: 'Full Name',
    staff_id: 'Staff ID',
    department: 'Department',
    position: 'Position',
    email: 'Email',
    destination: 'Destination',
    travel_purpose: 'Travel Purpose',
    visa_type: 'Visa Type',
    trip_start_date: 'Trip Start Date',
    trip_end_date: 'Trip End Date',
    passport_number: 'Passport Number',
    passport_expiry_date: 'Passport Expiry Date',
    passport_place_of_issuance: 'Passport Place of Issuance',
    passport_date_of_issuance: 'Passport Date of Issuance',
    date_of_birth: 'Date of Birth',
    place_of_birth: 'Place of Birth',
    citizenship: 'Citizenship',
    contact_telephone: 'Contact Telephone',
    home_address: 'Home Address',
    marital_status: 'Marital Status',
    request_type: 'Request Type',
    visa_entry_type: 'Visa Entry Type',
    approximately_arrival_date: 'Approximate Arrival Date',
    duration_of_stay: 'Duration of Stay',
    trf_reference_number: 'TRF Reference Number',
    status: 'Status'
  };

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private visaService: VisaService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private formUtils: FormUtilsService,
    private userFormHelper: UserFormHelperService
  ) {}

  ngOnInit(): void {
    this.initForm();

    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.applicationId = +params['id'];
        this.loadApplication();
      } else {
        // Only auto-populate in create mode
        this.populateUserDetails();
      }
    });
  }

  private populateUserDetails(): void {
    // Auto-populate user details using helper service
    const userDefaults = this.userFormHelper.getUserFormDefaults();

    this.visaForm.patchValue({
      requestor_name: userDefaults.fullName,
      staff_id: userDefaults.staffId,
      department: userDefaults.department,
      position: userDefaults.position,
      email: userDefaults.email,
      contact_telephone: userDefaults.phone
    });
  }

  initForm(): void {
    this.visaForm = this.fb.group({
      // Personal Information
      requestor_name: ['', Validators.required],
      email: ['', [Validators.email]],
      staff_id: [''],
      department: [''],
      position: [''],
      contact_telephone: [''],
      home_address: [''],

      // Travel Details
      destination: ['', Validators.required],
      travel_purpose: ['', Validators.required],
      trip_start_date: [''],
      trip_end_date: [''],
      approximately_arrival_date: [''],
      duration_of_stay: [''],
      itinerary_details: [''],
      trf_reference_number: [''],

      // Visa Information
      visa_type: ['', Validators.required],
      visa_entry_type: [''],
      work_visit_category: [''],
      request_type: ['VISA'],

      // Passport Details
      passport_number: [''],
      passport_expiry_date: [''],
      passport_place_of_issuance: [''],
      passport_date_of_issuance: [''],
      date_of_birth: [''],
      place_of_birth: [''],
      citizenship: [''],
      marital_status: [''],

      // Family & Education
      family_information: [''],
      education_details: [''],

      // Employment
      current_employer_name: [''],
      current_employer_address: [''],

      // Cost Information
      application_fees_borne_by: [''],
      cost_centre_number: [''],

      // Additional
      additional_comments: [''],
      supporting_documents_notes: ['']
    });
  }

  loadApplication(): void {
    if (!this.applicationId) return;

    this.isLoading = true;
    this.visaService.getApplicationById(this.applicationId).subscribe({
      next: (application: any) => {
        // Check if application can be edited based on status
        // Allow editing for Draft, Rejected, Submitted, or any Pending status
        const status = application.status || '';
        const canEdit = status === 'Draft' ||
                        status === 'Rejected' ||
                        status === 'Submitted' ||
                        status.startsWith('Pending');

        if (status && !canEdit) {
          const errorMsg = `This visa application cannot be edited because its status is "${status}". Completed, Approved, Processing, and Cancelled applications cannot be modified.`;
          this.isLoading = false;

          // Show error toast and redirect back to list
          this.toastService.error(errorMsg);
          setTimeout(() => {
            this.router.navigate(['/visa']);
          }, 3000);
          return;
        }

        this.visaForm.patchValue(application);
        // Load passport file info if exists
        if (application.passport_file_url) {
          this.passportFileUrl = application.passport_file_url;
          // Extract filename from URL
          const urlParts = application.passport_file_url.split('/');
          this.passportFileName = urlParts[urlParts.length - 1];
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.toastService.error('Failed to load visa application');
        this.isLoading = false;
      }
    });
  }

  onSubmit(): void {
    if (this.visaForm.invalid) {
      const invalidFields = this.formUtils.markFormGroupTouched(this.visaForm, true);

      // Build error message with field names
      if (invalidFields.length > 0) {
        const fieldList = invalidFields.map(field => this.fieldLabels[field] || field).join(', ');
        this.toastService.error(
          `Please fill in the following required fields: ${fieldList}`,
          true,
          8000
        );
      } else {
        this.toastService.error('Please fill in all required fields', true, 5000);
      }

      // Scroll to first invalid field
      this.scrollToFirstInvalidField();
      return;
    }

    this.isSubmitting = true;
    const formData = this.prepareFormData();
    formData.status = 'Pending';

    const saveOperation = this.isEditMode && this.applicationId
      ? this.visaService.updateApplication(this.applicationId, formData)
      : this.visaService.createApplication(formData);

    saveOperation.subscribe({
      next: (response: any) => {
        const savedId = response.id || this.applicationId;
        // Upload passport file if one was selected
        if (this.passportFile && savedId) {
          this.uploadPassportFileToServer(savedId);
        }
        this.toastService.success(`Visa application ${this.isEditMode ? 'updated' : 'submitted'} successfully`);
        this.router.navigate(['/visa']);
      },
      error: (error) => {

        // Handle validation errors from backend
        if (error.status === 400 && error.error) {
          const errors = error.error;
          let errorMessage = 'Validation Error: ';

          // Check if errors is an object with field-specific errors
          if (typeof errors === 'object' && !Array.isArray(errors)) {
            const errorMessages: string[] = [];

            Object.keys(errors).forEach(field => {
              const fieldError = Array.isArray(errors[field]) ? errors[field][0] : errors[field];
              const fieldLabel = this.fieldLabels[field] || field.replace(/_/g, ' ');
              errorMessages.push(`${fieldLabel}: ${fieldError}`);
            });

            if (errorMessages.length > 0) {
              errorMessage = errorMessages.join('; ');
            }
          } else if (typeof errors === 'string') {
            errorMessage = errors;
          } else if (errors.detail) {
            errorMessage = errors.detail;
          } else if (errors.message) {
            errorMessage = errors.message;
          }

          this.toastService.error(errorMessage, true, 10000);
        } else {
          const errorMsg = error?.error?.message || error?.message || 'Failed to save visa application';
          this.toastService.error(errorMsg);
        }

        this.isSubmitting = false;
      }
    });
  }

  onSaveDraft(): void {
    this.isSubmitting = true;
    const formData = this.prepareFormData();
    formData.status = 'Draft';

    const saveOperation = this.isEditMode && this.applicationId
      ? this.visaService.updateApplication(this.applicationId, formData)
      : this.visaService.createApplication(formData);

    saveOperation.subscribe({
      next: (response: any) => {
        const savedId = response.id || this.applicationId;
        // Upload passport file if one was selected
        if (this.passportFile && savedId) {
          this.uploadPassportFileToServer(savedId);
        }
        this.toastService.success('Visa application saved as draft successfully');
        this.router.navigate(['/visa']);
      },
      error: (error) => {

        // Handle validation errors from backend
        if (error.status === 400 && error.error) {
          const errors = error.error;
          let errorMessage = 'Validation Error: ';

          // Check if errors is an object with field-specific errors
          if (typeof errors === 'object' && !Array.isArray(errors)) {
            const errorMessages: string[] = [];

            Object.keys(errors).forEach(field => {
              const fieldError = Array.isArray(errors[field]) ? errors[field][0] : errors[field];
              const fieldLabel = this.fieldLabels[field] || field.replace(/_/g, ' ');
              errorMessages.push(`${fieldLabel}: ${fieldError}`);
            });

            if (errorMessages.length > 0) {
              errorMessage = errorMessages.join('; ');
            }
          } else if (typeof errors === 'string') {
            errorMessage = errors;
          } else if (errors.detail) {
            errorMessage = errors.detail;
          } else if (errors.message) {
            errorMessage = errors.message;
          }

          this.toastService.error(errorMessage, true, 10000);
        } else {
          const errorMsg = error?.error?.message || error?.message || 'Failed to save draft';
          this.toastService.error(errorMsg);
        }

        this.isSubmitting = false;
      }
    });
  }

  onCancel(): void {
    this.confirmationService.confirmCancel('Are you sure you want to cancel? All unsaved changes will be lost.').subscribe(confirmed => {
      if (confirmed) {
        this.router.navigate(['/visa']);
      }
    });
  }

  prepareFormData(): Partial<VisaApplication> {
    const formValue = this.visaForm.value;

    // List of date fields that should be null instead of empty strings
    const dateFields = [
      'trip_start_date', 'trip_end_date', 'passport_expiry_date',
      'passport_date_of_issuance', 'date_of_birth', 'approximately_arrival_date'
    ];

    // Convert empty strings to null for date fields
    dateFields.forEach(field => {
      if (formValue[field] === '' || formValue[field] === null || formValue[field] === undefined) {
        formValue[field] = null;
      }
    });

    // Also clean up other fields that might be empty strings but should be null
    Object.keys(formValue).forEach(key => {
      if (formValue[key] === '') {
        formValue[key] = null;
      }
    });

    return formValue;
  }


  scrollToFirstInvalidField(): void {
    // Find the first invalid control
    const firstInvalidControl = document.querySelector('.form-control.ng-invalid, .form-select.ng-invalid');

    if (firstInvalidControl) {
      // Scroll to the field with offset for header
      const yOffset = -100; // Offset for fixed header
      const element = firstInvalidControl as HTMLElement;
      const y = element.getBoundingClientRect().top + window.pageYOffset + yOffset;

      window.scrollTo({ top: y, behavior: 'smooth' });

      // Focus on the field after scroll
      setTimeout(() => {
        (firstInvalidControl as HTMLElement).focus();
      }, 300);
    }
  }

  isFieldInvalid(fieldName: string): boolean {
    const field = this.visaForm.get(fieldName);
    return !!(field && field.invalid && field.touched);
  }

  // Passport file handling methods
  onPassportFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    this.passportFileError = null;

    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      this.passportFileError = 'Invalid file type. Please upload PDF, JPG, or PNG.';
      input.value = '';
      return;
    }

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      this.passportFileError = 'File size must not exceed 10MB.';
      input.value = '';
      return;
    }

    this.passportFile = file;
    this.passportFileName = file.name;
    this.passportFileUrl = null; // Clear existing URL when new file is selected
  }

  removePassportFile(): void {
    // If we have an existing file on server and in edit mode, delete it
    if (this.passportFileUrl && this.applicationId) {
      this.visaService.deletePassportFile(this.applicationId).subscribe({
        next: () => {
          this.toastService.success('Passport file removed');
        },
        error: (error) => {
          this.toastService.error('Failed to remove passport file');
        }
      });
    }

    this.passportFile = null;
    this.passportFileName = null;
    this.passportFileUrl = null;
    this.passportFileError = null;
  }

  private uploadPassportFileToServer(applicationId: number): void {
    if (!this.passportFile) return;

    this.visaService.uploadPassportFile(applicationId, this.passportFile).subscribe({
      next: () => {
        // File uploaded successfully - no additional toast needed as form save toast is shown
      },
      error: (error) => {
        this.toastService.error('Failed to upload passport file');
      }
    });
  }
}
