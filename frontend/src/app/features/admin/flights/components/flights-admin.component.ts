import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { BookingsService, FlightBooking } from '../../../bookings/services/bookings.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-flights-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './flights-admin.component.html',
  styleUrl: './flights-admin.component.scss'
})
export class FlightsAdminComponent implements OnInit {
  bookings: FlightBooking[] = [];
  filteredBookings: FlightBooking[] = [];
  selectedBooking: FlightBooking | null = null;

  // Filter criteria
  filterCriteria = {
    status: 'all',
    bookingClass: 'all',
    search: '',
    dateFrom: '',
    dateTo: ''
  };

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalBookings = 0;

  // Loading states
  loading: boolean = true;
  error: string = '';
  processingId: number | null = null;

  // Issue ticket modal
  showIssueTicketModal: boolean = false;
  ticketNumber: string = '';

  // Status options for filter
  statusOptions = [
    { value: 'all', label: 'All Statuses' },
    { value: 'PENDING', label: 'Pending' },
    { value: 'REQUESTED', label: 'Requested' },
    { value: 'CONFIRMED', label: 'Confirmed' },
    { value: 'TICKETED', label: 'Ticketed' },
    { value: 'CANCELLED', label: 'Cancelled' },
    { value: 'REFUNDED', label: 'Refunded' },
    { value: 'NO_SHOW', label: 'No Show' }
  ];

  // Booking class options
  bookingClassOptions = [
    { value: 'all', label: 'All Classes' },
    { value: 'ECONOMY', label: 'Economy' },
    { value: 'PREMIUM_ECONOMY', label: 'Premium Economy' },
    { value: 'BUSINESS', label: 'Business' },
    { value: 'FIRST', label: 'First Class' }
  ];

  constructor(
    private bookingsService: BookingsService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private router: Router,
    private appSettingsService: AppSettingsService,
    public dateUtils: DateUtilsService
  ) {}

  ngOnInit(): void {
    this.loadBookings();
  }

  /**
   * Load flight bookings from API
   */
  loadBookings(): void {
    this.loading = true;
    this.error = '';

    const filters: any = {
      page: this.currentPage,
      page_size: this.pageSize
    };

    if (this.filterCriteria.status !== 'all') {
      filters.status = this.filterCriteria.status;
    }

    this.bookingsService.getAllFlightBookings(filters).subscribe({
      next: (response) => {
        this.bookings = response.results || response;
        this.totalBookings = response.count || this.bookings.length;
        this.applyLocalFilters();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load flight bookings: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading bookings:', err);
      }
    });
  }

  /**
   * Apply local filters (search and date range)
   */
  applyLocalFilters(): void {
    this.filteredBookings = this.bookings.filter(booking => {
      // Search filter
      if (this.filterCriteria.search) {
        const search = this.filterCriteria.search.toLowerCase();
        const matchesSearch =
          booking.booking_reference.toLowerCase().includes(search) ||
          booking.airline.toLowerCase().includes(search) ||
          booking.flight_number.toLowerCase().includes(search) ||
          (booking.departure_airport && booking.departure_airport.toLowerCase().includes(search)) ||
          (booking.arrival_airport && booking.arrival_airport.toLowerCase().includes(search));

        if (!matchesSearch) return false;
      }

      // Booking class filter
      if (this.filterCriteria.bookingClass !== 'all' && booking.booking_class !== this.filterCriteria.bookingClass) {
        return false;
      }

      // Date range filter
      if (this.filterCriteria.dateFrom && booking.departure_time) {
        const bookingDate = new Date(booking.departure_time);
        const fromDate = new Date(this.filterCriteria.dateFrom);
        if (bookingDate < fromDate) return false;
      }

      if (this.filterCriteria.dateTo && booking.departure_time) {
        const bookingDate = new Date(booking.departure_time);
        const toDate = new Date(this.filterCriteria.dateTo);
        if (bookingDate > toDate) return false;
      }

      return true;
    });
  }

  /**
   * Apply filters
   */
  applyFilters(): void {
    this.currentPage = 1;
    this.loadBookings();
  }

  /**
   * Reset filters
   */
  resetFilters(): void {
    this.filterCriteria = {
      status: 'all',
      bookingClass: 'all',
      search: '',
      dateFrom: '',
      dateTo: ''
    };
    this.currentPage = 1;
    this.loadBookings();
  }

  /**
   * Change page
   */
  changePage(page: number): void {
    this.currentPage = page;
    this.loadBookings();
  }

  /**
   * View booking details
   */
  viewBooking(booking: FlightBooking): void {
    this.router.navigate(['/bookings/flights', booking.id]);
  }

  /**
   * Open issue ticket modal
   */
  openIssueTicketModal(booking: FlightBooking): void {
    this.selectedBooking = booking;
    this.ticketNumber = '';
    this.showIssueTicketModal = true;
  }

