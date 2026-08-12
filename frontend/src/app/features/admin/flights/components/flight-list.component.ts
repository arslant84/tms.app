import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { BookingsService, FlightBooking } from '../../../bookings/services/bookings.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { ListStateService } from '../../../../core/services/list-state.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

export const FLIGHT_STATUSES = [
  'PENDING',
  'REQUESTED',
  'CONFIRMED',
  'TICKETED',
  'CANCELLED',
  'REFUNDED',
  'NO_SHOW'
];

export const BOOKING_CLASSES = [
  { value: 'ECONOMY', label: 'Economy' },
  { value: 'PREMIUM_ECONOMY', label: 'Premium Economy' },
  { value: 'BUSINESS', label: 'Business' },
  { value: 'FIRST', label: 'First Class' }
];

@Component({
  selector: 'app-flight-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './flight-list.component.html',
  styleUrls: ['./flight-list.component.scss']
})
export class FlightListComponent implements OnInit, OnDestroy {
  bookings: FlightBooking[] = [];

  // Filters
  filterStatus = '';
  filterClass = '';

  // Constants for template
  statuses = FLIGHT_STATUSES;
  bookingClasses = BOOKING_CLASSES;
  Math = Math; // Expose Math to template

  // Create list state service manually (not via DI)
  listState = new ListStateService({ pageSize: 20 });

  constructor(
    private bookingsService: BookingsService,
    private router: Router,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    // Subscribe to debounced search changes
    this.listState.search$.subscribe(() => {
      this.fetchBookings();
    });

    // Initial load
    this.fetchBookings();
  }

  ngOnDestroy(): void {
    this.listState.destroy();
  }

  onSearchChange(term: string): void {
    this.listState.setSearch(term);
  }

  fetchBookings(): void {
    this.listState.setLoading(true);
    this.listState.clearError();

    // Add status filter to the request
    const filters = {
      ...this.listState.getFilters(),
      ...(this.filterStatus && { status: this.filterStatus })
    };

    this.bookingsService.getAllFlightBookings(filters).subscribe({
      next: (response) => {
        this.bookings = Array.isArray(response) ? response : response.results || [];
        this.listState.setTotalItems(response.count || this.bookings.length);
        this.listState.setLoading(false);
      },
      error: (err) => {
        // Handle "Invalid page" error from DRF pagination
        if (err.error?.detail === 'Invalid page.' || err.statusText === 'Not Found') {
          // Reset to first page and retry
          this.listState.resetToFirstPage();
          this.fetchBookings();
          return;
        }

        console.error('Error fetching bookings:', err);
        this.listState.setError('Failed to load flight bookings');
        this.listState.setLoading(false);
      }
    });
  }

  onFilterChange(): void {
    this.listState.resetToFirstPage();
    this.fetchBookings();
  }

  navigateToCreate(): void {
    this.router.navigate(['/bookings/flights/create']);
  }

  navigateToDetail(id: number): void {
    this.router.navigate(['/bookings/flights', id]);
  }

  navigateToEdit(id: number, event: Event): void {
    event.stopPropagation();
    this.router.navigate(['/bookings/flights/edit', id]);
  }

  deleteBooking(id: number, event: Event): void {
    event.stopPropagation();
    this.confirmationService.confirmDelete('this flight booking').subscribe(confirmed => {
      if (confirmed) {
        this.bookingsService.deleteFlightBooking(id).subscribe({
          next: () => {
            this.toastService.success('Flight booking deleted successfully');
            this.fetchBookings();
          },
          error: (err) => {
            console.error('Error deleting booking:', err);
            this.toastService.error('Failed to delete flight booking');
          }
        });
      }
    });
  }

  getStatusBadgeClass(status: string): string {
    return this.statusUtils.getFlightStatusBadgeClass(status);
  }

  formatRoute(booking: FlightBooking): string {
    const dep = booking.departure_airport_code || booking.departure_airport;
    const arr = booking.arrival_airport_code || booking.arrival_airport;
    return `${dep} → ${arr}`;
  }

  // Pagination
  goToPage(page: number): void {
    this.listState.setCurrentPage(page);
    this.fetchBookings();
  }

  previousPage(): void {
    this.listState.previousPage();
    this.fetchBookings();
  }

  nextPage(): void {
    this.listState.nextPage();
    this.fetchBookings();
  }
}
