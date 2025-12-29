import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { TransportService, TransportRequest } from '../../services/transport.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';

// Status constants for filtering (broad categories to match workflow statuses)
export const TRANSPORT_STATUSES = [
  'Draft',
  'Pending', // Matches "Pending", "Pending Line Manager", "Pending Department Focal", etc.
  'Approved',
  'Rejected',
  'Completed',
  'Cancelled'
];

@Component({
  selector: 'app-transport-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './transport-list.component.html',
  styleUrls: ['./transport-list.component.scss']
})
export class TransportListComponent implements OnInit, OnDestroy {
  requests: TransportRequest[] = [];
  loading = false;
  error = '';

  // Filters
  searchTerm = '';
  statusFilter = '';
  statuses = TRANSPORT_STATUSES;

  // Pagination
  currentPage = 1;
  pageSize = 10;
  totalRequests = 0;

  // Sorting
  sortField = 'submittedAt';
  sortDirection: 'asc' | 'desc' = 'desc';

  private searchSubject = new Subject<string>();
  private destroy$ = new Subject<void>();

  constructor(
    private transportService: TransportService,
    private router: Router,
    private toastService: ToastService,
    private appSettingsService: AppSettingsService,
    public dateUtils: DateUtilsService
  ) {}

  ngOnInit(): void {
    // Setup debounced search
    this.searchSubject.pipe(
      debounceTime(500),
      distinctUntilChanged()
    ).subscribe(searchTerm => {
      this.searchTerm = searchTerm;
      this.resetToFirstPage();
      this.fetchRequests();
    });

    this.fetchRequests();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  fetchRequests(): void {
    this.loading = true;
    this.error = '';

    const filters = {
      status: this.statusFilter,
      search: this.searchTerm,
      page: this.currentPage,
      page_size: this.pageSize
    };

    this.transportService.getAllRequests(filters).subscribe({
      next: (response) => {
        // Handle both array and paginated responses
        if (Array.isArray(response)) {
          this.requests = response;
          this.totalRequests = response.length;
        } else {
          this.requests = response.results || [];
          this.totalRequests = response.count || 0;
        }
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load transport requests';
        this.loading = false;
      }
    });
  }

  onSearchChange(value: string): void {
    this.searchSubject.next(value);
  }

  onStatusFilterChange(): void {
    this.resetToFirstPage();
    this.fetchRequests();
  }

  resetToFirstPage(): void {
    this.currentPage = 1;
  }

  onSort(field: string): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.fetchRequests();
  }

  nextPage(): void {
    if (this.currentPage * this.pageSize < this.totalRequests) {
      this.currentPage++;
      this.fetchRequests();
    }
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.fetchRequests();
    }
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.fetchRequests();
    }
  }

  getPageNumbers(): number[] {
    const maxPagesToShow = 5;
    const pages: number[] = [];

    if (this.totalPages <= maxPagesToShow) {
      for (let i = 1; i <= this.totalPages; i++) {
        pages.push(i);
      }
    } else {
      const half = Math.floor(maxPagesToShow / 2);
      let start = Math.max(1, this.currentPage - half);
      let end = Math.min(this.totalPages, start + maxPagesToShow - 1);

      if (end - start < maxPagesToShow - 1) {
        start = Math.max(1, end - maxPagesToShow + 1);
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
    }

    return pages;
  }

  navigateToCreate(): void {
    this.router.navigate(['/transport/create']);
  }

  navigateToView(id: number | string): void {
    this.router.navigate(['/transport', id]);
  }

  navigateToEdit(id: number | string): void {
    this.router.navigate(['/transport/edit', id]);
  }

  private deleteConfirmId: number | string | null = null;
  private deleteConfirmTimeout: any = null;

  deleteRequest(id: number | string, event: Event): void {
    event.stopPropagation();

    // If this is the second click on the same item within 3 seconds, proceed with deletion
    if (this.deleteConfirmId === id) {
      clearTimeout(this.deleteConfirmTimeout);
      this.deleteConfirmId = null;

      this.transportService.deleteRequest(id).subscribe({
        next: () => {
          this.toastService.success('Transport request deleted successfully');
          this.fetchRequests();
        },
        error: (error) => {
          this.toastService.error('Failed to delete transport request');
        }
      });
    } else {
      // First click - show confirmation toast
      this.deleteConfirmId = id;
      this.toastService.warning('Click delete again to confirm deletion');

      // Reset confirmation after 3 seconds
      this.deleteConfirmTimeout = setTimeout(() => {
        this.deleteConfirmId = null;
      }, 3000);
    }
  }

  getStatusClass(status: string): string {
    const lowerStatus = status.toLowerCase();
    if (lowerStatus.includes('approved') || lowerStatus.includes('completed')) {
      return 'badge-success';
    }
    if (lowerStatus.includes('rejected')) {
      return 'badge-danger';
    }
    if (lowerStatus.includes('pending')) {
      return 'badge-warning';
    }
    if (lowerStatus.includes('cancelled')) {
      return 'badge-secondary';
    }
    if (lowerStatus.includes('draft')) {
      return 'badge-secondary';
    }
    return 'badge-info';
  }


  getTotalPassengers(request: TransportRequest): number {
    if (!request.transportDetails || request.transportDetails.length === 0) return 0;
    return request.transportDetails.reduce((sum, detail) => sum + (detail.numberOfPassengers || 0), 0);
  }

  getFirstTransportType(request: TransportRequest): string {
    if (!request.transportDetails || request.transportDetails.length === 0) return 'N/A';
    return request.transportDetails[0].transportType || 'N/A';
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
      return `${currencyCode} ${amount.toFixed(2)}`;
    }
  }

  get totalPages(): number {
    return Math.ceil(this.totalRequests / this.pageSize);
  }

  get startIndex(): number {
    return (this.currentPage - 1) * this.pageSize + 1;
  }

  get endIndex(): number {
    return Math.min(this.currentPage * this.pageSize, this.totalRequests);
  }
}
