import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { FormUtilsService } from '../../../core/utils/form-utils.service';
import { Router, ActivatedRoute } from '@angular/router';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-travel-request-wizard',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LoadingSpinnerComponent],
  templateUrl: './travel-request-wizard.component.html',
  styleUrl: './travel-request-wizard.component.scss'
})
export class TravelRequestWizardComponent implements OnInit {
  currentStep: number = 1;
  totalSteps: number = 4;
  travelRequestForm: FormGroup = new FormGroup({});
  isSubmitting: boolean = false;
  requestType: string = 'domestic'; // Default type
  
  // Form step titles
  stepTitles = [
    'Basic Information',
    'Travel Details',
    'Accommodation & Transport',
    'Budget & Approvals'
  ];
  
  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private formUtils: FormUtilsService
  ) {
    this.initForm();
  }
  
  ngOnInit(): void {
    // Determine the request type from the URL
    const urlPath = this.router.url;
    if (urlPath.includes('/domestic')) {
      this.requestType = 'domestic';
    } else if (urlPath.includes('/international')) {
      this.requestType = 'international';
    } else if (urlPath.includes('/home-leave')) {
      this.requestType = 'home-leave';
    } else if (urlPath.includes('/external')) {
      this.requestType = 'external';
    }
    
    // Load any saved draft
    this.loadDraft();
  }
  
  // Initialize the form with all fields across all steps
  private initForm(): void {
    this.travelRequestForm = this.fb.group({
      // Step 1: Basic Information
      requestType: ['domestic', Validators.required], // Will be set based on selection
      purpose: ['', Validators.required],
      description: ['', Validators.required],
      priority: ['medium', Validators.required],
      
      // Step 2: Travel Details
      departureDate: ['', Validators.required],
      returnDate: ['', Validators.required],
      originCity: ['', Validators.required],
      destinationCity: ['', Validators.required],
      travelMode: ['flight', Validators.required],
      
      // Step 3: Accommodation & Transport
      requiresAccommodation: [false],
      accommodationType: [''],
      checkInDate: [''],
      checkOutDate: [''],
      requiresLocalTransport: [false],
      transportType: [''],
      
      // Step 4: Budget & Approvals
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
      const control = this.travelRequestForm.get(field);
      return control ? control.valid : true;
    });
  }
  
  // Get fields that belong to current step
  private getFieldsForCurrentStep(): string[] {
    switch(this.currentStep) {
      case 1:
        return ['purpose', 'description', 'priority'];
      case 2:
        return ['departureDate', 'returnDate', 'originCity', 'destinationCity', 'travelMode'];
      case 3:
        return ['requiresAccommodation', 'requiresLocalTransport'];
      case 4:
        return ['estimatedBudget', 'budgetCurrency', 'approvers.focalPerson', 'approvers.departmentHead'];
      default:
        return [];
    }
  }
  
  // Draft saving and loading
  autosaveDraft(): void {
    const draftData = this.travelRequestForm.value;
    localStorage.setItem(`draft_travel_request_${this.requestType}`, JSON.stringify({
      formData: draftData,
      lastStep: this.currentStep,
      requestType: this.requestType,
      timestamp: new Date().toISOString()
    }));
  }
  
  loadDraft(): void {
    const savedDraft = localStorage.getItem(`draft_travel_request_${this.requestType}`);
    if (savedDraft) {
      try {
        const draftData = JSON.parse(savedDraft);
        // Only load if the draft matches the current request type
        if (draftData.requestType === this.requestType) {
          this.travelRequestForm.patchValue(draftData.formData);
          this.currentStep = draftData.lastStep || 1;
        }
      } catch (error) {
        console.error('Error loading draft:', error);
      }
    }
    
    // Set the request type in the form
    this.travelRequestForm.patchValue({ requestType: this.requestType });
  }
  
  clearDraft(): void {
    localStorage.removeItem(`draft_travel_request_${this.requestType}`);
    this.travelRequestForm.reset();
    this.travelRequestForm.patchValue({ requestType: this.requestType });
    this.currentStep = 1;
  }
  
  // Form submission
  submitRequest(): void {
    if (this.travelRequestForm.valid) {
      this.isSubmitting = true;
      
      // Here you would call your API service to submit the request
      // For now, we'll simulate an API call with a timeout
      setTimeout(() => {
        this.clearDraft();
        this.isSubmitting = false;
        this.router.navigate(['/requests/success'], { 
          state: { 
            message: `${this.getRequestTypeLabel()} request submitted successfully!`,
            requestType: this.requestType 
          } 
        });
      }, 1500);
    } else {
      // Mark all fields as touched to show validation errors
      this.formUtils.markFormGroupTouched(this.travelRequestForm);
    }
  }
  
  
  // Get progress percentage for the progress bar
  get progressPercentage(): number {
    return (this.currentStep / this.totalSteps) * 100;
  }
  
  // Get a user-friendly label for the request type
  getRequestTypeLabel(): string {
    switch(this.requestType) {
      case 'domestic':
        return 'Domestic Business Trip';
      case 'international':
        return 'International Business Trip';
      case 'home-leave':
        return 'Home Leave Passage';
      case 'external':
        return 'Business Travel Request for External Parties';
      default:
        return 'Travel Request';
    }
  }
}
