import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { AccommodationService, AccommodationRequest } from '../../services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';

export const ACCOMMODATION_STATUSES = [
  'Draft',
  'Pending',
  'Approved',
  'Rejected',
  'Confirmed',
  'Checked-in',
  'Checked-out',
  'Cancelled'
];

@Component({
  selector: 'app-accommodation-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './accommodation-list.component.html',
  styleUrls: ['./accommodation-list.component.scss']
})
export class AccommodationListComponent implements OnInit, OnDestroy {
  requests: AccommodationRequest[] = [];
  loading = false;
  error = '';

  searchTerm = '';
  statusFilter = '';
  statuses = ACCOMMODATION_STATUSES;

  currentPage = 1;
  pageSize = 10;
  totalRequests = 0;

  sortField = 'created_at';
  sortDirection: 'asc' | 'desc' = 'desc';

  private searchSubject = new Subject<string>();
  private destroy$ = new Subject<void>();

  constructor(
    private accommodationService: AccommodationService,
    private router: Router,
    private toastService: ToastService,
    private appSettingsService: AppSettingsService
  ) {}

  ngOnInit(): void {
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

    this.accommodationService.getAllRequests(filters).subscribe({
      next: (response) => {
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
        this.error = 'Failed to load accommodation requests';
        this.loading = false;
        console.error('Error fetching requests:', err);
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
    this.router.navigate(['/accommodation/create']);
  }

  navigateToView(id: number): void {
    this.router.navigate(['/accommodation', id]);
  }

  navigateToEdit(id: number): void {
    this.router.navigate(['/accommodation/edit', id]);
  }

  deleteRequest(id: number, event: Event): void {
    event.stopPropagation();
    if (confirm('Are you sure you want to delete this accommodation request?')) {
      this.accommodationService.deleteRequest(id).subscribe({
        next: () => {
          this.toastService.success('Accommodation request deleted successfully');
          this.fetchRequests();
        },
        error: (error) => {
          console.error('Error deleting accommodation request:', error);
          this.toastService.error('Failed to delete accommodation request');
        }
      });
    }
  }

  getStatusClass(status: string): string {
    const lowerStatus = status.toLowerCase();
    if (lowerStatus.includes('approved') || lowerStatus.includes('confirmed') || lowerStatus.includes('checked-out')) {
      return 'badge-success';
    }
    if (lowerStatus.includes('rejected')) {
      return 'badge-danger';
    }
    if (lowerStatus.includes('pending') || lowerStatus.includes('checked-in')) {
      return 'badge-warning';
    }
    if (lowerStatus.includes('cancelled') || lowerStatus.includes('draft')) {
      return 'badge-secondary';
    }
    return 'badge-info';
  }

  formatDate(dateString: string): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  formatCurrency(amount: number | undefined): string {
    if (!amount && amount !== 0) return '$0.00';
    const currency = this.appSettingsService.getDefaultCurrency();
    return new Intl.NumberFormat('en-MY', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  canEdit(request: AccommodationRequest): boolean {
    const status = request.status.toLowerCase();
    return status.includes('draft') || status.includes('pending');
  }

  canDelete(request: AccommodationRequest): boolean {
    const status = request.status.toLowerCase();
    return status.includes('draft') || status.includes('rejected') || status.includes('cancelled');
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
