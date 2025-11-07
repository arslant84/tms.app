import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ExpenseClaimsService, ExpenseClaim } from '../../expense-claims/services/expense-claims.service';
import { ToastService } from '../../../core/services/toast.service';
import { AppSettingsService } from '../../../core/services/app-settings.service';

@Component({
  selector: 'app-claims-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './claims-admin.component.html',
  styleUrl: './claims-admin.component.scss'
})
export class ClaimsAdminComponent implements OnInit {
  // Stats
  stats = {
    total: 0,
    pendingReview: 0,
    approved: 0,
    processing: 0
  };

  // Claims
  claims: ExpenseClaim[] = [];
  filteredClaims: ExpenseClaim[] = [];
  loadingClaims = false;

  // Filter criteria
  filterCriteria = {
    status: '',
    search: '',
    dateFrom: '',
    dateTo: ''
  };

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalClaims = 0;

  // Loading states
  error: string = '';

  constructor(
    private expenseClaimsService: ExpenseClaimsService,
    private toastService: ToastService,
    public router: Router,
    private appSettingsService: AppSettingsService
  ) {}

  ngOnInit(): void {
    this.fetchStats();
    this.loadClaims();
  }

  /**
   * Fetch expense claims statistics
   */
  fetchStats(): void {
    this.expenseClaimsService.getAllClaims({}).subscribe({
      next: (response: any) => {
        const claims = response.results || response || [];

        this.stats.total = claims.length;
        this.stats.pendingReview = claims.filter((claim: any) =>
          claim.status && (claim.status.toLowerCase().includes('pending') || claim.status === 'Submitted')
        ).length;
        this.stats.approved = claims.filter((claim: any) =>
          claim.status === 'Approved'
        ).length;
        this.stats.processing = claims.filter((claim: any) =>
          claim.status && (claim.status.toLowerCase().includes('processing') || claim.status === 'Pending Payment' || claim.status === 'Paid')
        ).length;
      },
      error: (err) => {
        console.error('Error fetching stats:', err);
      }
    });
  }

  /**
   * Load claims from API
   */
  loadClaims(): void {
    this.loadingClaims = true;
    this.error = '';

    const params: any = {
      page: this.currentPage,
      page_size: this.pageSize
    };

    if (this.filterCriteria.status) {
      params.status = this.filterCriteria.status;
    }

    if (this.filterCriteria.search) {
      params.search = this.filterCriteria.search;
    }

    if (this.filterCriteria.dateFrom) {
      params.date_from = this.filterCriteria.dateFrom;
    }

    if (this.filterCriteria.dateTo) {
      params.date_to = this.filterCriteria.dateTo;
    }

    this.expenseClaimsService.getAllClaims(params).subscribe({
      next: (response) => {
        this.claims = response.results || response;
        this.totalClaims = response.count || this.claims.length;
        this.filteredClaims = [...this.claims];
        this.loadingClaims = false;
      },
      error: (err) => {
        this.error = 'Failed to load expense claims: ' + (err.error?.message || err.message || 'Unknown error');
        this.loadingClaims = false;
        console.error('Error loading claims:', err);
      }
    });
  }

  /**
   * Apply filters
   */
  applyFilters(): void {
    this.currentPage = 1;
    this.loadClaims();
  }

  /**
   * Clear filters
   */
  clearFilters(): void {
    this.filterCriteria = {
      status: '',
      search: '',
      dateFrom: '',
      dateTo: ''
    };
    this.currentPage = 1;
    this.loadClaims();
  }

  /**
   * Change page
   */
  changePage(page: number): void {
    if (page < 1 || page > this.totalPages) return;
    this.currentPage = page;
    this.loadClaims();
  }

  /**
   * View claim details
   */
  viewClaim(claim: ExpenseClaim): void {
    this.router.navigate(['/expenses', claim.id]);
  }

  /**
   * Navigate to claims processing
   */
  goToProcessing(): void {
    this.router.navigate(['/admin/claims/processing']);
  }

  /**
   * Get status badge class
   */
  getStatusBadgeClass(status: string): string {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('paid')) return 'badge-success';
    if (statusLower.includes('approved')) return 'badge-info';
    if (statusLower.includes('rejected')) return 'badge-danger';
    if (statusLower.includes('cancelled')) return 'badge-secondary';
    if (statusLower.includes('pending') || statusLower.includes('submitted')) return 'badge-warning';
    return 'badge-secondary';
  }

  /**
   * Format currency
   */
  formatCurrency(amount: number | null | undefined): string {
    if (amount === null || amount === undefined) return 'N/A';
    const currency = this.appSettingsService.getDefaultCurrency();
    return amount.toLocaleString('en-US', { style: 'currency', currency: currency });
  }

  /**
   * Format date
   */
  formatDate(date: string | Date | null | undefined): string {
    if (!date) return 'N/A';
    try {
      const d = typeof date === 'string' ? new Date(date) : date;
      return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return 'Invalid Date';
    }
  }

  /**
   * Get total pages
   */
  get totalPages(): number {
    return Math.ceil(this.totalClaims / this.pageSize);
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
