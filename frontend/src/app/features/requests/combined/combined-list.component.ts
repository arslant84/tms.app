import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil, finalize, filter } from 'rxjs/operators';
import { CombinedRequestService } from './services/combined-request.service';
import { ToastService } from '../../../core/services/toast.service';
import { DateUtilsService } from '../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../core/utils/status-utils.service';
import { ListStateService } from '../../../core/services/list-state.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

interface CombinedListItem {
  id: number;
  requestNumber?: string;
  requestorName?: string;
  staffId?: string;
  department?: string;
  status?: string;
  submittedAt?: string;
  travelPurpose?: string;
  transportPurpose?: string;
  includeTravel?: boolean;
  includeTransport?: boolean;
  includeAccommodation?: boolean;
  includeVisa?: boolean;
}

@Component({
  selector: 'app-combined-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './combined-list.component.html',
  styleUrls: ['./combined-list.component.scss']
})
export class CombinedListComponent implements OnInit, OnDestroy {
  requests: CombinedListItem[] = [];
  statusFilter = '';
  private destroy$ = new Subject<void>();
  listState = new ListStateService({ pageSize: 10 });
  statuses: string[] = [];

  get Math() { return Math; }

  constructor(
    private router: Router,
    private combinedRequestService: CombinedRequestService,
    private toastService: ToastService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    this.listState.search$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.fetchRequests());

    this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd),
        filter((event: NavigationEnd) => event.url === '/combined' || event.url.startsWith('/combined?')),
        takeUntil(this.destroy$)
      )
      .subscribe(() => this.fetchRequests());

    this.fetchRequests();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.listState.destroy();
  }

  fetchRequests(): void {
    this.listState.setLoading(true);
    this.listState.clearError();

    const filters: Record<string, unknown> = { ...this.listState.getFilters() };
    if (this.statusFilter) filters['status'] = this.statusFilter;

    this.combinedRequestService.getAll(filters as any)
      .pipe(takeUntil(this.destroy$), finalize(() => this.listState.setLoading(false)))
      .subscribe({
        next: (response) => {
          this.requests = (response.results ?? []) as unknown as CombinedListItem[];
          this.listState.setTotalItems(response.count ?? 0);
          if (this.statuses.length === 0) {
            this.statuses = [...new Set(this.requests.map(r => r.status ?? '').filter(Boolean))].sort();
          }
        },
        error: (err) => {
          this.listState.setError(err.message ?? 'Failed to load combined requests');
          this.requests = [];
        }
      });
  }

  onSearchChange(value: string): void { this.listState.setSearch(value); }
  onStatusFilterChange(): void { this.listState.resetToFirstPage(); this.fetchRequests(); }

  clearFilters(): void {
    this.statusFilter = '';
    this.listState.clearSearch();
    this.listState.clearFilters();
    this.fetchRequests();
  }

  hasActiveFilters(): boolean {
    return this.listState.hasActiveFilters() || this.statusFilter !== '';
  }

  previousPage(): void { this.listState.previousPage(); this.fetchRequests(); }
  nextPage(): void { this.listState.nextPage(); this.fetchRequests(); }
  goToPage(page: number): void { this.listState.setCurrentPage(page); this.fetchRequests(); }

  getStatusBadgeClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  getModuleIcons(item: CombinedListItem): { icon: string; title: string }[] {
    const modules: { icon: string; title: string }[] = [];
    if (item.includeTravel) modules.push({ icon: 'bi-airplane', title: 'TSR' });
    if (item.includeTransport) modules.push({ icon: 'bi-truck', title: 'Transport' });
    if (item.includeAccommodation) modules.push({ icon: 'bi-house-door', title: 'Accommodation' });
    if (item.includeVisa) modules.push({ icon: 'bi-passport', title: 'Visa' });
    return modules;
  }

  private deleteConfirmId: number | null = null;
  private deleteConfirmTimeout: ReturnType<typeof setTimeout> | null = null;

  deleteRequest(id: number, event: Event): void {
    event.stopPropagation();
    if (this.deleteConfirmId === id) {
      if (this.deleteConfirmTimeout !== null) clearTimeout(this.deleteConfirmTimeout);
      this.deleteConfirmId = null;
      this.combinedRequestService.delete(id).pipe(takeUntil(this.destroy$)).subscribe({
        next: () => { this.toastService.success('Combined request deleted'); this.fetchRequests(); },
        error: () => this.toastService.error('Failed to delete request')
      });
    } else {
      this.deleteConfirmId = id;
      this.toastService.warning('Click delete again to confirm');
      this.deleteConfirmTimeout = setTimeout(() => { this.deleteConfirmId = null; }, 3000);
    }
  }
}
