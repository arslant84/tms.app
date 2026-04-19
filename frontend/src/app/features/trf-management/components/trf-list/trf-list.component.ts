import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TrfService } from '../../services/trf.service';
import { ToastService } from '../../../../core/services/toast.service';
import { finalize, takeUntil } from 'rxjs/operators';
import { Subject } from 'rxjs';
import { filter } from 'rxjs/operators';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { ListStateService } from '../../../../core/services/list-state.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

export interface TrfListItem {
  id: number;
  request_number?: string;
  requestor_name: string;
  staff_id?: string;
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
  imports: [CommonModule, RouterModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './trf-list.component.html',
  styleUrls: ['./trf-list.component.scss']
})
export class TrfListComponent implements OnInit, OnDestroy {
  // Filter properties
  statusFilter = '';
  travelTypeFilter = '';

  private destroy$ = new Subject<void>();
  private navigationRefreshReady = false;

  // TRF data
  trfs: TrfListItem[] = [];

  // Sort configuration
  sortKey: string | null = 'submitted_at';
  sortDirection: 'ascending' | 'descending' = 'descending';

  // Filter options populated dynamically from actual data
  trfStatuses: string[] = [];
  travelTypes: string[] = [];

  // Create list state service manually (not via DI)
  listState = new ListStateService({ pageSize: 10 });

  constructor(
    private router: Router,
    private trfService: TrfService,
    private toastService: ToastService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    this.listState.search$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => { this.fetchTrfs(); });

    this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd),
        filter((event: NavigationEnd) => event.url === '/trf' || event.url.startsWith('/trf?')),
        takeUntil(this.destroy$)
      )
      .subscribe(() => {
        if (this.navigationRefreshReady) { this.fetchTrfs(); }
      });

    this.fetchTrfs();
    this.navigationRefreshReady = true;
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.listState.destroy();
  }

  onSearchChange(value: string): void {
    this.listState.setSearch(value);
  }

  fetchTrfs(): void {
    this.listState.setLoading(true);
    this.listState.clearError();

    const params: Record<string, unknown> = {
      ...this.listState.getFilters()
    };

    if (this.statusFilter) {
      params['status'] = this.statusFilter;
    }

    if (this.travelTypeFilter) {
      params['travel_type'] = this.travelTypeFilter;
    }

    if (this.sortKey && this.sortDirection) {
      params['sortBy'] = this.sortKey;
      params['sortOrder'] = this.sortDirection;
    }

    this.trfService.getAllTrfs(params)
      .pipe(
        takeUntil(this.destroy$),
        finalize(() => {
          this.listState.setLoading(false);
        })
      )
      .subscribe({
        next: (response: { results?: TrfListItem[]; count?: number } | TrfListItem[]) => {
          if (Array.isArray(response)) {
            this.trfs = response;
            this.listState.setTotalItems(response.length);
          } else {
            this.trfs = response.results ?? [];
            this.listState.setTotalItems(response.count ?? 0);
          }
          if (this.trfStatuses.length === 0) {
            this.trfStatuses = [...new Set(this.trfs.map(i => i.status).filter(Boolean))].sort();
          }
          if (this.travelTypes.length === 0) {
            this.travelTypes = [...new Set(this.trfs.map(i => i.travel_type).filter(Boolean))].sort();
          }
        },
        error: (err: { error?: { detail?: string }; statusText?: string; message?: string }) => {
          // Handle "Invalid page" error from DRF pagination
          if (err.error?.detail === 'Invalid page.' || err.statusText === 'Not Found') {
            this.listState.resetToFirstPage();
            this.fetchTrfs();
            return;
          }

          this.listState.setError(err.message ?? 'Failed to load TRFs');
          this.trfs = [];
        }
      });
  }

  onStatusFilterChange(): void {
    this.listState.resetToFirstPage();
    this.fetchTrfs();
  }

  onTravelTypeFilterChange(): void {
    this.listState.resetToFirstPage();
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
    this.listState.clearSearch();
    this.listState.clearFilters();
    this.statusFilter = '';
    this.travelTypeFilter = '';
    this.sortKey = 'submitted_at';
    this.sortDirection = 'descending';
    this.fetchTrfs();
  }

  hasActiveFilters(): boolean {
    return this.listState.hasActiveFilters() || this.statusFilter !== '' || this.travelTypeFilter !== '';
  }

  navigateToCreate(): void {
    this.router.navigate(['/trf/create']);
  }

  navigateToView(id: number): void {
    this.router.navigate(['/trf', id]);
  }

  navigateToEdit(id: number): void {
    this.router.navigate(['/trf/edit', id]);
  }

  private deleteConfirmId: number | null = null;
  private deleteConfirmTimeout: ReturnType<typeof setTimeout> | null = null;

  deleteTrf(id: number, event: Event): void {
    event.stopPropagation();

    if (this.deleteConfirmId === id) {
      if (this.deleteConfirmTimeout !== null) {
        clearTimeout(this.deleteConfirmTimeout);
      }
      this.deleteConfirmId = null;

      this.trfService.deleteTrf(id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            this.toastService.success('Travel request deleted successfully');
            this.trfStatuses = [];
            this.travelTypes = [];
            this.fetchTrfs();
          },
          error: () => {
            this.toastService.error('Failed to delete travel request');
          }
        });
    } else {
      this.deleteConfirmId = id;
      this.toastService.warning('Click delete again to confirm deletion');

      this.deleteConfirmTimeout = setTimeout(() => {
        this.deleteConfirmId = null;
      }, 3000);
    }
  }

  previousPage(): void {
    this.listState.previousPage();
    this.fetchTrfs();
  }

  nextPage(): void {
    this.listState.nextPage();
    this.fetchTrfs();
  }

  goToPage(page: number): void {
    this.listState.setCurrentPage(page);
    this.fetchTrfs();
  }

  get Math() {
    return Math;
  }

  getStatusBadgeClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  formatStatusDisplay(status: string): string {
    return status.replace(/_/g, ' ');
  }

  formatTravelTypeDisplay(type: string): string {
    return type.replace(/_/g, ' ');
  }
}
