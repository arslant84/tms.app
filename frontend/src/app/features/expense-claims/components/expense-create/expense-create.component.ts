import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';

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

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initForm();
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

  onSubmit(): void {
    if (this.expenseForm.valid) {
      console.log('Form submitted:', this.expenseForm.value);
      // Add API call to save the form data
    } else {
      // Mark all fields as touched to trigger validation messages
      this.markFormGroupTouched(this.expenseForm);
    }
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
