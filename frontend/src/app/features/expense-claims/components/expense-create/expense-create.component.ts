import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ExpenseClaimsService } from '../../services/expense-claims.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import {
  ExpenseClaim,
  DocumentType,
  StaffType,
  ExecutiveStatus,
  MedicalClaimApplicable,
  toBackendFormat
} from '../../models/expense-claim.model';

// Time validation regex
const TIME_REGEX = /^([01]\d|2[0-3]):([0-5]\d)$/;

// Custom validator for time format
function timeValidator(control: AbstractControl): ValidationErrors | null {
  if (!control.value) return null;
  return TIME_REGEX.test(control.value) ? null : { invalidTime: true };
}

@Component({
  selector: 'app-expense-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './expense-create.component.html',
  styleUrl: './expense-create.component.scss'
})
export class ExpenseCreateComponent implements OnInit {
  expenseForm!: FormGroup;

  // Constants matching React source
  documentTypes: DocumentType[] = ['TR01', 'TB35', 'TB05'];
  staffTypes: StaffType[] = ['PERMANENT STAFF', 'CONTRACT STAFF'];
  executiveStatuses: ExecutiveStatus[] = ['EXECUTIVE', 'NON-EXECUTIVE'];
  medicalTypes: MedicalClaimApplicable[] = ['Inpatient', 'Outpatient'];
  currencyTypes = ['USD', 'MYR', 'EUR', 'GBP', 'SGD', 'AUD', 'JPY', 'CNY'];

  isEditMode = false;
  claimId: string | number | null = null;
  loading = false;
  submitting = false;

