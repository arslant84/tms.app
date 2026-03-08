import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AccommodationService, AccommodationRequest } from '../../services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { ListStateService } from '../../../../core/services/list-state.service';

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
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './accommodation-list.component.html',
  styleUrls: ['./accommodation-list.component.scss']
})
export class AccommodationListComponent implements OnInit, OnDestroy {
  requests: AccommodationRequest[] = [];
  statuses = ACCOMMODATION_STATUSES;

  statusFilter = '';
  sortField = 'created_at';
  sortDirection: 'asc' | 'desc' = 'desc';

  // Create list state service manually (not via DI)
  listState = new ListStateService({ pageSize: 10 });

  constructor(
    private accommodationService: AccommodationService,
    private router: Router,
    private toastService: ToastService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    // Subscribe to debounced search changes
    this.listState.search$.subscribe(() => {
      this.fetchRequests();
    });

    // Initial load
    this.fetchRequests();
  }

  ngOnDestroy(): void {
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

    this.accommodationService.getAllRequests(filters).subscribe({
      next: (response) => {
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

        this.listState.setError('Failed to load accommodation requests');
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
    this.router.navigate(['/accommodation/create']);
  }

  navigateToView(id: number): void {
    this.router.navigate(['/accommodation', id]);
  }

  navigateToEdit(id: number): void {
    this.router.navigate(['/accommodation/edit', id]);
  }

  private deleteConfirmId: number | null = null;
  private deleteConfirmTimeout: any = null;

  deleteRequest(id: number, event: Event): void {
    event.stopPropagation();

    // If this is the second click on the same item within 3 seconds, proceed with deletion
    if (this.deleteConfirmId === id) {
      clearTimeout(this.deleteConfirmTimeout);
      this.deleteConfirmId = null;

      this.accommodationService.deleteRequest(id).subscribe({
        next: () => {
          this.toastService.success('Accommodation request deleted successfully');
          this.fetchRequests();
        },
        error: (error) => {
          this.toastService.error('Failed to delete accommodation request');
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
    return this.statusUtils.getAccommodationStatusBadgeClass(status);
  }


  getCheckInDate(request: AccommodationRequest): string {
    // Try multiple sources for check-in date
    const checkInDate = request.additional_data?.requested_check_in_date ||
                        request.additional_data?.check_in_date ||
                        request.tsr_departure_date;
    if (!checkInDate) return 'N/A';
    return this.dateUtils.formatDate(checkInDate);
  }

  getLocation(request: AccommodationRequest): string {
    return request.additional_data?.location || '';
  }

  canEdit(request: AccommodationRequest): boolean {
    const status = request.status.toLowerCase();
    return status.includes('draft') || status.includes('pending');
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
