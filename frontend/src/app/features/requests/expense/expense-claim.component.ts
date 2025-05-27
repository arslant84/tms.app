import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-expense-claim',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './expense-claim.component.html',
  styleUrl: './expense-claim.component.scss'
})
export class ExpenseClaimComponent implements OnInit {
  currentStep: number = 1;
  totalSteps: number = 3;
  expenseForm: FormGroup = new FormGroup({});
  isSubmitting: boolean = false;
  
  // Form step titles
  stepTitles = [
    'Basic Information',
    'Expense Details',
    'Review & Submit'
  ];
  
  // Expense categories
  expenseCategories = [
    { id: 'transportation', name: 'Transportation' },
    { id: 'accommodation', name: 'Accommodation' },
    { id: 'meals', name: 'Meals & Entertainment' },
    { id: 'conference', name: 'Conference & Registration Fees' },
    { id: 'visa', name: 'Visa & Immigration Fees' },
    { id: 'communication', name: 'Communication' },
    { id: 'supplies', name: 'Office Supplies' },
    { id: 'other', name: 'Other' }
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
    this.expenseForm = this.fb.group({
      // Step 1: Basic Information
      title: ['', Validators.required],
      description: ['', Validators.required],
      tripPurpose: ['', Validators.required],
      relatedTravelRequest: [''],
      startDate: ['', Validators.required],
      endDate: ['', Validators.required],
      
      // Step 2: Expense Details
      expenseItems: this.fb.array([]),
      totalAmount: [{ value: 0, disabled: true }],
      currency: ['USD', Validators.required],
      paymentMethod: ['reimbursement', Validators.required],
      bankAccountDetails: [''],
      
      // Step 3: Review & Submit
      attachments: [null],
      comments: [''],
      approvers: this.fb.group({
        focalPerson: ['', Validators.required],
        departmentHead: ['', Validators.required],
        financeManager: ['', Validators.required]
      })
    });
    
    // Add one expense item by default
    this.addExpenseItem();
  }
  
  // Get the expense items form array
  get expenseItems(): FormArray {
    return this.expenseForm.get('expenseItems') as FormArray;
  }
  
  // Add a new expense item to the form array
  addExpenseItem(): void {
    const expenseItem = this.fb.group({
      date: ['', Validators.required],
      category: ['', Validators.required],
      description: ['', Validators.required],
      amount: ['', [Validators.required, Validators.min(0.01)]],
      currency: ['USD', Validators.required],
      receiptAttached: [true],
      notes: ['']
    });
    
    this.expenseItems.push(expenseItem);
    this.calculateTotal();
  }
  
  // Remove an expense item from the form array
  removeExpenseItem(index: number): void {
    this.expenseItems.removeAt(index);
    this.calculateTotal();
  }
  
  // Calculate the total amount of all expense items
  calculateTotal(): void {
    let total = 0;
    
    for (let i = 0; i < this.expenseItems.length; i++) {
      const amount = parseFloat(this.expenseItems.at(i).get('amount')?.value || 0);
      if (!isNaN(amount)) {
        total += amount;
      }
    }
    
    this.expenseForm.get('totalAmount')?.setValue(total.toFixed(2));
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
    switch(this.currentStep) {
      case 1:
        return !!this.expenseForm.get('title')?.valid &&
               !!this.expenseForm.get('description')?.valid &&
               !!this.expenseForm.get('tripPurpose')?.valid &&
               !!this.expenseForm.get('startDate')?.valid &&
               !!this.expenseForm.get('endDate')?.valid;
      case 2:
        if (this.expenseItems.length === 0) return false;
        
        for (let i = 0; i < this.expenseItems.length; i++) {
          const item = this.expenseItems.at(i);
          if (!item.valid) return false;
        }
        
        return !!this.expenseForm.get('currency')?.valid &&
               !!this.expenseForm.get('paymentMethod')?.valid;
      case 3:
        return !!this.expenseForm.get('approvers.focalPerson')?.valid &&
               !!this.expenseForm.get('approvers.departmentHead')?.valid &&
               !!this.expenseForm.get('approvers.financeManager')?.valid;
      default:
        return false;
    }
  }
  
