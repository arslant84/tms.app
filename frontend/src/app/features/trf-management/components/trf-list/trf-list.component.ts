import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TrfService } from '../../../../core/services/trf.service';
import { TravelRequestForm } from '../../../../core/models/trf.model';
import { finalize } from 'rxjs/operators';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, filter } from 'rxjs/operators';

// Status and type constants matching backend
export const TRF_STATUSES = [
  'Draft',
  'Pending Department Focal',
  'Pending HOD',
  'Pending Travel Desk',
  'Pending Finance',
  'Approved',
  'Rejected',
  'Cancelled',
  'Completed'
];

export const TRAVEL_TYPES = [
  'Domestic',
  'International',
  'Local',
  'Field Visit'
];

export interface TrfListItem {
  id: number;
  requestor_name: string;
  travel_type: string;
  purpose: string;
  status: string;
  submitted_at: string;
  departure_date?: string;
  return_date?: string;
}

@Component({
  selector: 'app-trf-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './trf-list.component.html',
  styleUrls: ['./trf-list.component.scss']
})
export class TrfListComponent implements OnInit, OnDestroy {
  // Pagination
  currentPage = 1;
  totalPages = 1;
  totalTrfs = 0;
  limit = 10;

  // Search and filter properties
  searchTerm = '';
  statusFilter = '';
  travelTypeFilter = '';

  // Search debouncing
  private searchSubject = new Subject<string>();
  private routerSubscription?: Subscription;

  // TRF data
  trfs: TrfListItem[] = [];

  // Loading states
  isLoading = false;
  error: string | null = null;

  // Sort configuration
  sortKey: string | null = 'submitted_at';
  sortDirection: 'ascending' | 'descending' = 'descending';

  // Constants for template
  readonly TRF_STATUSES = TRF_STATUSES;
  readonly TRAVEL_TYPES = TRAVEL_TYPES;

  constructor(
    private router: Router,
    private trfService: TrfService
  ) {}

  ngOnInit(): void {
    // Setup search debouncing
    this.searchSubject.pipe(
      debounceTime(500),
      distinctUntilChanged()
    ).subscribe(searchTerm => {
      this.searchTerm = searchTerm;
      this.resetToFirstPage();
      this.fetchTrfs();
    });

    // Refresh list when navigating back to this page
    this.routerSubscription = this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd),
        filter((event: any) => event.url === '/trf' || event.url.startsWith('/trf?'))
      )
      .subscribe(() => {
        console.log('TRF list refreshing due to navigation');
        this.fetchTrfs();
      });

    // Load initial data
    this.fetchTrfs();
  }

  ngOnDestroy(): void {
    if (this.routerSubscription) {
      this.routerSubscription.unsubscribe();
    }
  }

  onSearchChange(value: string): void {
    this.searchSubject.next(value);
  }

  fetchTrfs(): void {
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

    if (this.travelTypeFilter) {
      params.travel_type = this.travelTypeFilter;
    }

    if (this.sortKey && this.sortDirection) {
      params.sortBy = this.sortKey;
      params.sortOrder = this.sortDirection;
    }

    this.trfService.getAllTrfs(params)
      .pipe(
        finalize(() => {
          this.isLoading = false;
        })
      )
      .subscribe({
        next: (response: any) => {
          console.log('✅ TRFs loaded:', response);

          // Handle both array response and paginated response
          if (Array.isArray(response)) {
            // Direct array response from Django
            this.trfs = response;
            this.totalTrfs = response.length;
          } else {
            // Paginated response
            this.trfs = response.results || response.trfs || [];
            this.totalTrfs = response.count || response.totalCount || 0;
          }

          this.totalPages = Math.ceil(this.totalTrfs / this.limit);
          console.log('Total TRFs:', this.totalTrfs);
          console.log('TRFs array:', this.trfs);
        },
        error: (err) => {
          console.error('❌ Error fetching TRFs:', err);
          this.error = err.message || 'Failed to load TRFs';
          this.trfs = [];
          this.totalTrfs = 0;
          this.totalPages = 1;
        }
      });
  }

  onStatusFilterChange(): void {
    this.resetToFirstPage();
    this.fetchTrfs();
  }

  onTravelTypeFilterChange(): void {
    this.resetToFirstPage();
    this.fetchTrfs();
  }

  handleSort(key: string): void {
    if (this.sortKey === key) {
      this.sortDirection = this.sortDirection === 'ascending' ? 'descending' : 'ascending';
    } else {
      this.sortKey = key;
      this.sortDirection = 'ascending';
    }
    this.fetchTrfs();
  }

  clearFilters(): void {
    this.searchTerm = '';
    this.statusFilter = '';
    this.travelTypeFilter = '';
    this.sortKey = 'submitted_at';
    this.sortDirection = 'descending';
    this.resetToFirstPage();
    this.fetchTrfs();
  }

  hasActiveFilters(): boolean {
    return this.searchTerm !== '' || this.statusFilter !== '' || this.travelTypeFilter !== '';
  }

  navigateToCreate(): void {
    this.router.navigate(['/trf/create']);
  }

  navigateToView(id: number): void {
    this.router.navigate(['/trf', id]);
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.fetchTrfs();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.fetchTrfs();
    }
  }

  private resetToFirstPage(): void {
    this.currentPage = 1;
  }

  getStatusBadgeClass(status: string): string {
    const statusMap: { [key: string]: string } = {
      'Draft': 'badge-secondary',
      'Pending Department Focal': 'badge-warning',
      'Pending HOD': 'badge-warning',
      'Pending Travel Desk': 'badge-warning',
      'Pending Finance': 'badge-warning',
      'Approved': 'badge-success',
      'Rejected': 'badge-danger',
      'Cancelled': 'badge-secondary',
      'Completed': 'badge-success'
    };
    return statusMap[status] || 'badge-secondary';
  }

  formatStatusDisplay(status: string): string {
    return status.replace(/_/g, ' ');
  }

  formatTravelTypeDisplay(type: string): string {
    return type.replace(/_/g, ' ');
  }

  formatDate(dateString: string): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }
}
