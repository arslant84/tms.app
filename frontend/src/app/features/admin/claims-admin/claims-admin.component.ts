import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ExpenseClaimsService, ExpenseClaim } from '../../expense-claims/services/expense-claims.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-claims-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './claims-admin.component.html',
  styleUrl: './claims-admin.component.scss'
})
export class ClaimsAdminComponent implements OnInit {
  claims: ExpenseClaim[] = [];
  filteredClaims: ExpenseClaim[] = [];
  selectedClaim: ExpenseClaim | null = null;

  // Filter criteria
  filterCriteria = {
    status: 'all',
    search: '',
    dateFrom: '',
    dateTo: ''
  };

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalClaims = 0;

  // Loading states
  loading: boolean = true;
  error: string = '';
  processingId: number | null = null;

  // Mark as paid modal
  showMarkAsPaidModal: boolean = false;
  paymentData = {
    cheque_receipt_no: '',
    payment_date: '',
    payment_method: 'CHEQUE',
    comments: ''
  };

  // Status options for filter
  statusOptions = [
    { value: 'all', label: 'All Statuses' },
    { value: 'Pending Approval', label: 'Pending Approval' },
    { value: 'Approved', label: 'Approved' },
    { value: 'Pending Payment', label: 'Pending Payment' },
    { value: 'Paid', label: 'Paid' },
    { value: 'Rejected', label: 'Rejected' },
    { value: 'Cancelled', label: 'Cancelled' }
  ];

  constructor(
    private expenseClaimsService: ExpenseClaimsService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadClaims();
  }

  /**
   * Load claims from API
   */
  loadClaims(): void {
    this.loading = true;
    this.error = '';

    const params: any = {
      page: this.currentPage,
      page_size: this.pageSize
    };

    if (this.filterCriteria.status !== 'all') {
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
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load expense claims: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
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
   * Reset filters
   */
  resetFilters(): void {
    this.filterCriteria = {
      status: 'all',
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
   * Open mark as paid modal
   */
  openMarkAsPaidModal(claim: ExpenseClaim): void {
    this.selectedClaim = claim;
    this.paymentData = {
      cheque_receipt_no: '',
      payment_date: new Date().toISOString().split('T')[0],
      payment_method: 'CHEQUE',
      comments: ''
    };
    this.showMarkAsPaidModal = true;
  }

  /**
   * Close mark as paid modal
   */
  closeMarkAsPaidModal(): void {
    this.showMarkAsPaidModal = false;
    this.selectedClaim = null;
    this.paymentData = {
      cheque_receipt_no: '',
      payment_date: '',
      payment_method: 'CHEQUE',
      comments: ''
    };
  }

  /**
   * Mark claim as paid
   */
  markAsPaid(): void {
    if (!this.selectedClaim) return;

    if (!this.paymentData.cheque_receipt_no || !this.paymentData.payment_date) {
      this.toastService.error('Please provide payment reference and date');
      return;
    }

    this.processingId = this.selectedClaim.id;

    this.expenseClaimsService.markAsPaid(this.selectedClaim.id, this.paymentData).subscribe({
      next: () => {
        this.toastService.success('Claim marked as paid successfully');
        this.closeMarkAsPaidModal();
        this.processingId = null;
        this.loadClaims();
      },
      error: (err) => {
        this.toastService.error('Failed to mark claim as paid: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error marking claim as paid:', err);
      }
    });
  }

  /**
   * Approve claim
   */
  approveClaim(claim: ExpenseClaim): void {
    if (!confirm(`Are you sure you want to approve claim #${claim.id}?`)) {
      return;
    }

    this.processingId = claim.id;

    this.expenseClaimsService.approveClaim(claim.id, {
      step_role: 'FINANCE',
      comments: 'Approved by Finance Admin'
    }).subscribe({
      next: () => {
        this.toastService.success('Claim approved successfully');
        this.processingId = null;
        this.loadClaims();
      },
      error: (err) => {
        this.toastService.error('Failed to approve claim: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error approving claim:', err);
      }
    });
  }

  /**
   * Reject claim
   */
  rejectClaim(claim: ExpenseClaim): void {
    const reason = prompt('Please provide a reason for rejection:');

    if (!reason || reason.trim() === '') {
      this.toastService.error('Rejection reason is required');
      return;
    }

    this.processingId = claim.id;

    this.expenseClaimsService.rejectClaim(claim.id, {
      step_role: 'FINANCE',
      comments: reason
    }).subscribe({
      next: () => {
        this.toastService.success('Claim rejected successfully');
        this.processingId = null;
        this.loadClaims();
      },
      error: (err) => {
        this.toastService.error('Failed to reject claim: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error rejecting claim:', err);
      }
    });
  }

  /**
   * Get status badge class
   */
  getStatusClass(status: string): string {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('paid')) return 'badge bg-success';
    if (statusLower.includes('approved')) return 'badge bg-info';
    if (statusLower.includes('rejected')) return 'badge bg-danger';
    if (statusLower.includes('cancelled')) return 'badge bg-secondary';
    if (statusLower.includes('pending')) return 'badge bg-warning';
    return 'badge bg-secondary';
  }

  /**
   * Format currency
   */
  formatCurrency(amount: number | null | undefined): string {
    if (amount === null || amount === undefined) return 'N/A';
    return amount.toLocaleString('en-MY', { style: 'currency', currency: 'MYR' });
  }

  /**
   * Format date
   */
  formatDate(date: string | Date | null | undefined): string {
    if (!date) return 'N/A';
    try {
      const d = typeof date === 'string' ? new Date(date) : date;
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return 'Invalid Date';
    }
  }

  /**
   * Check if claim can be approved
   */
  canApprove(claim: ExpenseClaim): boolean {
    return claim.status === 'Pending Approval' || claim.status === 'Approved';
  }

  /**
   * Check if claim can be marked as paid
   */
  canMarkAsPaid(claim: ExpenseClaim): boolean {
    return claim.status === 'Approved' || claim.status === 'Pending Payment';
  }

  /**
   * Check if claim is processing
   */
  isProcessing(claimId: number): boolean {
    return this.processingId === claimId;
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
