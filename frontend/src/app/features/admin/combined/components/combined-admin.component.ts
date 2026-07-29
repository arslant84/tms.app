/**
 * Combined Admin Overview Component
 *
 * Admin dashboard for managing Combined Requests (TSR + Transport + Accommodation + Visa)
 * Shows stats, filterable list, and quick actions.
 */

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { CombinedRequestService } from '../../../requests/combined/services/combined-request.service';
import { CombinedRequest } from '../../../requests/combined/models/combined-request.model';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';

interface FilterCriteria {
  status: string;
  search: string;
  dateFrom: string;
  dateTo: string;
  includeTravel: string;
  includeTransport: string;
  includeAccommodation: string;
  includeVisa: string;
}

interface DashboardStats {
  total: number;
  draft: number;
  pending: number;
  approved: number;
  processing: number;
  completed: number;
  rejected: number;
}

@Component({
  selector: 'app-combined-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './combined-admin.component.html',
  styleUrl: './combined-admin.component.scss'
})
export class CombinedAdminComponent implements OnInit {
  // Data
  requests: CombinedRequest[] = [];
  filteredRequests: CombinedRequest[] = [];

  // Dashboard stats
  stats: DashboardStats = {
    total: 0,
    draft: 0,
    pending: 0,
    approved: 0,
    processing: 0,
    completed: 0,
    rejected: 0
  };

  // Filter criteria
  filterCriteria: FilterCriteria = {
    status: 'all',
    search: '',
    dateFrom: '',
    dateTo: '',
    includeTravel: 'all',
    includeTransport: 'all',
    includeAccommodation: 'all',
    includeVisa: 'all'
  };

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalItems = 0;

  // State
  loading = true;
  error = '';
  processingId: number | null = null;

  // Filter state
  travelTypeFilter = 'all';

  // Filter options — start minimal, populated dynamically after data loads
  statusOptions: { value: string; label: string }[] = [
    { value: 'all', label: 'All Statuses' }
  ];

  travelTypeOptions: { value: string; label: string }[] = [
    { value: 'all', label: 'All Types' }
  ];

  constructor(
    private combinedRequestService: CombinedRequestService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private router: Router,
    public dateUtils: DateUtilsService,
    private statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    this.loadStats();
    this.loadRequests();
  }

  /**
   * Load all requests (large page) once for accurate dashboard stats
   */
  private loadStats(): void {
    this.combinedRequestService.getAll({ adminView: true, pageSize: 1000 }).subscribe({
      next: (response) => {
        const all = response.results || [];
        this.stats = {
          total: response.count || all.length,
          draft: all.filter(r => r.status === 'Draft').length,
          pending: all.filter(r => r.status?.startsWith('Pending') || r.status === 'Submitted').length,
          approved: all.filter(r => r.status === 'Approved').length,
          processing: all.filter(r => r.status === 'Processing').length,
          completed: all.filter(r => r.status === 'Completed').length,
          rejected: all.filter(r => r.status === 'Rejected' || r.status === 'Cancelled').length
        };
        this.buildDynamicOptions(all);
      }
    });
  }

  /**
   * Load all combined requests with admin view
   */
  loadRequests(): void {
    this.loading = true;
    this.error = '';

    const filters: any = {
      page: this.currentPage,
      pageSize: this.pageSize,
      adminView: true
    };

    if (this.filterCriteria.status !== 'all') {
      filters.status = this.filterCriteria.status;
    }
    if (this.filterCriteria.search) {
      filters.search = this.filterCriteria.search;
    }

    this.combinedRequestService.getAll(filters).subscribe({
      next: (response) => {
        this.requests = response.results || [];
        this.totalItems = response.count || this.requests.length;
        this.applyClientFilters();
        this.loading = false;
      },
      error: (err) => {
        this.error = err.message || 'Failed to load requests';
        this.loading = false;
        this.toastService.error('Failed to load combined requests');
      }
    });
  }

  /**
   * Build dynamic filter option lists from all-requests data
   */
  private buildDynamicOptions(all: CombinedRequest[] = this.requests): void {
    // Unique statuses
    const uniqueStatuses = [
      ...new Set(all.map(r => r.status).filter(Boolean))
    ].sort() as string[];
    this.statusOptions = [
      { value: 'all', label: 'All Statuses' },
      ...uniqueStatuses.map(s => ({ value: s, label: s }))
    ];

    // Unique travel types (label-mapped for readability)
    const travelTypeLabels: Record<string, string> = {
      domestic: 'Domestic',
      international: 'International',
      home_leave: 'Home Leave',
      external: 'External Parties'
    };
    const uniqueTypes = [
      ...new Set(all.map(r => r.travelType).filter(Boolean))
    ].sort() as string[];
    this.travelTypeOptions = [
      { value: 'all', label: 'All Types' },
      ...uniqueTypes.map(t => ({ value: t, label: travelTypeLabels[t] || t }))
    ];
  }

  /**
   * Apply client-side filters
   */
  applyClientFilters(): void {
    this.filteredRequests = this.requests.filter(request => {
      // Travel type filter
      if (this.travelTypeFilter !== 'all' && request.travelType !== this.travelTypeFilter) {
        return false;
      }
      return true;
    });
  }

