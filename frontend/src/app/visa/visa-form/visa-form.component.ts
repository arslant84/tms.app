import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { VisaService, VisaApplication } from '../visa.service';

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

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private visaService: VisaService
  ) {}

  ngOnInit(): void {
    this.initForm();

    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.applicationId = +params['id'];
        this.loadApplication();
      }
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

      // Approval Information
      line_focal_person: [''],
      line_focal_dept: [''],
      line_focal_contact: [''],
      line_focal_date: [''],
      sponsoring_dept_head: [''],
      sponsoring_dept_head_dept: [''],
      sponsoring_dept_head_contact: [''],
      sponsoring_dept_head_date: [''],
      ceo_approval_name: [''],
      ceo_approval_date: [''],

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
        console.error('Error loading visa application:', error);
        alert('Failed to load visa application');
        this.isLoading = false;
      }
    });
  }

  onSubmit(): void {
    if (this.visaForm.invalid) {
      this.markFormGroupTouched(this.visaForm);
      alert('Please fill in all required fields');
      return;
    }

    this.isSubmitting = true;
    const formData = this.prepareFormData();
    formData.status = 'Submitted';

    const saveOperation = this.isEditMode && this.applicationId
      ? this.visaService.updateApplication(this.applicationId, formData)
      : this.visaService.createApplication(formData);

    saveOperation.subscribe({
      next: () => {
        alert(`Visa application ${this.isEditMode ? 'updated' : 'submitted'} successfully`);
        this.router.navigate(['/visa']);
      },
      error: (error) => {
        console.error('Error saving visa application:', error);
        alert('Failed to save visa application');
        this.isSubmitting = false;
      }
    });
  }

  onSaveDraft(): void {
    this.isSubmitting = true;
    const formData = this.prepareFormData();
    formData.status = 'Pending Department Focal';

    const saveOperation = this.isEditMode && this.applicationId
      ? this.visaService.updateApplication(this.applicationId, formData)
      : this.visaService.createApplication(formData);

    saveOperation.subscribe({
      next: () => {
        alert('Visa application saved as draft successfully');
        this.router.navigate(['/visa']);
      },
      error: (error) => {
        console.error('Error saving draft:', error);
        alert('Failed to save draft');
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
    return this.visaForm.value;
  }

  markFormGroupTouched(formGroup: FormGroup): void {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      control?.markAsTouched();
    });
  }
}
