import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ExpenseClaimsService, ExpenseClaimDetail } from '../../services/expense-claims.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-expense-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './expense-detail.component.html',
  styleUrls: ['./expense-detail.component.scss']
})
export class ExpenseDetailComponent implements OnInit {
  claim: ExpenseClaimDetail | null = null;
  loading: boolean = true;
  error: string = '';
  claimId!: number;

  // Status-based visibility constants (from pctsb.syntra)
  private readonly EDITABLE_STATUSES = ['Pending Department Focal', 'Pending Verification', 'Draft', 'Rejected', 'Pending Approval'];
  private readonly CANCELLABLE_STATUSES = ['Pending Department Focal', 'Pending Verification', 'Pending Approval', 'Pending HOD'];
  private readonly DELETABLE_STATUSES = ['Draft', 'Pending Department Focal', 'Pending Verification', 'Rejected'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private expenseService: ExpenseClaimsService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.claimId = +params['id'];
      if (this.claimId) {
        this.loadClaimDetails();
      }
    });
  }

  loadClaimDetails(): void {
    this.loading = true;
    this.error = '';

    this.expenseService.getClaimById(this.claimId).subscribe({
      next: (data) => {
        this.claim = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load claim details: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading claim:', err);
      }
    });
  }

  canEdit(): boolean {
    return this.EDITABLE_STATUSES.includes(this.claim?.status || '');
  }

  canCancel(): boolean {
    return this.CANCELLABLE_STATUSES.includes(this.claim?.status || '');
  }

  canDelete(): boolean {
    return this.DELETABLE_STATUSES.includes(this.claim?.status || '');
  }

  getStatusClass(): string {
    const status = this.claim?.status?.toLowerCase() || '';
    if (status.includes('approved') || status.includes('processed')) return 'badge-success';
    if (status.includes('rejected')) return 'badge-danger';
    if (status.includes('pending') || status.includes('verification')) return 'badge-warning';
    if (status.includes('draft')) return 'badge-secondary';
    if (status.includes('cancelled')) return 'badge-secondary';
    return 'badge-info';
  }

  goBack(): void {
    this.router.navigate(['/expenses']);
  }

  onEdit(): void {
    this.router.navigate(['/expenses/edit', this.claimId]);
  }

  onCancel(): void {
    if (confirm('Are you sure you want to cancel this claim? This action cannot be undone.')) {
      this.expenseService.cancelClaim(this.claimId).subscribe({
        next: () => {
          this.toastService.success('Claim cancelled successfully');
          this.loadClaimDetails();
        },
        error: (err) => {
          this.toastService.error('Failed to cancel claim: ' + (err.error?.message || err.message));
          console.error('Error cancelling claim:', err);
        }
      });
    }
  }

  onDelete(): void {
    if (confirm('Are you sure you want to delete this claim? This action cannot be undone.')) {
      this.expenseService.deleteClaim(this.claimId).subscribe({
        next: () => {
          this.toastService.success('Claim deleted successfully');
          this.router.navigate(['/expenses']);
        },
        error: (err) => {
          this.toastService.error('Failed to delete claim: ' + (err.error?.message || err.message));
          console.error('Error deleting claim:', err);
        }
      });
    }
  }

  onPrint(): void {
    window.print();
  }

  formatCurrency(amount: number | undefined): string {
    if (!amount && amount !== 0) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  }

  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }
}
