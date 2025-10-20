import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { TransportService, TransportRequest } from '../../services/transport.service';

// Status constants matching backend
export const TRANSPORT_STATUSES = [
  'Draft',
  'Pending',
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
    private router: Router
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
        console.error('Error fetching transport requests:', err);
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

  navigateToCreate(): void {
    this.router.navigate(['/transport/create']);
  }

  navigateToView(id: number | string): void {
    this.router.navigate(['/transport', id]);
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

  formatDate(dateString: string | Date | undefined): string {
    if (!dateString) return 'N/A';
    const date = dateString instanceof Date ? dateString : new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  getTotalPassengers(request: TransportRequest): number {
    if (!request.transportDetails || request.transportDetails.length === 0) return 0;
    return request.transportDetails.reduce((sum, detail) => sum + (detail.numberOfPassengers || 0), 0);
  }

  formatCurrency(amount: number, currency: string = 'USD'): string {
    if (!amount && amount !== 0) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
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
