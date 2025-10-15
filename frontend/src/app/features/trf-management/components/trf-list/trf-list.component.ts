import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TrfService } from '../../../../core/services/trf.service';
import { TravelRequestForm } from '../../../../core/models/trf.model';
import { finalize } from 'rxjs/operators';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

// Status and type constants matching backend
export const TRF_STATUSES = [
  'DRAFT',
  'PENDING_DEPARTMENT_FOCAL',
  'PENDING_LINE_MANAGER',
  'PENDING_HOD',
  'APPROVED',
  'REJECTED',
  'CANCELLED',
  'PROCESSING_FLIGHTS',
  'PROCESSING_ACCOMMODATION',
  'AWAITING_VISA',
  'TSR_PROCESSED'
];

export const TRAVEL_TYPES = [
  'DOMESTIC',
  'OVERSEAS',
  'HOME_LEAVE_PASSAGE',
  'EXTERNAL_PARTIES'
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
export class TrfListComponent implements OnInit {
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

    // Load initial data
    this.fetchTrfs();
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
          this.trfs = response.results || response.trfs || [];
          this.totalTrfs = response.count || response.totalCount || 0;
          this.totalPages = Math.ceil(this.totalTrfs / this.limit);
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
    this.router.navigate(['/trf/view', id]);
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
      'DRAFT': 'badge-secondary',
      'PENDING_DEPARTMENT_FOCAL': 'badge-warning',
      'PENDING_LINE_MANAGER': 'badge-warning',
      'PENDING_HOD': 'badge-warning',
      'APPROVED': 'badge-success',
      'REJECTED': 'badge-danger',
      'CANCELLED': 'badge-secondary',
      'PROCESSING_FLIGHTS': 'badge-info',
      'PROCESSING_ACCOMMODATION': 'badge-info',
      'AWAITING_VISA': 'badge-info',
      'TSR_PROCESSED': 'badge-success'
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
