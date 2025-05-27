import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-accommodation-request',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './accommodation-request.component.html',
  styleUrl: './accommodation-request.component.scss'
})
export class AccommodationRequestComponent implements OnInit {
  currentStep: number = 1;
  totalSteps: number = 3;
  accommodationForm: FormGroup = new FormGroup({});
  isSubmitting: boolean = false;
  
  // Form step titles
  stepTitles = [
    'Basic Information',
    'Accommodation Details',
    'Budget & Approvals'
  ];
  
  constructor(
    private fb: FormBuilder,
    private router: Router
  ) {
    this.initForm();
  }
  
  ngOnInit(): void {
    this.loadDraft();
  }
  
  // Initialize the form with all fields across all steps
  private initForm(): void {
    this.accommodationForm = this.fb.group({
      // Step 1: Basic Information
      purpose: ['', Validators.required],
      description: ['', Validators.required],
      priority: ['medium', Validators.required],
      relatedTravelRequest: [''],
      
      // Step 2: Accommodation Details
      checkInDate: ['', Validators.required],
      checkOutDate: ['', Validators.required],
      location: ['', Validators.required],
      accommodationType: ['hotel', Validators.required],
      numberOfGuests: [1, [Validators.required, Validators.min(1)]],
      specialRequirements: [''],
      
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
      const control = this.accommodationForm.get(field);
      return control ? control.valid : true;
    });
  }
  
  // Get fields that belong to current step
  private getFieldsForCurrentStep(): string[] {
    switch(this.currentStep) {
      case 1:
        return ['purpose', 'description', 'priority'];
      case 2:
        return ['checkInDate', 'checkOutDate', 'location', 'accommodationType', 'numberOfGuests'];
      case 3:
        return ['estimatedBudget', 'budgetCurrency', 'approvers.focalPerson', 'approvers.departmentHead'];
      default:
        return [];
    }
  }
  
  // Draft saving and loading
  autosaveDraft(): void {
    const draftData = this.accommodationForm.value;
    localStorage.setItem('draft_accommodation_request', JSON.stringify({
      formData: draftData,
      lastStep: this.currentStep,
      timestamp: new Date().toISOString()
    }));
  }
  
  loadDraft(): void {
    const savedDraft = localStorage.getItem('draft_accommodation_request');
    if (savedDraft) {
      try {
        const draftData = JSON.parse(savedDraft);
        this.accommodationForm.patchValue(draftData.formData);
        this.currentStep = draftData.lastStep || 1;
      } catch (error) {
        console.error('Error loading draft:', error);
      }
    }
  }
  
  clearDraft(): void {
    localStorage.removeItem('draft_accommodation_request');
    this.accommodationForm.reset();
    this.currentStep = 1;
    
    // Reset default values
    this.accommodationForm.patchValue({
      priority: 'medium',
      accommodationType: 'hotel',
      numberOfGuests: 1,
      budgetCurrency: 'USD'
    });
  }
  
  // Form submission
  submitRequest(): void {
    if (this.accommodationForm.valid) {
      this.isSubmitting = true;
      
      // Here you would call your API service to submit the request
      // For now, we'll simulate an API call with a timeout
      setTimeout(() => {
        console.log('Accommodation request submitted:', this.accommodationForm.value);
        this.clearDraft();
        this.isSubmitting = false;
        this.router.navigate(['/requests/success'], { 
          state: { message: 'Accommodation request submitted successfully!' } 
        });
      }, 1500);
    } else {
      // Mark all fields as touched to show validation errors
      this.markFormGroupTouched(this.accommodationForm);
    }
  }
  
  // Helper to mark all controls as touched
  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();
      
      if ((control as FormGroup).controls) {
        this.markFormGroupTouched(control as FormGroup);
      }
    });
  }
  
  // Get progress percentage for the progress bar
  get progressPercentage(): number {
    return (this.currentStep / this.totalSteps) * 100;
  }
}
