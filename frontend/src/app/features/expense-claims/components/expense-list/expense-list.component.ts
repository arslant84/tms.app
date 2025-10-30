import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ExpenseClaimsService, ExpenseClaim } from '../../services/expense-claims.service';
import { ToastService } from '../../../../core/services/toast.service';
import { finalize } from 'rxjs/operators';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, filter } from 'rxjs/operators';

// Status constants matching backend
export const CLAIM_STATUSES = [
  'Draft',
  'Pending Verification',
  'Pending Department Focal',
  'Pending HOD',
  'Pending Finance',
  'Approved',
  'Processed',
  'Rejected',
  'Cancelled'
];

@Component({
  selector: 'app-expense-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './expense-list.component.html',
  styleUrl: './expense-list.component.scss'
})
export class ExpenseListComponent implements OnInit, OnDestroy {
  // Pagination
  currentPage = 1;
  totalPages = 1;
  totalClaims = 0;
  limit = 10;

  // Search and filter properties
  searchTerm = '';
  statusFilter = '';

  // Search debouncing
  private searchSubject = new Subject<string>();
  private routerSubscription?: Subscription;

  // Claims data
  claims: ExpenseClaim[] = [];

  // Loading states
  isLoading = false;
  error: string | null = null;

  // Sort configuration
  sortKey: string | null = 'submitted_at';
  sortDirection: 'ascending' | 'descending' = 'descending';

  // Constants for template
  readonly CLAIM_STATUSES = CLAIM_STATUSES;

  constructor(
    private router: Router,
    private expenseService: ExpenseClaimsService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    // Setup search debouncing
    this.searchSubject.pipe(
      debounceTime(500),
      distinctUntilChanged()
    ).subscribe(searchTerm => {
      this.searchTerm = searchTerm;
      this.resetToFirstPage();
      this.fetchClaims();
    });

    // Refresh list when navigating back to this page
    this.routerSubscription = this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd),
        filter((event: any) => event.url === '/expenses' || event.url.startsWith('/expenses?'))
      )
      .subscribe(() => {
        console.log('Expense Claims list refreshing due to navigation');
        this.fetchClaims();
      });

    // Load initial data
    this.fetchClaims();
  }

  ngOnDestroy(): void {
    if (this.routerSubscription) {
      this.routerSubscription.unsubscribe();
    }
  }

  onSearchChange(value: string): void {
    this.searchSubject.next(value);
  }

  fetchClaims(): void {
    this.isLoading = true;
    this.error = null;

    const params: any = {
      page: this.currentPage,
      limit: this.limit
    };

    if (this.searchTerm) {
      params.search = this.searchTerm;
    }

    if (this.statusFilter) {
      params.status = this.statusFilter;
    }

    if (this.sortKey && this.sortDirection) {
      params.sortBy = this.sortKey;
      params.sortOrder = this.sortDirection;
    }

    this.expenseService.getAllClaims(params)
      .pipe(
        finalize(() => {
          this.isLoading = false;
        })
      )
      .subscribe({
        next: (response: any) => {
          console.log('✅ Expense Claims loaded:', response);

          // Handle both array response and paginated response
          if (Array.isArray(response)) {
            // Direct array response from Django
            this.claims = response;
            this.totalClaims = response.length;
          } else {
            // Paginated response
            this.claims = response.results || response.claims || [];
            this.totalClaims = response.count || response.totalCount || 0;
          }

          this.totalPages = Math.ceil(this.totalClaims / this.limit);
          console.log('Total Claims:', this.totalClaims);
          console.log('Claims array:', this.claims);
        },
        error: (err) => {
          console.error('❌ Error fetching expense claims:', err);
          this.error = err.message || 'Failed to load expense claims';
          this.claims = [];
          this.totalClaims = 0;
          this.totalPages = 1;
        }
      });
  }

  onStatusFilterChange(): void {
    this.resetToFirstPage();
    this.fetchClaims();
  }

  handleSort(key: string): void {
    if (this.sortKey === key) {
      this.sortDirection = this.sortDirection === 'ascending' ? 'descending' : 'ascending';
    } else {
      this.sortKey = key;
      this.sortDirection = 'ascending';
    }
    this.fetchClaims();
  }

  clearFilters(): void {
    this.searchTerm = '';
    this.statusFilter = '';
    this.sortKey = 'submitted_at';
    this.sortDirection = 'descending';
    this.resetToFirstPage();
    this.fetchClaims();
  }

  hasActiveFilters(): boolean {
    return this.searchTerm !== '' || this.statusFilter !== '';
  }

  navigateToCreate(): void {
    this.router.navigate(['/expenses/create']);
  }

  navigateToView(id: number): void {
    this.router.navigate(['/expenses', id]);
  }

  navigateToEdit(id: number): void {
    this.router.navigate(['/expenses/edit', id]);
  }

  deleteClaim(id: number, event: Event): void {
    event.stopPropagation();
    if (confirm('Are you sure you want to delete this expense claim?')) {
      this.expenseService.deleteClaim(id).subscribe({
        next: () => {
          this.toastService.success('Expense claim deleted successfully');
          this.fetchClaims();
        },
        error: (error) => {
          console.error('Error deleting expense claim:', error);
          this.toastService.error('Failed to delete expense claim');
        }
      });
    }
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.fetchClaims();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.fetchClaims();
    }
  }

  private resetToFirstPage(): void {
    this.currentPage = 1;
  }

  getStatusBadgeClass(status: string): string {
    const statusMap: { [key: string]: string } = {
      'Draft': 'badge-secondary',
      'Pending Verification': 'badge-warning',
      'Pending Department Focal': 'badge-warning',
      'Pending HOD': 'badge-warning',
      'Pending Finance': 'badge-warning',
      'Approved': 'badge-success',
      'Processed': 'badge-success',
      'Rejected': 'badge-danger',
      'Cancelled': 'badge-secondary'
    };
    return statusMap[status] || 'badge-secondary';
  }

  formatStatusDisplay(status: string): string {
    return status.replace(/_/g, ' ');
  }

  formatCurrency(amount: number): string {
    if (!amount && amount !== 0) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  }

  formatDate(dateString: string): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }
}
