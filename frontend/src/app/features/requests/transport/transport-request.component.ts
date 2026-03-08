import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { FormUtilsService } from '../../../core/utils/form-utils.service';
import { Router } from '@angular/router';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-transport-request',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LoadingSpinnerComponent],
  templateUrl: './transport-request.component.html',
  styleUrl: './transport-request.component.scss'
})
export class TransportRequestComponent implements OnInit {
  currentStep: number = 1;
  totalSteps: number = 3;
  transportForm: FormGroup = new FormGroup({});
  isSubmitting: boolean = false;
  
  // Form step titles
  stepTitles = [
    'Basic Information',
    'Transport Details',
    'Budget & Approvals'
  ];
  
  constructor(
    private fb: FormBuilder,
    private router: Router,
    private formUtils: FormUtilsService
  ) {
    this.initForm();
  }
  
  ngOnInit(): void {
    this.loadDraft();
  }
  
  // Initialize the form with all fields across all steps
  private initForm(): void {
    this.transportForm = this.fb.group({
      // Step 1: Basic Information
      purpose: ['', Validators.required],
      description: ['', Validators.required],
      priority: ['medium', Validators.required],
      relatedTravelRequest: [''],
      
      // Step 2: Transport Details
      transportType: ['taxi', Validators.required],
      startDate: ['', Validators.required],
      endDate: ['', Validators.required],
      pickupLocation: ['', Validators.required],
      dropoffLocation: ['', Validators.required],
      numberOfPassengers: [1, [Validators.required, Validators.min(1)]],
      specialRequirements: [''],
      isRoundTrip: [false],
      
      // Step 3: Budget & Approvals
      estimatedBudget: ['', [Validators.required, Validators.min(0)]],
      budgetCurrency: ['USD', Validators.required],
      budgetJustification: [''],
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
      const control = this.transportForm.get(field);
      return control ? control.valid : true;
    });
  }
  
  // Get fields that belong to current step
  private getFieldsForCurrentStep(): string[] {
    switch(this.currentStep) {
      case 1:
        return ['purpose', 'description', 'priority'];
      case 2:
        return ['transportType', 'startDate', 'endDate', 'pickupLocation', 'dropoffLocation', 'numberOfPassengers'];
      case 3:
        return ['estimatedBudget', 'budgetCurrency', 'approvers.focalPerson', 'approvers.departmentHead'];
      default:
        return [];
    }
  }
  
  // Draft saving and loading
  autosaveDraft(): void {
    const draftData = this.transportForm.value;
    localStorage.setItem('draft_transport_request', JSON.stringify({
      formData: draftData,
      lastStep: this.currentStep,
      timestamp: new Date().toISOString()
    }));
  }
  
  loadDraft(): void {
    const savedDraft = localStorage.getItem('draft_transport_request');
    if (savedDraft) {
      try {
        const draftData = JSON.parse(savedDraft);
        this.transportForm.patchValue(draftData.formData);
        this.currentStep = draftData.lastStep || 1;
      } catch (error) {
        console.error('Error loading draft:', error);
      }
    }
  }
  
  clearDraft(): void {
    localStorage.removeItem('draft_transport_request');
    this.transportForm.reset();
    this.currentStep = 1;
    
    // Reset default values
    this.transportForm.patchValue({
      priority: 'medium',
      transportType: 'taxi',
      numberOfPassengers: 1,
      isRoundTrip: false,
      budgetCurrency: 'USD'
    });
  }
  
  // Form submission
  submitRequest(): void {
    if (this.transportForm.valid) {
      this.isSubmitting = true;
      
      // Here you would call your API service to submit the request
      // For now, we'll simulate an API call with a timeout
      setTimeout(() => {
        this.clearDraft();
        this.isSubmitting = false;
        this.router.navigate(['/requests/success'], { 
          state: { message: 'Transport request submitted successfully!' } 
        });
      }, 1500);
    } else {
      // Mark all fields as touched to show validation errors
      this.formUtils.markFormGroupTouched(this.transportForm);
    }
  }
  
  
  // Get progress percentage for the progress bar
  get progressPercentage(): number {
    return (this.currentStep / this.totalSteps) * 100;
  }
}
