import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ExpenseClaimsService, ExpenseClaim } from '../../expense-claims/services/expense-claims.service';
import { ToastService } from '../../../core/services/toast.service';

interface PendingClaim {
  id: number;
  request_number: string;
  staffName: string;
  staffNo: string;
  purpose: string;
  amount: number;
  status: string;
  submittedDate: string;
}

interface CompletedClaim {
  id: number;
  request_number: string;
  staffName: string;
  amount: number;
  status: string;
  completedDate: string;
  paymentMethod?: string;
  paymentReference?: string;
}

@Component({
  selector: 'app-claims-processing',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './claims-processing.component.html',
  styleUrl: './claims-processing.component.scss'
})
export class ClaimsProcessingComponent implements OnInit {
  activeTab: 'pending' | 'completed' = 'pending';

  // Pending Claims
  pendingClaims: PendingClaim[] = [];
  isLoadingPending = false;
  errorPending: string | null = null;

  // Completed Claims
  completedClaims: CompletedClaim[] = [];
  isLoadingCompleted = false;

  // Selected Claim for processing
  selectedClaim: PendingClaim | null = null;
  isProcessing = false;

  // Processing form fields
  processingNotes = '';
  paymentMethod = 'BANK_TRANSFER';
  paymentReference = '';
  paymentDate = '';

  constructor(
    private expenseClaimsService: ExpenseClaimsService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.fetchPendingClaims();
    this.fetchCompletedClaims();
  }

  /**
   * Fetch pending expense claims (Approved status)
   */
  fetchPendingClaims(): void {
    this.isLoadingPending = true;
    this.errorPending = null;

    this.expenseClaimsService.getAllClaims({ status: 'Approved' }).subscribe({
      next: (response: any) => {
        const claims = response.results || response;

        this.pendingClaims = claims.map((claim: any) => ({
          id: claim.id,
          request_number: claim.request_number || `CLM-${claim.id}`,
          staffName: claim.staff_name || 'N/A',
          staffNo: claim.staff_no || 'N/A',
          purpose: claim.purpose_of_claim || 'N/A',
          amount: claim.total_advance_claim_amount || 0,
          status: claim.status,
          submittedDate: claim.submitted_at || claim.created_at
        }));

        this.isLoadingPending = false;

        // Auto-select first claim if available
        if (this.pendingClaims.length > 0 && !this.selectedClaim) {
          this.selectClaim(this.pendingClaims[0]);
        }
      },
      error: (err) => {
        this.errorPending = 'Failed to load pending claims: ' + (err.error?.message || err.message || 'Unknown error');
        this.isLoadingPending = false;
        console.error('Error loading pending claims:', err);
      }
    });
  }

  /**
   * Fetch completed expense claims (Paid status)
   */
  fetchCompletedClaims(): void {
    this.isLoadingCompleted = true;

    this.expenseClaimsService.getAllClaims({ status: 'Paid' }).subscribe({
      next: (response: any) => {
        const claims = response.results || response;

        this.completedClaims = claims.map((claim: any) => ({
          id: claim.id,
          request_number: claim.request_number || `CLM-${claim.id}`,
          staffName: claim.staff_name || 'N/A',
          amount: claim.total_advance_claim_amount || 0,
          status: claim.status,
          completedDate: claim.payment_date || claim.updated_at,
          paymentMethod: claim.payment_method || 'N/A',
          paymentReference: claim.cheque_receipt_no || 'N/A'
        }));

        this.isLoadingCompleted = false;
      },
      error: (err) => {
        this.isLoadingCompleted = false;
        console.error('Error loading completed claims:', err);
      }
    });
  }

  /**
   * Switch between tabs
   */
  setActiveTab(tab: 'pending' | 'completed'): void {
    this.activeTab = tab;
  }

  /**
   * Select a claim for processing
   */
  selectClaim(claim: PendingClaim): void {
    this.selectedClaim = claim;
    this.resetFormFields();
  }

  /**
   * Reset form fields
   */
  resetFormFields(): void {
    this.processingNotes = '';
    this.paymentMethod = 'BANK_TRANSFER';
    this.paymentReference = '';
    this.paymentDate = new Date().toISOString().split('T')[0];
  }

  /**
   * Mark claim as paid
   */
  markAsPaid(): void {
    if (!this.selectedClaim) {
      this.toastService.error('No claim selected');
      return;
    }

    if (!this.paymentReference || !this.paymentDate) {
      this.toastService.error('Payment reference and date are required');
      return;
    }

    this.isProcessing = true;

    const paymentData = {
      payment_method: this.paymentMethod,
      cheque_receipt_no: this.paymentReference,
      payment_date: this.paymentDate,
      comments: this.processingNotes
    };

    this.expenseClaimsService.markAsPaid(this.selectedClaim.id, paymentData).subscribe({
      next: () => {
        this.toastService.success(`Claim ${this.selectedClaim!.request_number} marked as paid successfully`);
        this.isProcessing = false;

        // Refresh lists
        this.fetchPendingClaims();
        this.fetchCompletedClaims();

        // Clear selection
        this.selectedClaim = null;
      },
      error: (err) => {
        this.toastService.error('Failed to mark claim as paid: ' + (err.error?.message || err.message));
        this.isProcessing = false;
        console.error('Error marking claim as paid:', err);
      }
    });
  }

  /**
   * Go back to claims admin overview
   */
  goBack(): void {
    this.router.navigate(['/admin/claims']);
  }

  /**
   * Format currency
   */
  formatCurrency(amount: number | null | undefined): string {
    if (amount === null || amount === undefined) return 'N/A';
    return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  }

  /**
   * Format date
   */
  formatDate(date: string | null | undefined): string {
    if (!date) return 'N/A';
    try {
      const d = new Date(date);
      return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return 'Invalid Date';
    }
  }
}
