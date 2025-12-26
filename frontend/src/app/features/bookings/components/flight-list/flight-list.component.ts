import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { BookingsService, FlightBooking } from '../../services/bookings.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

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
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './flight-list.component.html',
  styleUrls: ['./flight-list.component.scss']
})
export class FlightListComponent implements OnInit {
  bookings: FlightBooking[] = [];
  isLoading = false;

  // Filters
  searchTerm = '';
  filterStatus = '';
  filterClass = '';

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalBookings = 0;
  totalPages = 1;

  // Constants for template
  statuses = FLIGHT_STATUSES;
  bookingClasses = BOOKING_CLASSES;
  Math = Math; // Expose Math to template

  private searchSubject = new Subject<string>();

  constructor(
    private bookingsService: BookingsService,
    private router: Router,
    private toastService: ToastService,
    private appSettingsService: AppSettingsService
  ) {}

  ngOnInit(): void {
    this.setupSearch();
    this.fetchBookings();
  }

  setupSearch(): void {
    this.searchSubject.pipe(
      debounceTime(500),
      distinctUntilChanged()
    ).subscribe(searchTerm => {
      this.searchTerm = searchTerm;
      this.resetToFirstPage();
      this.fetchBookings();
    });
  }

  onSearchChange(term: string): void {
    this.searchSubject.next(term);
  }

  fetchBookings(): void {
    this.isLoading = true;
    const filters: any = {
      page: this.currentPage,
      page_size: this.pageSize
    };

    if (this.filterStatus) {
      filters.status = this.filterStatus;
    }

    this.bookingsService.getAllFlightBookings(filters).subscribe({
      next: (response) => {
        this.bookings = Array.isArray(response) ? response : response.results || [];
        this.totalBookings = response.count || this.bookings.length;
        this.totalPages = Math.ceil(this.totalBookings / this.pageSize);
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error fetching bookings:', err);
        this.toastService.error('Failed to load flight bookings');
        this.isLoading = false;
      }
    });
  }

  onFilterChange(): void {
    this.resetToFirstPage();
    this.fetchBookings();
  }

  resetToFirstPage(): void {
    this.currentPage = 1;
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
    if (confirm('Are you sure you want to delete this flight booking?')) {
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
  }

  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'PENDING': return 'badge-secondary';
      case 'REQUESTED': return 'badge-warning';
      case 'CONFIRMED': return 'badge-success';
      case 'TICKETED': return 'badge-primary';
      case 'CANCELLED': return 'badge-danger';
      case 'REFUNDED': return 'badge-info';
      case 'NO_SHOW': return 'badge-dark';
      default: return 'badge-secondary';
    }
  }

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

  formatDateTime(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  formatRoute(booking: FlightBooking): string {
    const dep = booking.departure_airport_code || booking.departure_airport;
    const arr = booking.arrival_airport_code || booking.arrival_airport;
    return `${dep} → ${arr}`;
  }

  // Pagination
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.fetchBookings();
    }
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.fetchBookings();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.fetchBookings();
    }
  }

  get paginationPages(): number[] {
    const pages: number[] = [];
    const maxPagesToShow = 5;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(this.totalPages, startPage + maxPagesToShow - 1);

    if (endPage - startPage + 1 < maxPagesToShow) {
      startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    return pages;
  }
}
