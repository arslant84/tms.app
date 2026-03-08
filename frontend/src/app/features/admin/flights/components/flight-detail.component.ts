import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { BookingsService, FlightBooking } from '../../../bookings/services/bookings.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-flight-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './flight-detail.component.html',
  styleUrls: ['./flight-detail.component.scss']
})
export class FlightDetailComponent implements OnInit {
  booking: FlightBooking | null = null;
  loading = true;
  error: string | null = null;
  bookingId!: number;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private bookingsService: BookingsService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private appSettingsService: AppSettingsService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    this.bookingId = Number(this.route.snapshot.paramMap.get('id'));
    if (this.bookingId) {
      this.loadBooking();
    }
  }

  loadBooking(): void {
    this.loading = true;
    this.error = null;

    this.bookingsService.getFlightBookingById(this.bookingId).subscribe({
      next: (data) => {
        this.booking = data;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading booking:', error);
        this.error = 'Failed to load booking details. Please try again.';
        this.loading = false;
        this.toastService.error('Failed to load booking details');
      }
    });
  }

  // Status badge helpers
  getStatusBadgeClass(status: string): string {
    // Convert badge- to bg- prefix for compatibility
    return this.statusUtils.getFlightStatusBadgeClass(status).replace('badge-', 'bg-');
  }

  getBookingClassBadgeClass(bookingClass: string): string {
    const classMap: { [key: string]: string } = {
      'ECONOMY': 'bg-secondary',
      'PREMIUM_ECONOMY': 'bg-info',
      'BUSINESS': 'bg-primary',
      'FIRST': 'bg-warning text-dark'
    };
    return classMap[bookingClass] || 'bg-secondary';
  }

  // Action buttons visibility
  canEdit(): boolean {
    return this.booking?.status === 'PENDING' || this.booking?.status === 'REQUESTED';
  }

  canConfirm(): boolean {
    return this.booking?.status === 'REQUESTED' || this.booking?.status === 'PENDING';
  }

  canCancel(): boolean {
    return this.booking?.status === 'PENDING' ||
           this.booking?.status === 'REQUESTED' ||
           this.booking?.status === 'CONFIRMED';
  }

  canDelete(): boolean {
    return this.booking?.status === 'PENDING' || this.booking?.status === 'CANCELLED';
  }

  // Actions
  editBooking(): void {
    this.router.navigate(['/bookings/flights', this.bookingId, 'edit']);
  }

  confirmBooking(): void {
    this.confirmationService.confirm({
      title: 'Confirm Booking',
      message: 'Are you sure you want to confirm this booking?',
      confirmText: 'Confirm',
      type: 'success'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeConfirmBooking();
    });
  }

  private executeConfirmBooking(): void {
    this.bookingsService.confirmFlightBooking(this.bookingId).subscribe({
      next: () => {
        this.toastService.success('Booking confirmed successfully');
        this.loadBooking();
      },
      error: (error) => {
        console.error('Error confirming booking:', error);
        this.toastService.error('Failed to confirm booking');
      }
    });
  }

  cancelBooking(): void {
    const reason = prompt('Please provide a reason for cancellation:');
    if (!reason) return;

    this.bookingsService.cancelFlightBooking(this.bookingId, reason).subscribe({
      next: () => {
        this.toastService.success('Booking cancelled successfully');
        this.loadBooking();
      },
      error: (error) => {
        console.error('Error cancelling booking:', error);
        this.toastService.error('Failed to cancel booking');
      }
    });
  }

  deleteBooking(): void {
    this.confirmationService.confirmDelete('this booking').subscribe(confirmed => {
      if (!confirmed) return;
      this.executeDeleteBooking();
    });
  }

  private executeDeleteBooking(): void {
    this.bookingsService.deleteFlightBooking(this.bookingId).subscribe({
      next: () => {
        this.toastService.success('Booking deleted successfully');
        this.router.navigate(['/bookings/flights']);
      },
      error: (error) => {
        console.error('Error deleting booking:', error);
        this.toastService.error('Failed to delete booking');
      }
    });
  }

  // Format helpers
  formatCurrency(amount: number | null | undefined, currency?: string | null): string {
    if (amount === null || amount === undefined || isNaN(amount)) {
      return 'N/A';
    }

    const currencyCode = currency || this.appSettingsService.getDefaultCurrency();

    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount);
    } catch (error) {
      console.error('Error formatting currency:', error);
      return `${currencyCode} ${amount.toFixed(2)}`;
    }
  }

  formatTime(time: string | undefined): string {
    if (!time) return 'N/A';
    return new Date(time).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
