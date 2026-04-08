import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { TransportService, TransportRequest } from '../../services/transport.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { ListStateService } from '../../../../core/services/list-state.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-transport-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LoadingSpinnerComponent],
  templateUrl: './transport-list.component.html',
  styleUrls: ['./transport-list.component.scss']
})
export class TransportListComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  requests: TransportRequest[] = [];

  // Filters
  statusFilter = '';
  statuses: string[] = [];

  // Sorting
  sortField = 'submittedAt';
  sortDirection: 'asc' | 'desc' = 'desc';

  // Create list state service manually (not via DI)
  listState = new ListStateService({ pageSize: 10 });

  constructor(
    private transportService: TransportService,
    private router: Router,
    private toastService: ToastService,
    private appSettingsService: AppSettingsService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    // Load filter options from actual data
    this.loadFilterOptions();

    // Subscribe to debounced search changes
    this.listState.search$.subscribe(() => {
      this.fetchRequests();
    });

    // Initial load
    this.fetchRequests();
  }

  private loadFilterOptions(): void {
    this.transportService.getAllRequests({ page_size: 1000 }).pipe(takeUntil(this.destroy$)).subscribe({
      next: (response) => {
        const items: TransportRequest[] = Array.isArray(response)
          ? response
          : (response.results ?? []);

        this.statuses = [...new Set(
          items.map(i => i.status ?? '').filter(Boolean)
        )].sort();
      },
      error: () => { /* silently ignore — dropdown stays empty */ }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.listState.destroy();
  }

  fetchRequests(): void {
    this.listState.setLoading(true);
    this.listState.clearError();

    // Add status filter to the request
    const filters = {
      ...this.listState.getFilters(),
      ...(this.statusFilter && { status: this.statusFilter })
    };

    this.transportService.getAllRequests(filters).subscribe({
      next: (response) => {
        // Handle both array and paginated responses
        if (Array.isArray(response)) {
          this.requests = response;
          this.listState.setTotalItems(response.length);
        } else {
          this.requests = response.results || [];
          this.listState.setTotalItems(response.count || 0);
        }
        this.listState.setLoading(false);
      },
      error: (err) => {
        // Handle "Invalid page" error from DRF pagination
        if (err.error?.detail === 'Invalid page.' || err.statusText === 'Not Found') {
          // Reset to first page and retry
          this.listState.resetToFirstPage();
          this.fetchRequests();
          return;
        }

        this.listState.setError('Failed to load transport requests');
        this.listState.setLoading(false);
      }
    });
  }

  onSearchChange(value: string): void {
    this.listState.setSearch(value);
  }

  onStatusFilterChange(): void {
    this.listState.resetToFirstPage();
    this.fetchRequests();
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
    this.listState.nextPage();
    this.fetchRequests();
  }

  previousPage(): void {
    this.listState.previousPage();
    this.fetchRequests();
  }

  goToPage(page: number): void {
    this.listState.setCurrentPage(page);
    this.fetchRequests();
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
    return this.statusUtils.getStatusBadgeClass(status);
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

  // Pagination display helpers
  get startIndex(): number {
    return (this.listState.getCurrentPage() - 1) * this.listState.getPageSize() + 1;
  }

  get endIndex(): number {
    return Math.min(
      this.listState.getCurrentPage() * this.listState.getPageSize(),
      this.listState.getTotalItems()
    );
  }
}
