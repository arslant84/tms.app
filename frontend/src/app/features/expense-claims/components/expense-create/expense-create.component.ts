import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ExpenseClaimsService } from '../../services/expense-claims.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-expense-create',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule
  ],
  templateUrl: './expense-create.component.html',
  styleUrl: './expense-create.component.scss'
})
export class ExpenseCreateComponent implements OnInit {
  expenseForm!: FormGroup;
  staffTypes = ['PERMANENT STAFF', 'CONTRACT STAFF', 'EXECUTIVE', 'NON-EXECUTIVE'];
  claimTypes = ['TR01', 'TR05', 'TR06'];
  currencyTypes = ['MYR', 'USD', 'EUR', 'GBP', 'SGD', 'AUD'];

  isEditMode = false;
  claimId: number | null = null;
  loading = false;
  submitting = false;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private expenseService: ExpenseClaimsService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.initForm();

    // Check if we're in edit mode
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.claimId = +params['id'];
        this.loadClaimData(this.claimId);
      }
    });
  }

  initForm(): void {
    this.expenseForm = this.fb.group({
      documentNumber: ['', Validators.required],
      claimForMonthOf: ['', Validators.required],
      staffInfo: this.fb.group({
        name: ['', Validators.required],
        staffType: ['', Validators.required],
        staffNo: ['', Validators.required],
        hired: ['', Validators.required],
        departmentCode: ['', Validators.required],
        costCenterCode: ['', Validators.required],
        location: [''],
        telext: ['']
      }),
      bankDetails: this.fb.group({
        bankName: ['', Validators.required],
        accountNumber: ['', Validators.required],
        address: ['', Validators.required],
        purposeOfClaim: ['', Validators.required]
      }),
      travelTimes: this.fb.group({
        startTime: [''],
        arrivalTime: ['']
      }),
      medicalClaim: this.fb.group({
        isApplying: [false],
        forFamily: [false],
        spouse: [false],
        children: [false],
        other: [false]
      }),
      expenseItems: this.fb.array([
        this.createExpenseItem()
      ]),
      foreignExchange: this.fb.array([
        this.createExchangeRate()
      ]),
      totalAmount: ['0.00'],
      advanceTaken: ['0.00'],
      creditCardPayment: ['0.00'],
      balanceAmount: ['0.00'],
      debitCredit: ['DEBIT'],
      signature: [''],
      verifiedBy: [''],
      approvedBy: [''],
      dateSubmitted: [''],
      termsAccepted: [false, Validators.requiredTrue]
    });
  }

  createExpenseItem(): FormGroup {
    return this.fb.group({
      date: ['', Validators.required],
      fromTo: ['', Validators.required],
      mileage: ['0'],
      transport: ['0.00'],
      accommodation: ['0.00'],
      outstation: ['0.00'],
      miscellaneous: ['0.00'],
      other: ['0.00']
    });
  }

  createExchangeRate(): FormGroup {
    return this.fb.group({
      date: [''],
      currencyType: [''],
      sellingRate: [''],
      totalInForeignCurrency: ['0.00']
    });
  }

  get expenseItems(): FormArray {
    return this.expenseForm.get('expenseItems') as FormArray;
  }

  get foreignExchange(): FormArray {
    return this.expenseForm.get('foreignExchange') as FormArray;
  }

  addExpenseItem(): void {
    this.expenseItems.push(this.createExpenseItem());
  }

  removeExpenseItem(index: number): void {
    this.expenseItems.removeAt(index);
  }

  addExchangeRate(): void {
    this.foreignExchange.push(this.createExchangeRate());
  }

  removeExchangeRate(index: number): void {
    this.foreignExchange.removeAt(index);
  }

  calculateTotals(): void {
    // Implement calculation logic here
    let total = 0;
    this.expenseItems.controls.forEach(item => {
      total += parseFloat(item.get('transport')?.value || '0') +
              parseFloat(item.get('accommodation')?.value || '0') +
              parseFloat(item.get('outstation')?.value || '0') +
              parseFloat(item.get('miscellaneous')?.value || '0') +
              parseFloat(item.get('other')?.value || '0');
    });
    
    this.expenseForm.get('totalAmount')?.setValue(total.toFixed(2));
    
    const advanceTaken = parseFloat(this.expenseForm.get('advanceTaken')?.value || '0');
    const creditCardPayment = parseFloat(this.expenseForm.get('creditCardPayment')?.value || '0');
    
    const balance = total - advanceTaken - creditCardPayment;
    this.expenseForm.get('balanceAmount')?.setValue(balance.toFixed(2));
    this.expenseForm.get('debitCredit')?.setValue(balance >= 0 ? 'DEBIT' : 'CREDIT');
  }

  loadClaimData(id: number): void {
    this.loading = true;
    this.expenseService.getClaimById(id).subscribe({
      next: (claim) => {
        // Populate form with existing data
        this.expenseForm.patchValue({
          documentNumber: claim.document_number || '',
          claimForMonthOf: claim.claim_for_month_of || '',
          staffInfo: {
            name: claim.staff_name || '',
            staffType: claim.staff_type || '',
            staffNo: claim.staff_no || '',
            hired: claim.gred || '',
            departmentCode: claim.department_code || '',
            costCenterCode: claim.dept_cost_center_code || '',
            location: claim.location || '',
            telext: claim.tel_ext || ''
          },
          bankDetails: {
            bankName: claim.bank_name || '',
            accountNumber: claim.account_number || '',
            address: '',
            purposeOfClaim: claim.purpose_of_claim || ''
          },
          travelTimes: {
            startTime: claim.start_time_from_home || '',
            arrivalTime: claim.time_of_arrival_at_home || ''
          },
          medicalClaim: {
            isApplying: claim.is_medical_claim || false,
            forFamily: claim.is_for_family || false,
            spouse: claim.family_member_spouse || false,
            children: claim.family_member_children || false,
            other: claim.family_member_other || false
          },
          totalAmount: claim.total_advance_claim_amount || 0,
          advanceTaken: claim.less_advance_taken || 0,
          creditCardPayment: claim.less_corporate_credit_card_payment || 0,
          balanceAmount: claim.balance_claim_repayment || 0,
          debitCredit: 'DEBIT',
          signature: '',
          verifiedBy: '',
          approvedBy: '',
          dateSubmitted: claim.submitted_at || '',
          termsAccepted: false
        });

        // Load expense items
        if (claim.expense_items && claim.expense_items.length > 0) {
          this.expenseItems.clear();
          claim.expense_items.forEach(item => {
            this.expenseItems.push(this.fb.group({
              date: [item.item_date || ''],
              fromTo: [item.claim_or_travel_details || ''],
              mileage: [item.official_mileage_km || 0],
              transport: [item.transport || 0],
              accommodation: [item.hotel_accommodation_allowance || 0],
              outstation: [item.out_station_allowance_meal || 0],
              miscellaneous: [item.miscellaneous_allowance_10_percent || 0],
              other: [item.other_expenses || 0]
            }));
          });
        }

        // Load FX rates
        if (claim.fx_rates && claim.fx_rates.length > 0) {
          this.foreignExchange.clear();
          claim.fx_rates.forEach(rate => {
            this.foreignExchange.push(this.fb.group({
              date: [rate.fx_date || ''],
              currencyType: [rate.type_of_currency || ''],
              sellingRate: [rate.selling_rate_tt_od || ''],
              totalInForeignCurrency: [0]
            }));
          });
        }

        this.loading = false;
      },
      error: (err) => {
        this.toastService.error('Failed to load claim data: ' + (err.error?.message || err.message));
        this.loading = false;
        console.error('Error loading claim:', err);
      }
    });
  }

  onSubmit(): void {
    if (this.expenseForm.invalid) {
      this.markFormGroupTouched(this.expenseForm);
      this.toastService.warning('Please fill in all required fields');
      return;
    }

    this.submitting = true;
    const formData = this.prepareFormData();

    const saveOperation = this.isEditMode && this.claimId
      ? this.expenseService.updateClaim(this.claimId, formData)
      : this.expenseService.createClaim(formData);

    saveOperation.subscribe({
      next: (response) => {
        this.submitting = false;
        const message = this.isEditMode ? 'Claim updated successfully' : 'Claim created successfully';
        this.toastService.success(message);
        this.router.navigate(['/expenses', response.id]);
      },
      error: (err) => {
        this.submitting = false;
        const action = this.isEditMode ? 'update' : 'create';
        this.toastService.error(`Failed to ${action} claim: ` + (err.error?.message || err.message));
        console.error(`Error ${action}ing claim:`, err);
      }
    });
  }

  onSaveDraft(): void {
    this.submitting = true;
    const formData = this.prepareFormData();
    formData.status = 'Draft';

    const saveOperation = this.isEditMode && this.claimId
      ? this.expenseService.updateClaim(this.claimId, formData)
      : this.expenseService.createClaim(formData);

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
      }
    });
  }

  onCancel(): void {
    if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
      this.router.navigate(['/expenses']);
    }
  }

  prepareFormData(): any {
    const formValue = this.expenseForm.value;

    return {
      document_number: formValue.documentNumber,
      claim_for_month_of: formValue.claimForMonthOf,
      staff_name: formValue.staffInfo.name,
      staff_type: formValue.staffInfo.staffType,
      staff_no: formValue.staffInfo.staffNo,
      gred: formValue.staffInfo.hired,
      department_code: formValue.staffInfo.departmentCode,
      dept_cost_center_code: formValue.staffInfo.costCenterCode,
      location: formValue.staffInfo.location,
      tel_ext: formValue.staffInfo.telext,
      bank_name: formValue.bankDetails.bankName,
      account_number: formValue.bankDetails.accountNumber,
      purpose_of_claim: formValue.bankDetails.purposeOfClaim,
      start_time_from_home: formValue.travelTimes.startTime,
      time_of_arrival_at_home: formValue.travelTimes.arrivalTime,
      is_medical_claim: formValue.medicalClaim.isApplying,
      is_for_family: formValue.medicalClaim.forFamily,
      family_member_spouse: formValue.medicalClaim.spouse,
      family_member_children: formValue.medicalClaim.children,
      family_member_other: formValue.medicalClaim.other,
      total_advance_claim_amount: parseFloat(formValue.totalAmount),
      less_advance_taken: parseFloat(formValue.advanceTaken),
      less_corporate_credit_card_payment: parseFloat(formValue.creditCardPayment),
      balance_claim_repayment: parseFloat(formValue.balanceAmount),
      status: 'Pending Verification', // Default status for new submissions
      expense_items: formValue.expenseItems.map((item: any) => ({
        item_date: item.date,
        claim_or_travel_details: item.fromTo,
        official_mileage_km: parseFloat(item.mileage),
        transport: parseFloat(item.transport),
        hotel_accommodation_allowance: parseFloat(item.accommodation),
        out_station_allowance_meal: parseFloat(item.outstation),
        miscellaneous_allowance_10_percent: parseFloat(item.miscellaneous),
        other_expenses: parseFloat(item.other)
      })),
      fx_rates: formValue.foreignExchange.map((rate: any) => ({
        fx_date: rate.date,
        type_of_currency: rate.currencyType,
        selling_rate_tt_od: parseFloat(rate.sellingRate)
      }))
    };
  }

  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();

      if ((control as FormGroup).controls) {
        this.markFormGroupTouched(control as FormGroup);
      }
    });
  }
}
