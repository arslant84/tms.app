import { Component, EventEmitter, Input, OnInit, OnChanges, SimpleChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';

export interface ExternalPartiesDetails {
  purpose: string;
  externalFullName: string;
  externalOrganization: string;
  externalRefToAuthorityLetter?: string;
  externalCostCenter: string;
  itinerary: any[];
  accommodation: any[];
  transport: any[];
}

@Component({
  selector: 'app-external-parties-details',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './external-parties-details.component.html',
  styleUrls: ['./external-parties-details.component.scss']
})
export class ExternalPartiesDetailsComponent implements OnInit, OnChanges {
  @Input() initialData: Partial<ExternalPartiesDetails> = {};
  @Output() formSubmit = new EventEmitter<ExternalPartiesDetails>();

  externalForm!: FormGroup;
  weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initForm();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // When initialData changes (e.g., loaded from API in edit mode), rebuild the form
    if (changes['initialData'] && !changes['initialData'].firstChange && this.externalForm) {
      this.initForm();  // Rebuild form with new data
    }
  }

  private initForm(): void {
    this.externalForm = this.fb.group({
      purpose: [this.initialData.purpose || '', [Validators.required, Validators.minLength(10)]],
      externalFullName: [this.initialData.externalFullName || '', Validators.required],
      externalOrganization: [this.initialData.externalOrganization || '', Validators.required],
      externalRefToAuthorityLetter: [this.initialData.externalRefToAuthorityLetter || ''],
      externalCostCenter: [this.initialData.externalCostCenter || '', Validators.required],
      itinerary: this.fb.array([]),
      accommodation: this.fb.array([]),
      transport: this.fb.array([])
    });

    // Initialize itinerary from initialData or add one empty entry
    if (this.initialData.itinerary && this.initialData.itinerary.length > 0) {
      this.initialData.itinerary.forEach(segment => this.addItinerarySegment(segment));
    } else {
      this.addItinerarySegment();
    }

    // Initialize accommodation from initialData or add one empty entry
    if (this.initialData.accommodation && this.initialData.accommodation.length > 0) {
      this.initialData.accommodation.forEach(acc => this.addAccommodation(acc));
    } else {
      this.addAccommodation();
    }

    // Initialize transport from initialData or add one empty entry
    if (this.initialData.transport && this.initialData.transport.length > 0) {
      this.initialData.transport.forEach(trans => this.addTransport(trans));
    } else {
      this.addTransport();
    }
  }

  get accommodation(): FormArray {
    return this.externalForm.get('accommodation') as FormArray;
  }

  get transport(): FormArray {
    return this.externalForm.get('transport') as FormArray;
  }

  private createAccommodation(): FormGroup {
    return this.fb.group({
      fromDate: ['', Validators.required],
      toDate: ['', Validators.required],
      fromLocation: ['', Validators.required],
      toLocation: ['', Validators.required],
      accommodationType: ['', Validators.required],
      address: [''],
      remarks: ['']
    });
  }

  private createTransport(): FormGroup {
    return this.fb.group({
      date: ['', Validators.required],
      fromLocation: ['', Validators.required],
      toLocation: ['', Validators.required],
      btNoRequired: [''],
      remarks: ['']
    });
  }

  addAccommodation(): void {
    this.accommodation.push(this.createAccommodation());
  }

  removeAccommodation(index: number): void {
    if (this.accommodation.length > 1) {
      this.accommodation.removeAt(index);
    }
  }

  addTransport(): void {
    this.transport.push(this.createTransport());
  }

  removeTransport(index: number): void {
    if (this.transport.length > 1) {
      this.transport.removeAt(index);
    }
  }

  onSubmit(): void {
    if (this.externalForm.valid) {
      const formValue = this.externalForm.getRawValue();
      this.formSubmit.emit(formValue);
    } else {
      this.markFormGroupTouched(this.externalForm);
    }
  }

  // Public methods for wizard integration
  getFormData(): ExternalPartiesDetails {
    return this.externalForm.getRawValue();
  }

  isValid(): boolean {
    return this.externalForm.valid;
  }

  markAllAsTouched(): void {
    this.markFormGroupTouched(this.externalForm);
  }

  private markFormGroupTouched(formGroup: FormGroup | FormArray): void {
    Object.values(formGroup.controls).forEach(control => {
      control.markAsTouched();
      if (control instanceof FormGroup || control instanceof FormArray) {
        this.markFormGroupTouched(control);
      }
    });
  }
}
