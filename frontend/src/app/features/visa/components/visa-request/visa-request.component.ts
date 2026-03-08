import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { Router } from '@angular/router';
import { VisaService } from '../../services/visa.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-visa-request',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LoadingSpinnerComponent],
  templateUrl: './visa-request.component.html',
  styleUrl: './visa-request.component.scss'
})
export class VisaRequestComponent implements OnInit {
  currentStep: number = 1;
  totalSteps: number = 3;
  visaForm: FormGroup = new FormGroup({});
  isSubmitting: boolean = false;
  
  // Form step titles
  stepTitles = [
    'Basic Information',
    'Visa Details',
    'Documents & Approvals'
  ];
  
  constructor(
    private fb: FormBuilder,
    private router: Router,
    private visaService: VisaService,
    private formUtils: FormUtilsService
  ) {
    this.initForm();
  }
  
  ngOnInit(): void {
    this.loadDraft();
  }
  
  // Initialize the form with all fields across all steps
  private initForm(): void {
    this.visaForm = this.fb.group({
      // Step 1: Basic Information
      purpose: ['', Validators.required],
      description: ['', Validators.required],
      priority: ['medium', Validators.required],
      relatedTravelRequest: [''],
      
      // Step 2: Visa Details
      visaType: ['business', Validators.required],
      country: ['', Validators.required],
      entryType: ['single', Validators.required],
      plannedArrivalDate: ['', Validators.required],
      plannedDepartureDate: ['', Validators.required],
      durationOfStay: ['', Validators.required],
      hasVisitedBefore: [false],
      previousVisitDetails: [''],
      
      // Step 3: Documents & Approvals
      hasPassport: [true, Validators.required],
      passportNumber: [''],
      passportExpiryDate: [''],
      requiresLetterOfInvitation: [false],
      requiresHotelBooking: [false],
      requiresFlightBooking: [false],
      otherRequirements: [''],
      estimatedProcessingFee: ['', [Validators.required, Validators.min(0)]],
      budgetCurrency: ['USD', Validators.required],
      attachments: [null],
      approvers: this.fb.group({
        focalPerson: ['', Validators.required],
        departmentHead: ['', Validators.required]
      })
    });
  }
  
  // Navigation methods
  nextStep(): void {
    if (this.currentStep < this.totalSteps) {
      this.currentStep++;
      this.autosaveDraft();
    }
  }
  
  previousStep(): void {
    if (this.currentStep > 1) {
      this.currentStep--;
    }
  }
  
  // Check if current step is valid
  isCurrentStepValid(): boolean {
    const fieldsToValidate = this.getFieldsForCurrentStep();
    return fieldsToValidate.every(field => {
      const control = this.visaForm.get(field);
      return control ? control.valid : true;
    });
  }
  
  // Get fields that belong to current step
  private getFieldsForCurrentStep(): string[] {
    switch(this.currentStep) {
      case 1:
        return ['purpose', 'description', 'priority'];
      case 2:
        return ['visaType', 'country', 'entryType', 'plannedArrivalDate', 'plannedDepartureDate', 'durationOfStay'];
      case 3:
        return ['hasPassport', 'estimatedProcessingFee', 'budgetCurrency', 'approvers.focalPerson', 'approvers.departmentHead'];
      default:
        return [];
    }
  }
  
  // Draft saving and loading
  autosaveDraft(): void {
    const draftData = this.visaForm.value;
    localStorage.setItem('draft_visa_request', JSON.stringify({
      formData: draftData,
      lastStep: this.currentStep,
      timestamp: new Date().toISOString()
    }));
  }
  
  loadDraft(): void {
    const savedDraft = localStorage.getItem('draft_visa_request');
    if (savedDraft) {
      try {
        const draftData = JSON.parse(savedDraft);
        this.visaForm.patchValue(draftData.formData);
        this.currentStep = draftData.lastStep || 1;
      } catch (error) {
        console.error('Error loading draft:', error);
      }
    }
  }
  
  clearDraft(): void {
    localStorage.removeItem('draft_visa_request');
    this.visaForm.reset();
    this.currentStep = 1;
    
    // Reset default values
    this.visaForm.patchValue({
      priority: 'medium',
      visaType: 'business',
      entryType: 'single',
      hasPassport: true,
      hasVisitedBefore: false,
      requiresLetterOfInvitation: false,
      requiresHotelBooking: false,
      requiresFlightBooking: false,
      budgetCurrency: 'USD'
    });
  }
  
  // Form submission
  submitRequest(): void {
    if (this.visaForm.valid) {
      this.isSubmitting = true;
      this.visaService.createApplication(this.visaForm.value).subscribe({
        next: () => {
          this.clearDraft();
          this.isSubmitting = false;
          this.router.navigate(['/requests/success'], {
            state: { message: 'Visa request submitted successfully!' }
          });
        },
        error: (error) => {
          console.error('Error submitting visa request:', error);
          this.isSubmitting = false;
        }
      });
    } else {
      // Mark all fields as touched to show validation errors
      this.formUtils.markFormGroupTouched(this.visaForm);
    }
  }
  
  
  // Get progress percentage for the progress bar
  get progressPercentage(): number {
    return (this.currentStep / this.totalSteps) * 100;
  }
}