  /**
   * Respond to travel type dropdown change
   */
  onTravelTypeFilterChange(): void {
    this.applyClientFilters();
  }

  /**
   * Respond to status dropdown change — re-fetches with server-side filter
   */
  onStatusFilterChange(): void {
    this.currentPage = 1;
    this.loadRequests();
  }

  /**
   * Respond to search input (enter key)
   */
  onSearchChange(): void {
    this.currentPage = 1;
    this.loadRequests();
  }

  /**
   * Apply filters and reload
   */
  applyFilters(): void {
    this.currentPage = 1;
    this.loadRequests();
  }

  /**
   * Reset all filters
   */
  resetFilters(): void {
    this.filterCriteria = {
      status: 'all',
      search: '',
      dateFrom: '',
      dateTo: '',
      includeTravel: 'all',
      includeTransport: 'all',
      includeAccommodation: 'all',
      includeVisa: 'all'
    };
    this.travelTypeFilter = 'all';
    this.currentPage = 1;
    this.loadRequests();
  }

  /**
   * Change page
   */
  changePage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadRequests();
    }
  }

  /**
   * View request details (navigates to the user-facing detail page, same pattern as visa admin)
   */
  viewRequest(request: CombinedRequest): void {
    this.router.navigate(['/combined', request.id]);
  }

  /**
   * Go to processing view
   */
  goToProcessing(): void {
    this.router.navigate(['/admin/combined/processing']);
  }

  /**
   * Approve a request (quick action)
   */
  approveRequest(request: CombinedRequest): void {
    this.confirmationService.confirm({
      title: 'Approve Request',
      message: `Are you sure you want to approve request ${request.requestNumber || '#' + request.id}?`,
      confirmText: 'Approve',
      type: 'success'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeApprove(request);
    });
  }

  private executeApprove(request: CombinedRequest): void {
    this.processingId = request.id!;
    this.combinedRequestService.approve(request.id!, 'Approved by Admin').subscribe({
      next: () => {
        this.toastService.success('Request approved successfully');
        this.processingId = null;
        this.loadRequests();
      },
      error: (err) => {
        this.toastService.error('Failed to approve: ' + (err.message || 'Unknown error'));
        this.processingId = null;
      }
    });
  }

  /**
   * Reject a request
   */
  rejectRequest(request: CombinedRequest): void {
    this.confirmationService.confirm({
      title: 'Reject Request',
      message: `Are you sure you want to reject request ${request.requestNumber || '#' + request.id}? This action cannot be undone.`,
      confirmText: 'Reject',
      type: 'danger'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeReject(request);
    });
  }

  private executeReject(request: CombinedRequest): void {
    this.processingId = request.id!;
    this.combinedRequestService.reject(request.id!, 'Rejected by Admin').subscribe({
      next: () => {
        this.toastService.success('Request rejected');
        this.processingId = null;
        this.loadRequests();
      },
      error: (err) => {
        this.toastService.error('Failed to reject: ' + (err.message || 'Unknown error'));
        this.processingId = null;
      }
    });
  }

  // ===== UTILITY METHODS =====

  /**
   * Get CSS class for status badge - delegates to StatusUtilsService so
   * the same status renders the same color everywhere in the app.
   */
  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Get included modules as badges
   */
  getIncludedModules(request: CombinedRequest): string[] {
    const modules: string[] = [];
    if (request.includeTravel) modules.push('Travel');
    if (request.includeTransport) modules.push('Transport');
    if (request.includeAccommodation) modules.push('Accommodation');
    if (request.includeVisa) modules.push('Visa');
    return modules;
  }

  /**
   * Check if currently processing an item
   */
  isProcessing(id: number): boolean {
    return this.processingId === id;
  }

  /**
   * Format date for display
   */
  formatDate(date: string | undefined): string {
    if (!date) return '-';
    return this.dateUtils.formatDate(date, 'dd MMM yyyy');
  }

  /**
   * Get total pages for pagination
   */
  get totalPages(): number {
    return Math.ceil(this.totalItems / this.pageSize) || 1;
  }

  /**
   * Get page numbers for pagination
   */
  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
    const end = Math.min(this.totalPages, start + maxVisible - 1);

    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  }

  /**
   * Can approve — shown for pending/submitted requests
   */
  canApprove(request: CombinedRequest): boolean {
    return !!(request.status?.startsWith('Pending') || request.status === 'Submitted');
  }

  /**
   * Can reject — same conditions as approve
   */
  canReject(request: CombinedRequest): boolean {
    return this.canApprove(request);
  }

  /**
   * Can start processing — shown only for approved requests (matches visa admin pattern)
   */
  canStartProcessing(request: CombinedRequest): boolean {
    return request.status === 'Approved';
  }

  /**
   * Start processing a combined request
   */
  startProcessing(request: CombinedRequest): void {
    this.router.navigate(['/admin/combined/processing'], {
      queryParams: { id: request.id }
    });
  }
}