  /**
   * Close issue ticket modal
   */
  closeIssueTicketModal(): void {
    this.showIssueTicketModal = false;
    this.selectedBooking = null;
    this.ticketNumber = '';
  }

  /**
   * Issue ticket to booking
   */
  issueTicket(): void {
    if (!this.selectedBooking) return;

    if (!this.ticketNumber || this.ticketNumber.trim() === '') {
      this.toastService.error('Please enter a ticket number');
      return;
    }

    this.processingId = this.selectedBooking.id;

    this.bookingsService.issueTicket(this.selectedBooking.id, this.ticketNumber).subscribe({
      next: () => {
        this.toastService.success('Ticket issued successfully');
        this.closeIssueTicketModal();
        this.processingId = null;
        this.loadBookings();
      },
      error: (err) => {
        this.toastService.error('Failed to issue ticket: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error issuing ticket:', err);
      }
    });
  }

  /**
   * Confirm booking
   */
  confirmBooking(booking: FlightBooking): void {
    this.confirmationService.confirm({
      title: 'Confirm Booking',
      message: `Are you sure you want to confirm booking #${booking.booking_reference}?`,
      confirmText: 'Confirm',
      type: 'success'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeConfirmBooking(booking);
    });
  }

  private executeConfirmBooking(booking: FlightBooking): void {
    this.processingId = booking.id;

    this.bookingsService.confirmFlightBooking(booking.id).subscribe({
      next: () => {
        this.toastService.success('Booking confirmed successfully');
        this.processingId = null;
        this.loadBookings();
      },
      error: (err) => {
        this.toastService.error('Failed to confirm booking: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error confirming booking:', err);
      }
    });
  }

  /**
   * Cancel booking
   */
  cancelBooking(booking: FlightBooking): void {
    const reason = prompt('Please provide a reason for cancellation:');

    if (!reason || reason.trim() === '') {
      this.toastService.error('Cancellation reason is required');
      return;
    }

    this.processingId = booking.id;

    this.bookingsService.cancelFlightBooking(booking.id, reason).subscribe({
      next: () => {
        this.toastService.success('Booking cancelled successfully');
        this.processingId = null;
        this.loadBookings();
      },
      error: (err) => {
        this.toastService.error('Failed to cancel booking: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error cancelling booking:', err);
      }
    });
  }

  /**
   * Get status badge class
   */
  getStatusClass(status: string): string {
    const statusUpper = status.toUpperCase();
    if (statusUpper === 'TICKETED') return 'badge bg-success';
    if (statusUpper === 'CONFIRMED') return 'badge bg-info';
    if (statusUpper === 'REQUESTED') return 'badge bg-primary';
    if (statusUpper === 'CANCELLED' || statusUpper === 'REFUNDED' || statusUpper === 'NO_SHOW') return 'badge bg-danger';
    if (statusUpper === 'PENDING') return 'badge bg-warning';
    return 'badge bg-secondary';
  }

  /**
   * Get booking class badge
   */
  getBookingClassBadge(bookingClass: string): string {
    const classUpper = bookingClass.toUpperCase();
    if (classUpper === 'FIRST') return 'badge bg-warning text-dark';
    if (classUpper === 'BUSINESS') return 'badge bg-info';
    if (classUpper === 'PREMIUM_ECONOMY') return 'badge bg-primary';
    if (classUpper === 'ECONOMY') return 'badge bg-secondary';
    return 'badge bg-secondary';
  }

  /**
   * Format currency
   */
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

  /**
   * Format route
   */
  formatRoute(booking: FlightBooking): string {
    const from = booking.departure_airport_code || booking.departure_airport;
    const to = booking.arrival_airport_code || booking.arrival_airport;
    return `${from} → ${to}`;
  }

  /**
   * Check if booking can be confirmed
   */
  canConfirm(booking: FlightBooking): boolean {
    return booking.status === 'PENDING' || booking.status === 'REQUESTED';
  }

  /**
   * Check if ticket can be issued
   */
  canIssueTicket(booking: FlightBooking): boolean {
    return booking.status === 'CONFIRMED';
  }

  /**
   * Check if booking can be cancelled
   */
  canCancel(booking: FlightBooking): boolean {
    return booking.status !== 'CANCELLED' && booking.status !== 'REFUNDED' && booking.status !== 'NO_SHOW';
  }

  /**
   * Check if booking is processing
   */
  isProcessing(bookingId: number): boolean {
    return this.processingId === bookingId;
  }

  /**
   * Get total pages
   */
  get totalPages(): number {
    return Math.ceil(this.totalBookings / this.pageSize);
  }

  /**
   * Get page numbers for pagination
   */
  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxPages = 5;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxPages / 2));
    let endPage = Math.min(this.totalPages, startPage + maxPages - 1);

    if (endPage - startPage + 1 < maxPages) {
      startPage = Math.max(1, endPage - maxPages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    return pages;
  }
}