  // Calculated totals
  totalMileage = 0;
  totalTransport = 0;
  totalHotel = 0;
  totalOutstation = 0;
  totalMisc = 0;
  totalOther = 0;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private expenseService: ExpenseClaimsService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit(): void {
    this.initForm();

    // Check if we're in edit mode
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.claimId = params['id'];
        this.loadClaimData(this.claimId);
      }
    });

    // Subscribe to expense items changes for auto-calculation
    this.expenseItems.valueChanges.subscribe(() => {
      this.calculateTotals();
    });
  }

  initForm(): void {
    this.expenseForm = this.fb.group({
      // Header Details
      headerDetails: this.fb.group({
        documentType: ['', [Validators.required]],
        documentNumber: ['', [Validators.required]],
        claimForMonthOf: ['', [Validators.required]],
        staffName: ['', [Validators.required]],
        staffNo: ['', [Validators.required]],
        gred: ['', [Validators.required]],
        staffType: ['', [Validators.required]],
        executiveStatus: ['', [Validators.required]],
        departmentCode: ['', [Validators.required]],
        deptCostCenterCode: ['', [Validators.required]],
        location: ['', [Validators.required]],
        telExt: ['', [Validators.required]],
        startTimeFromHome: ['', [Validators.required, timeValidator]],
        timeOfArrivalAtHome: ['', [Validators.required, timeValidator]]
      }),

      // Bank Details
      bankDetails: this.fb.group({
        bankName: ['', [Validators.required]],
        accountNumber: ['', [Validators.required]],
        purposeOfClaim: ['', [Validators.required]]
      }),

      // Medical Claim Details
      medicalClaimDetails: this.fb.group({
        isMedicalClaim: [false],
        applicableMedicalType: [''],
        isForFamily: [false],
        familyMemberSpouse: [false],
        familyMemberChildren: [false],
        familyMemberOther: ['']
      }),

      // Expense Items (dynamic array)
      expenseItems: this.fb.array([]),

      // Foreign Exchange Rate (dynamic array)
      informationOnForeignExchangeRate: this.fb.array([]),

      // Financial Summary
      financialSummary: this.fb.group({
        totalAdvanceClaimAmount: [{ value: 0, disabled: true }],
        lessAdvanceTaken: [0],
        lessCorporateCreditCardPayment: [0],
        balanceClaimRepayment: [{ value: 0, disabled: true }],
        chequeReceiptNo: ['']
      }),

      // Declaration
      declaration: this.fb.group({
        iDeclare: [false, [Validators.requiredTrue]],
        date: ['', [Validators.required]]
      })
    });

    // Watch for changes to calculate balance
    this.expenseForm.get('financialSummary')?.valueChanges.subscribe(() => {
      this.calculateBalance();
    });
  }

  // Expense Items Array Methods
  get expenseItems(): FormArray {
    return this.expenseForm.get('expenseItems') as FormArray;
  }

  createExpenseItem(): FormGroup {
    return this.fb.group({
      date: ['', [Validators.required]],
      claimOrTravelDetails: this.fb.group({
        from: [''],
        to: [''],
        placeOfStay: ['']
      }),
      officialMileageKM: [null],
      transport: [null],
      hotelAccommodationAllowance: [null],
      outStationAllowanceMeal: [null],
      miscellaneousAllowance10Percent: [null],
      otherExpenses: [null]
    });
  }

  addExpenseItem(): void {
    this.expenseItems.push(this.createExpenseItem());
  }

  removeExpenseItem(index: number): void {
    if (this.expenseItems.length > 0) {
      this.expenseItems.removeAt(index);
    }
  }

  // Foreign Exchange Rate Array Methods
  get foreignExchangeRates(): FormArray {
    return this.expenseForm.get('informationOnForeignExchangeRate') as FormArray;
  }

  createForeignExchangeRate(): FormGroup {
    return this.fb.group({
      date: ['', [Validators.required]],
      typeOfCurrency: ['', [Validators.required]],
      sellingRateTTOD: [null]
    });
  }

  addForeignExchangeRate(): void {
    this.foreignExchangeRates.push(this.createForeignExchangeRate());
  }

  removeForeignExchangeRate(index: number): void {
    this.foreignExchangeRates.removeAt(index);
  }

  // Calculation Methods
  calculateTotals(): void {
    const items = this.expenseItems.controls;

    this.totalMileage = items.reduce((sum, item) =>
      sum + (Number(item.get('officialMileageKM')?.value) || 0), 0);

    this.totalTransport = items.reduce((sum, item) =>
      sum + (Number(item.get('transport')?.value) || 0), 0);

    this.totalHotel = items.reduce((sum, item) =>
      sum + (Number(item.get('hotelAccommodationAllowance')?.value) || 0), 0);

    this.totalOutstation = items.reduce((sum, item) =>
      sum + (Number(item.get('outStationAllowanceMeal')?.value) || 0), 0);

    this.totalMisc = items.reduce((sum, item) =>
      sum + (Number(item.get('miscellaneousAllowance10Percent')?.value) || 0), 0);

    this.totalOther = items.reduce((sum, item) =>
      sum + (Number(item.get('otherExpenses')?.value) || 0), 0);

    // Calculate grand total
    const grandTotal = this.totalTransport + this.totalHotel +
                      this.totalOutstation + this.totalMisc + this.totalOther;

    this.expenseForm.get('financialSummary.totalAdvanceClaimAmount')?.setValue(grandTotal, { emitEvent: false });
    this.calculateBalance();
  }

  calculateBalance(): void {
    const summary = this.expenseForm.get('financialSummary');
    const total = Number(summary?.get('totalAdvanceClaimAmount')?.value) || 0;
    const advance = Number(summary?.get('lessAdvanceTaken')?.value) || 0;
    const creditCard = Number(summary?.get('lessCorporateCreditCardPayment')?.value) || 0;

    const balance = total - advance - creditCard;
    summary?.get('balanceClaimRepayment')?.setValue(balance, { emitEvent: false });
  }

  // Form Submission
  onSubmit(): void {
    if (this.expenseForm.invalid) {
      this.markFormGroupTouched(this.expenseForm);
      this.toastService.warning('Please fill in all required fields correctly');
      this.scrollToFirstError();
      return;
    }

    if (this.expenseItems.length === 0) {
      this.toastService.warning('Please add at least one expense item');
      return;
    }

    this.submitting = true;
    const claimData = this.prepareClaimData();
    const backendData = toBackendFormat(claimData) as any;

    console.log('📤 Sending expense claim data to backend:', backendData);
    console.log('📤 Data keys:', Object.keys(backendData));
    console.log('📤 Items count:', backendData.items?.length);

    const saveOperation = this.isEditMode && this.claimId
      ? this.expenseService.updateClaim(Number(this.claimId), backendData)
      : this.expenseService.createClaim(backendData);

    saveOperation.subscribe({
      next: (response) => {
        this.submitting = false;
        const message = this.isEditMode ? 'Claim updated successfully' : 'Claim submitted successfully';
        this.toastService.success(message);
        // Navigate to list instead of detail view
        this.router.navigate(['/expenses']);
      },
      error: (err) => {
        this.submitting = false;
        const action = this.isEditMode ? 'update' : 'submit';
        this.toastService.error(`Failed to ${action} claim: ` + (err.error?.message || err.message));
        console.error(`Error ${action}ing claim:`, err);
        if (err.error) {
          console.error('Backend error details:', JSON.stringify(err.error, null, 2));
        }
      }
    });
  }

  onSaveDraft(): void {
    this.submitting = true;
    const claimData = this.prepareClaimData();
    claimData.status = 'Draft';
    const backendData = toBackendFormat(claimData) as any;

    console.log('📤 Sending draft expense claim data to backend:', backendData);
    console.log('📤 Draft data keys:', Object.keys(backendData));
    console.log('📤 Draft items count:', backendData.items?.length);

    const saveOperation = this.isEditMode && this.claimId
      ? this.expenseService.updateClaim(Number(this.claimId), backendData)
      : this.expenseService.createClaim(backendData);

    saveOperation.subscribe({
      next: (response) => {
        this.submitting = false;
        this.toastService.success('Draft saved successfully');
        this.router.navigate(['/expenses']);
      },
      error: (err) => {
        this.submitting = false;
        this.toastService.error('Failed to save draft: ' + (err.error?.message || err.message));
        console.error('Error saving draft:', err);
        if (err.error) {
          console.error('Backend error details:', JSON.stringify(err.error, null, 2));
        }
      }
    });
  }

  onCancel(): void {
    this.confirmationService.confirmCancel().subscribe(confirmed => {
      if (confirmed) {
        this.router.navigate(['/expenses']);
      }
    });
  }

  prepareClaimData(): ExpenseClaim {
    const formValue = this.expenseForm.getRawValue(); // getRawValue includes disabled fields

    return {
      id: this.claimId || undefined,
      headerDetails: formValue.headerDetails,
      bankDetails: formValue.bankDetails,
      medicalClaimDetails: formValue.medicalClaimDetails,
      expenseItems: formValue.expenseItems,
      informationOnForeignExchangeRate: formValue.informationOnForeignExchangeRate,
      financialSummary: formValue.financialSummary,
      declaration: formValue.declaration,
      status: 'Pending Verification'
    };
  }

  loadClaimData(id: string | number | null): void {
    if (!id) return;

    this.loading = true;
    this.expenseService.getClaimById(Number(id)).subscribe({
      next: (claim) => {
        // TODO: Convert backend format to frontend format and patch form
        // For now, just log
        console.log('Loaded claim data:', claim);
        this.loading = false;
      },
      error: (err) => {
        this.toastService.error('Failed to load claim data');
        this.loading = false;
        console.error('Error loading claim:', err);
      }
    });
  }

  // Helper Methods
  private markFormGroupTouched(formGroup: FormGroup | FormArray): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();

      if (control instanceof FormGroup || control instanceof FormArray) {
        this.markFormGroupTouched(control);
      }
    });
  }

  private scrollToFirstError(): void {
    setTimeout(() => {
      const firstError = document.querySelector('.ng-invalid:not(form)');
      if (firstError) {
        firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 100);
  }

  // Getter helpers for template
  get isMedicalClaim(): boolean {
    return this.expenseForm.get('medicalClaimDetails.isMedicalClaim')?.value === true;
  }

  get isForFamily(): boolean {
    return this.expenseForm.get('medicalClaimDetails.isForFamily')?.value === true;
  }

  formatNumber(value: any, decimals: number = 2): string {
    const num = Number(value);
    return isNaN(num) ? '0.' + '0'.repeat(decimals) : num.toFixed(decimals);
  }
}