  // Draft saving and loading
  autosaveDraft(): void {
    const draftData = {
      ...this.expenseForm.getRawValue(),
      totalAmount: this.expenseForm.get('totalAmount')?.value
    };
    
    localStorage.setItem('draft_expense_claim', JSON.stringify({
      formData: draftData,
      lastStep: this.currentStep,
      timestamp: new Date().toISOString()
    }));
  }
  
  loadDraft(): void {
    const savedDraft = localStorage.getItem('draft_expense_claim');
    if (savedDraft) {
      try {
        const draftData = JSON.parse(savedDraft);
        
        // Clear existing expense items
        while (this.expenseItems.length) {
          this.expenseItems.removeAt(0);
        }
        
        // Add expense items from draft
        if (draftData.formData.expenseItems && draftData.formData.expenseItems.length > 0) {
          draftData.formData.expenseItems.forEach((item: any) => {
            const expenseItem = this.fb.group({
              date: [item.date, Validators.required],
              category: [item.category, Validators.required],
              description: [item.description, Validators.required],
              amount: [item.amount, [Validators.required, Validators.min(0.01)]],
              currency: [item.currency, Validators.required],
              receiptAttached: [item.receiptAttached],
              notes: [item.notes]
            });
            
            this.expenseItems.push(expenseItem);
          });
        } else {
          // Add one expense item by default if none in draft
          this.addExpenseItem();
        }
        
        // Set other form values
        this.expenseForm.patchValue({
          title: draftData.formData.title,
          description: draftData.formData.description,
          tripPurpose: draftData.formData.tripPurpose,
          relatedTravelRequest: draftData.formData.relatedTravelRequest,
          startDate: draftData.formData.startDate,
          endDate: draftData.formData.endDate,
          currency: draftData.formData.currency,
          paymentMethod: draftData.formData.paymentMethod,
          bankAccountDetails: draftData.formData.bankAccountDetails,
          comments: draftData.formData.comments,
          approvers: draftData.formData.approvers
        });
        
        // Set total amount
        this.expenseForm.get('totalAmount')?.setValue(draftData.formData.totalAmount);
        
        // Set current step
        this.currentStep = draftData.lastStep || 1;
      } catch (error) {
        console.error('Error loading draft:', error);
      }
    }
  }
  
  clearDraft(): void {
    localStorage.removeItem('draft_expense_claim');
    
    // Reset form
    this.expenseForm.reset();
    
    // Clear expense items
    while (this.expenseItems.length) {
      this.expenseItems.removeAt(0);
    }
    
    // Add one expense item by default
    this.addExpenseItem();
    
    // Reset default values
    this.expenseForm.patchValue({
      currency: 'USD',
      paymentMethod: 'reimbursement'
    });
    
    this.currentStep = 1;
  }
  
  // Form submission
  submitRequest(): void {
    if (this.expenseForm.valid) {
      this.isSubmitting = true;
      
      // Get form data including disabled fields
      const formData = {
        ...this.expenseForm.getRawValue(),
        totalAmount: this.expenseForm.get('totalAmount')?.value
      };
      
      // Here you would call your API service to submit the request
      // For now, we'll simulate an API call with a timeout
      setTimeout(() => {
        console.log('Expense claim submitted:', formData);
        this.clearDraft();
        this.isSubmitting = false;
        this.router.navigate(['/requests/success'], { 
          state: { message: 'Expense claim submitted successfully!' } 
        });
      }, 1500);
    } else {
      // Mark all fields as touched to show validation errors
      this.markFormGroupTouched(this.expenseForm);
    }
  }
  
  // Helper to mark all controls as touched
  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();
      
      if ((control as FormGroup).controls) {
        this.markFormGroupTouched(control as FormGroup);
      } else if ((control as FormArray).controls) {
        const formArray = control as FormArray;
        for (let i = 0; i < formArray.length; i++) {
          this.markFormGroupTouched(formArray.at(i) as FormGroup);
        }
      }
    });
  }
  
  // Get progress percentage for the progress bar
  get progressPercentage(): number {
    return (this.currentStep / this.totalSteps) * 100;
  }
  
  // Helper method to get category name from category id
  getCategoryName(categoryId: string): string {
    if (!categoryId) return '';
    const category = this.expenseCategories.find(cat => cat.id === categoryId);
    return category ? category.name : categoryId;
  }
}
