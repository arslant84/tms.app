import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ExpenseClaimsService } from '../../services/expense-claims.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { AuthService } from '../../../../core/services/auth.service';
import {
  ExpenseClaim,
  DocumentType,
  StaffType,
  ExecutiveStatus,
  MedicalClaimApplicable,
  toBackendFormat,
  toFrontendFormat
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
  defaultCurrency = 'USD';

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
    private confirmationService: ConfirmationService,
    private appSettingsService: AppSettingsService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    // Load default currency from settings
    this.appSettingsService.settings$.subscribe(settings => {
      this.defaultCurrency = settings.default_currency || 'USD';
    });

    this.initForm();

    // Check if we're in edit mode
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.claimId = params['id'];
        this.loadClaimData(this.claimId);
      } else {
        // Only auto-populate in create mode
        this.populateUserDetails();
      }
    });

    // Subscribe to expense items changes for auto-calculation
    this.expenseItems.valueChanges.subscribe(() => {
      this.calculateTotals();
    });
  }

  private populateUserDetails(): void {
    const currentUser = this.authService.getCurrentUser();
    if (currentUser) {
      console.log('Expense Claims - Current user data:', currentUser);
      // Auto-populate user details from logged-in user
      this.expenseForm.get('headerDetails')?.patchValue({
        staffName: currentUser.name || '',
        staffNo: currentUser.staff_id || '',
        departmentCode: currentUser.department || ''
      });
    }
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

  createExpenseItem(data?: any): FormGroup {
    return this.fb.group({
      date: [data?.date || '', [Validators.required]],
      claimOrTravelDetails: this.fb.group({
        from: [data?.claimOrTravelDetails?.from || ''],
        to: [data?.claimOrTravelDetails?.to || ''],
        placeOfStay: [data?.claimOrTravelDetails?.placeOfStay || '']
      }),
      officialMileageKM: [data?.officialMileageKM || null],
      transport: [data?.transport || null],
      hotelAccommodationAllowance: [data?.hotelAccommodationAllowance || null],
      outStationAllowanceMeal: [data?.outStationAllowanceMeal || null],
      miscellaneousAllowance10Percent: [data?.miscellaneousAllowance10Percent || null],
      otherExpenses: [data?.otherExpenses || null]
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

  createForeignExchangeRate(data?: any): FormGroup {
    return this.fb.group({
      date: [data?.date || '', [Validators.required]],
      typeOfCurrency: [data?.typeOfCurrency || '', [Validators.required]],
      sellingRateTTOD: [data?.sellingRateTTOD || null]
    });
  }

  // Alias for consistency with loadClaimData
  createForeignExchangeRateItem(data?: any): FormGroup {
    return this.createForeignExchangeRate(data);
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
    const backendData = toBackendFormat(claimData, this.defaultCurrency) as any;

    console.log('📤 Sending expense claim data to backend:', backendData);
    console.log('📤 Data keys:', Object.keys(backendData));
    console.log('📤 Items count:', backendData.items?.length);

    const saveOperation = this.isEditMode && this.claimId
      ? this.expenseService.updateClaim(Number(this.claimId), backendData)
      : this.expenseService.createClaim(backendData);

    saveOperation.subscribe({
      next: (response) => {
        console.log('✅ Claim saved, now submitting for approval...');
        const claimId = response.id || this.claimId;

        // After saving, submit the claim for approval
        this.expenseService.submitClaim(Number(claimId)).subscribe({
          next: (submitResponse) => {
            this.submitting = false;
            console.log('✅ Claim submitted successfully:', submitResponse);
            this.toastService.success('Claim submitted for approval successfully');
            this.router.navigate(['/expenses']);
          },
          error: (submitErr) => {
            this.submitting = false;
            this.toastService.error('Failed to submit claim for approval: ' + (submitErr.error?.error || submitErr.error?.message || submitErr.message));
            console.error('Error submitting claim:', submitErr);
            // Still navigate to list even if submit fails (claim was saved as draft)
            this.router.navigate(['/expenses']);
          }
        });
      },
      error: (err) => {
        this.submitting = false;
        const action = this.isEditMode ? 'update' : 'create';
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
      status: 'Draft'
    };
  }

  loadClaimData(id: string | number | null): void {
    if (!id) return;

    this.loading = true;
    this.expenseService.getClaimById(Number(id)).subscribe({
      next: (backendClaim: any) => {
        console.log('Loaded claim data from backend:', backendClaim);

        // Convert backend format to frontend format
        const frontendClaim = toFrontendFormat(backendClaim as any);
        console.log('Converted to frontend format:', frontendClaim);

        // Patch header details
        this.expenseForm.patchValue({
          headerDetails: frontendClaim.headerDetails,
          bankDetails: frontendClaim.bankDetails,
          medicalClaimDetails: frontendClaim.medicalClaimDetails,
          financialSummary: frontendClaim.financialSummary,
          declaration: frontendClaim.declaration
        });

        // Clear and rebuild expense items array
        this.expenseItems.clear();
        if (frontendClaim.expenseItems && frontendClaim.expenseItems.length > 0) {
          frontendClaim.expenseItems.forEach((item: any) => {
            this.expenseItems.push(this.createExpenseItem(item));
          });
        } else {
          // Add one default item if none exist
          this.addExpenseItem();
        }

        // Clear and rebuild foreign exchange rate array
        this.foreignExchangeRates.clear();
        if (frontendClaim.informationOnForeignExchangeRate && frontendClaim.informationOnForeignExchangeRate.length > 0) {
          frontendClaim.informationOnForeignExchangeRate.forEach((fx: any) => {
            this.foreignExchangeRates.push(this.createForeignExchangeRateItem(fx));
          });
        }

        this.calculateTotals();
        this.loading = false;
      },
      error: (err) => {
        this.toastService.error('Failed to load claim data');
        this.loading = false;
        console.error('Error loading claim:', err);
        this.router.navigate(['/expenses']);
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
