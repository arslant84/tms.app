import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { BookingsService, FlightBooking } from '../../services/bookings.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';

@Component({
  selector: 'app-flight-create',
  standalone: true,
  imports: [CommonModule, RouterModule, ReactiveFormsModule],
  templateUrl: './flight-create.component.html',
  styleUrls: ['./flight-create.component.scss']
})
export class FlightCreateComponent implements OnInit {
  flightForm!: FormGroup;
  loading = false;
  submitting = false;
  isEditMode = false;
  bookingId: number | null = null;

  // Dropdown options
  flightTypes = [
    { value: 'ONE_WAY', label: 'One Way' },
    { value: 'ROUND_TRIP', label: 'Round Trip' },
    { value: 'MULTI_CITY', label: 'Multi-City' }
  ];

  bookingClasses = [
    { value: 'ECONOMY', label: 'Economy' },
    { value: 'PREMIUM_ECONOMY', label: 'Premium Economy' },
    { value: 'BUSINESS', label: 'Business' },
    { value: 'FIRST', label: 'First Class' }
  ];

  statuses = [
    { value: 'PENDING', label: 'Pending' },
    { value: 'REQUESTED', label: 'Requested' },
    { value: 'CONFIRMED', label: 'Confirmed' },
    { value: 'TICKETED', label: 'Ticketed' },
    { value: 'CANCELLED', label: 'Cancelled' },
    { value: 'REFUNDED', label: 'Refunded' },
    { value: 'NO_SHOW', label: 'No Show' }
  ];

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private bookingsService: BookingsService,
    private toastService: ToastService,
    private appSettingsService: AppSettingsService
  ) {}

  ngOnInit(): void {
    this.initializeForm();

    // Check if edit mode
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.bookingId = Number(id);
      this.loadBooking();
    }
  }

  initializeForm(): void {
    this.flightForm = this.fb.group({
      // Required fields
      trf: ['', Validators.required],
      user: ['', Validators.required],
      flight_type: ['ONE_WAY', Validators.required],
      airline: ['', Validators.required],
      flight_number: ['', Validators.required],
      departure_airport: ['', Validators.required],
      arrival_airport: ['', Validators.required],
      departure_time: ['', Validators.required],
      arrival_time: ['', Validators.required],
      booking_class: ['ECONOMY', Validators.required],
      status: ['PENDING', Validators.required],
      booking_reference: ['', Validators.required],
      cost: [0, [Validators.required, Validators.min(0)]],
      currency: [this.appSettingsService.getDefaultCurrency(), Validators.required],
      tax_amount: [0, [Validators.required, Validators.min(0)]],

      // Optional fields
      airline_code: [''],
      departure_airport_code: [''],
      arrival_airport_code: [''],
      departure_terminal: [''],
      arrival_terminal: [''],
      seat_number: [''],
      ticket_number: [''],
      baggage_allowance: [''],
      carry_on_allowance: [''],
      meal_preference: [''],
      special_requests: [''],
      booked_by: [''],
      booking_date: [''],
      confirmation_date: [''],
      ticketing_date: [''],
      cancellation_date: [''],
      cancellation_reason: [''],
      notes: ['']
    });
  }

  loadBooking(): void {
    if (!this.bookingId) return;

    this.loading = true;
    this.bookingsService.getFlightBookingById(this.bookingId).subscribe({
      next: (booking) => {
        this.flightForm.patchValue(booking);
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading booking:', error);
        this.toastService.error('Failed to load booking details');
        this.loading = false;
        this.router.navigate(['/bookings/flights']);
      }
    });
  }

  onSubmit(): void {
    if (this.flightForm.invalid) {
      this.toastService.warning('Please fill in all required fields');
      Object.keys(this.flightForm.controls).forEach(key => {
        const control = this.flightForm.get(key);
        if (control?.invalid) {
          control.markAsTouched();
        }
      });
      return;
    }

    this.submitting = true;
    const formData = this.flightForm.value;

    const request = this.isEditMode && this.bookingId
      ? this.bookingsService.updateFlightBooking(this.bookingId, formData)
      : this.bookingsService.createFlightBooking(formData);

    request.subscribe({
      next: (response) => {
        const action = this.isEditMode ? 'updated' : 'created';
        this.toastService.success(`Flight booking ${action} successfully`);
        this.router.navigate(['/bookings/flights', response.id]);
      },
      error: (error) => {
        console.error('Error saving booking:', error);
        this.toastService.error('Failed to save flight booking');
        this.submitting = false;
      }
    });
  }

  saveDraft(): void {
    this.flightForm.patchValue({ status: 'PENDING' });
    this.onSubmit();
  }

  cancel(): void {
    if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
      this.router.navigate(['/bookings/flights']);
    }
  }

  // Validation helpers
  isFieldInvalid(fieldName: string): boolean {
    const field = this.flightForm.get(fieldName);
    return !!(field && field.invalid && field.touched);
  }

  getFieldError(fieldName: string): string {
    const field = this.flightForm.get(fieldName);
    if (field?.errors) {
      if (field.errors['required']) return 'This field is required';
      if (field.errors['min']) return `Minimum value is ${field.errors['min'].min}`;
      if (field.errors['email']) return 'Invalid email format';
    }
    return '';
  }
}
