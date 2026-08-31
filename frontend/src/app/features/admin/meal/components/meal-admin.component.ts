import { CommonModule } from '@angular/common';
import { Component, inject, type OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { ToastService } from '../../../../core/services/toast.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { TrfService } from '../../../trf-management/services/trf.service';

interface MealQueueRequest {
  id: number;
  request_number?: string;
  requestor_name?: string;
  department?: string;
  travel_type?: string;
  status?: string;
  meal_processing_status?: string;
  submitted_at?: string;
  created_at?: string;
}

// 'Completed' was retired as a meal status: with one person handling the
// whole queue, Arranged is the terminal state in practice and no request
// has ever been marked Completed - keeping it around just left a filter
// option and stat tile that always showed zero.
const MEAL_STATUSES = ['Pending', 'Arranged'] as const;

@Component({
  selector: 'app-meal-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './meal-admin.component.html',
  styleUrl: './meal-admin.component.scss',
})
export class MealAdminComponent implements OnInit {
  requests: MealQueueRequest[] = [];

  totalRequestsCount = 0;
  pendingCount = 0;
  arrangedCount = 0;

  filterCriteria = {
    status: 'all',
    search: '',
  };

  currentPage = 1;
  pageSize = 20;
  totalRequests = 0;

  loading = true;
  error = '';
  processingId: number | null = null;

  statusOptions = [
    { value: 'all', label: 'All Meal Statuses' },
    ...MEAL_STATUSES.map(s => ({ value: s, label: s })),
  ];

  private trfService = inject(TrfService);
  private toastService = inject(ToastService);
  private confirmationService = inject(ConfirmationService);
  private statusUtils = inject(StatusUtilsService);
  private errorHandler = inject(HttpErrorHandlerService);
  router = inject(Router);
  dateUtils = inject(DateUtilsService);

  ngOnInit(): void {
    this.loadRequests();
  }

  loadRequests(): void {
    this.loading = true;
    this.error = '';

    this.trfService
      .getMealQueue({
        page: this.currentPage,
        page_size: this.pageSize,
        status: this.filterCriteria.status !== 'all' ? this.filterCriteria.status : undefined,
        search: this.filterCriteria.search || undefined,
      })
      .subscribe({
        next: (raw: unknown) => {
          const response = raw as
            | { results?: MealQueueRequest[]; count?: number }
            | MealQueueRequest[];
          this.requests = (Array.isArray(response) ? response : response.results) || [];
          this.totalRequests =
            (Array.isArray(response) ? undefined : response.count) || this.requests.length;
          this.calculateStats();
          this.loading = false;
        },
        error: err => {
          this.error = this.errorHandler.getErrorMessage(err, 'Failed to load meal requests');
          this.loading = false;
        },
      });
  }

  calculateStats(): void {
    this.totalRequestsCount = this.requests.length;
    this.pendingCount = this.requests.filter(
      r => (r.meal_processing_status || 'Pending') === 'Pending'
    ).length;
    this.arrangedCount = this.requests.filter(r => r.meal_processing_status === 'Arranged').length;
  }

  applyFilters(): void {
    this.currentPage = 1;
    this.loadRequests();
  }

  resetFilters(): void {
    this.filterCriteria = { status: 'all', search: '' };
    this.currentPage = 1;
    this.loadRequests();
  }

  changePage(page: number): void {
    this.currentPage = page;
    this.loadRequests();
  }

  viewRequest(request: MealQueueRequest): void {
    this.router.navigate(['/trf', request.id]);
  }

  markStatus(request: MealQueueRequest, newStatus: string): void {
    this.confirmationService
      .confirm({
        title: `Mark as ${newStatus}`,
        message: `Mark meal request for ${request.request_number || '#' + request.id} as ${newStatus}?`,
        confirmText: newStatus,
        type: 'success',
      })
      .subscribe(confirmed => {
        if (!confirmed) return;
        this.executeMarkStatus(request, newStatus);
      });
  }

  private executeMarkStatus(request: MealQueueRequest, newStatus: string): void {
    this.processingId = request.id;

    this.trfService.updateMealStatus(request.id, newStatus).subscribe({
      next: () => {
        this.toastService.success(`Meal status updated to ${newStatus}`);
        this.processingId = null;
        this.loadRequests();
      },
      error: err => {
        this.toastService.error(
          this.errorHandler.getErrorMessage(err, 'Failed to update meal status')
        );
        this.processingId = null;
      },
    });
  }

  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  getMealStatusClass(status: string | undefined): string {
    switch (status) {
      case 'Completed':
        return 'badge-success';
      case 'Arranged':
        return 'badge-info';
      default:
        return 'badge-warning';
    }
  }

  isProcessing(requestId: number): boolean {
    return this.processingId === requestId;
  }

  get totalPages(): number {
    return Math.ceil(this.totalRequests / this.pageSize);
  }

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
