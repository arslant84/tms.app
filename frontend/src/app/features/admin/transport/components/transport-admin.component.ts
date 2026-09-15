import { CommonModule } from '@angular/common';
import { Component, inject, type OnDestroy, type OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subject } from 'rxjs';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import {
  type TransportRequest,
  TransportService,
} from '../../../transport/services/transport.service';

/**
 * Transport Administration - a read-only overview of every transport
 * request (mirrors Flights/Accommodation Admin's list-only dashboards).
 * Assigning a vehicle, completing, and undoing a completion all happen in
 * Transport Processing instead - having two places that could both write
 * vehicle assignments was the root cause of an earlier bug where
 * assignments made here didn't show up consistently elsewhere.
 */
@Component({
  selector: 'app-transport-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LoadingSpinnerComponent],
  templateUrl: './transport-admin.component.html',
  styleUrl: './transport-admin.component.scss',
})
export class TransportAdminComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  requests: TransportRequest[] = [];
  filteredRequests: TransportRequest[] = [];

  // Stats
  totalRequestsCount = 0;
  pendingReviewCount = 0;
  approvedCount = 0;
  processingCount = 0;

  // Filter criteria
  filterCriteria = {
    status: 'all',
    search: '',
    dateFrom: '',
    dateTo: '',
  };

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalRequests = 0;

  // Loading states
  loading: boolean = true;
  error: string = '';

  // Status options for filter - populated dynamically
  statusOptions: { value: string; label: string }[] = [{ value: 'all', label: 'All Statuses' }];

  private transportService = inject(TransportService);
  private statusUtils = inject(StatusUtilsService);
  private errorHandler = inject(HttpErrorHandlerService);
  router = inject(Router);
  dateUtils = inject(DateUtilsService);

  ngOnInit(): void {
    this.loadRequests();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load transport requests from API
   */
  loadRequests(): void {
    this.loading = true;
    this.error = '';

    const filters = {
      page: this.currentPage,
      page_size: this.pageSize,
      adminView: true,
      status: this.filterCriteria.status !== 'all' ? this.filterCriteria.status : undefined,
      search: this.filterCriteria.search || undefined,
    };

    this.transportService.getAllRequests(filters).subscribe({
      next: response => {
        this.requests = Array.isArray(response) ? response : response.results;
        this.totalRequests = Array.isArray(response) ? this.requests.length : response.count;
        this.filteredRequests = [...this.requests];
        this.calculateStats();
        this.loading = false;
        if (this.statusOptions.length <= 1) {
          const statuses = this.requests.map(r => r.status).filter(Boolean) as string[];
          const uniqueStatuses = [...new Set(statuses)].sort();
          this.statusOptions = [
            { value: 'all', label: 'All Statuses' },
            ...uniqueStatuses.map(s => ({ value: s, label: s })),
          ];
        }
      },
      error: err => {
        this.error = this.errorHandler.getErrorMessage(err, 'Failed to load transport requests');
        this.loading = false;
        console.error('Error loading requests:', err);
      },
    });
  }

  /**
   * Calculate statistics for dashboard cards
   */
  calculateStats(): void {
    this.totalRequestsCount = this.requests.length;
    this.pendingReviewCount = this.requests.filter(req =>
      req.status?.toLowerCase().includes('pending')
    ).length;
    this.approvedCount = this.requests.filter(
      req =>
        req.status?.toLowerCase().includes('approved') &&
        !req.status?.toLowerCase().includes('processing')
    ).length;
    this.processingCount = this.requests.filter(
      req => req.status === 'Processing with Transport Admin' || req.status === 'Completed'
    ).length;
  }

  /**
   * Apply filters
   */
  applyFilters(): void {
    this.currentPage = 1;
    this.loadRequests();
  }

  /**
   * Reset filters
   */
  resetFilters(): void {
    this.filterCriteria = {
      status: 'all',
      search: '',
      dateFrom: '',
      dateTo: '',
    };
    this.currentPage = 1;
    this.loadRequests();
  }

  /**
   * Change page
   */
  changePage(page: number): void {
    this.currentPage = page;
    this.loadRequests();
  }

  /**
   * View request details
   */
  viewRequest(request: TransportRequest): void {
    this.router.navigate(['/transport', request.id]);
  }

  /**
   * Get status badge class - delegates to StatusUtilsService so the same
   * status renders the same color everywhere in the app.
   */
  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  getTotalPassengers(request: TransportRequest): number {
    if (!request.transportDetails || request.transportDetails.length === 0) return 0;
    return request.transportDetails.reduce(
      (sum, detail) => sum + (detail.numberOfPassengers || 0),
      0
    );
  }

  /**
   * Get total pages
   */
  get totalPages(): number {
    return Math.ceil(this.totalRequests / this.pageSize);
  }

  /**
   * Get page numbers for pagination
   */
  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxPages = 5;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxPages / 2));
    const endPage = Math.min(this.totalPages, startPage + maxPages - 1);

    if (endPage - startPage + 1 < maxPages) {
      startPage = Math.max(1, endPage - maxPages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    return pages;
  }
}
