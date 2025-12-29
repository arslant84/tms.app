import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { VisaService, VisaApplication } from '../visa.service';
import { ToastService } from '../../core/services/toast.service';
import { AuthService } from '../../core/services/auth.service';
import { FormUtilsService } from '../../core/utils/form-utils.service';

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
    private authService: AuthService,
    private formUtils: FormUtilsService
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
    const currentUser = this.authService.getCurrentUser();
    if (currentUser) {
      const position = this.authService.getUserPosition(currentUser);

      // Auto-populate user details from logged-in user

      this.visaForm.patchValue({
        requestor_name: currentUser.name || '',
        staff_id: currentUser.staff_id || '',
        department: currentUser.department || '',
        position: position || '',
        email: currentUser.email || '',
        contact_telephone: currentUser.phone || ''
      });
    }
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
      next: (application) => {
        this.visaForm.patchValue(application);
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
      next: () => {
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
      next: () => {
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
    if (confirm('Are you sure you want to cancel? All unsaved changes will be lost.')) {
      this.router.navigate(['/visa']);
    }
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
}
