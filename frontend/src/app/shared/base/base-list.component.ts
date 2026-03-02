import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { Subject, Observable } from 'rxjs';
import { takeUntil, filter, finalize } from 'rxjs/operators';
import { ListStateService } from '../../core/services/list-state.service';
import { ToastService } from '../../core/services/toast.service';
import { DateUtilsService } from '../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../core/utils/status-utils.service';

/**
 * Base class for list components with common functionality.
 *
 * Provides:
 * - ListStateService for pagination, search, and loading state
 * - Subscription cleanup with destroy$
 * - Common pagination methods
 * - Delete confirmation pattern
 * - Navigation refresh handling
 *
 * Usage:
 * ```typescript
 * export class TrfListComponent extends BaseListComponent<TrfListItem> {
 *   protected entityName = 'trf';
 *   protected basePath = '/trf';
 *
 *   constructor(private trfService: TrfService) {
 *     super();
 *   }
 *
 *   protected fetchDataFromService(): Observable<any> {
 *     return this.trfService.getAllTrfs(this.buildFetchParams());
 *   }
 *
 *   protected deleteFromService(id: number): Observable<any> {
 *     return this.trfService.deleteTrf(id);
 *   }
 * }
 * ```
 */
@Component({
  template: '' // Abstract component - no template
})
export abstract class BaseListComponent<T> implements OnInit, OnDestroy {
  // Injected services
  protected router = inject(Router);
  protected toastService = inject(ToastService);
  public dateUtils = inject(DateUtilsService);
  public statusUtils = inject(StatusUtilsService);

  // Configuration - override in subclass
  protected abstract entityName: string; // e.g., 'trf', 'accommodation', 'transport'
  protected abstract basePath: string;   // e.g., '/trf', '/accommodation'
  protected pageSize = 10;
  protected enableNavigationRefresh = true;

  // State
  protected destroy$ = new Subject<void>();
  items: T[] = [];
  listState = new ListStateService({ pageSize: this.pageSize });

  // Sort configuration
  sortKey: string | null = 'created_at';
  sortDirection: 'ascending' | 'descending' = 'descending';

  // Delete confirmation state
  private deleteConfirmId: number | null = null;
  private deleteConfirmTimeout: any = null;

  // Filter properties - override in subclass for additional filters
  statusFilter = '';

  /**
   * Abstract method to fetch data from service.
   * Subclass must implement this to call the appropriate service method.
   */
  protected abstract fetchDataFromService(): Observable<any>;

  /**
   * Abstract method to delete item from service.
   * Subclass must implement this to call the appropriate delete method.
   */
  protected abstract deleteFromService(id: number): Observable<any>;

  /**
   * Get status badge CSS class.
   * Override in subclass if different status utility method is needed.
   */
  getStatusBadgeClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  ngOnInit(): void {
    this.setupSearchSubscription();
    this.setupNavigationRefresh();
    this.onInit();
    this.fetchData();
  }

  /**
   * Hook for subclass initialization.
   * Override this instead of ngOnInit to add custom initialization.
   */
  protected onInit(): void {
    // Override in subclass
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.listState.destroy();
    this.clearDeleteConfirmTimeout();
    this.onDestroy();
  }

  /**
   * Hook for subclass cleanup.
   * Override this instead of ngOnDestroy to add custom cleanup.
   */
  protected onDestroy(): void {
    // Override in subclass
  }

  /**
   * Setup search subscription with automatic data fetch.
   */
  private setupSearchSubscription(): void {
    this.listState.search$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.fetchData();
      });
  }

  /**
   * Setup navigation refresh - refetch data when navigating back to this page.
   */
  private setupNavigationRefresh(): void {
    if (!this.enableNavigationRefresh) return;

    this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd),
        filter((event: NavigationEnd) =>
          event.url === this.basePath || event.url.startsWith(`${this.basePath}?`)
        ),
        takeUntil(this.destroy$)
      )
      .subscribe(() => {
        this.fetchData();
      });
  }

  /**
   * Fetch data from service with loading state management.
   */
  fetchData(): void {
    this.listState.setLoading(true);
    this.listState.clearError();

    this.fetchDataFromService()
      .pipe(
        takeUntil(this.destroy$),
        finalize(() => {
          this.listState.setLoading(false);
        })
      )
      .subscribe({
        next: (response: any) => {
          this.handleFetchResponse(response);
        },
        error: (err) => {
          this.handleFetchError(err);
        }
      });
  }

  /**
   * Handle successful fetch response.
   * Override to customize response handling.
   */
  protected handleFetchResponse(response: any): void {
    // Handle both array response and paginated response
    if (Array.isArray(response)) {
      this.items = response;
      this.listState.setTotalItems(response.length);
    } else {
      this.items = response.results || response.data || [];
      this.listState.setTotalItems(
        response.count || response.totalCount || response.meta?.pagination?.total_count || 0
      );
    }
  }

  /**
   * Handle fetch error.
   * Override to customize error handling.
   */
  protected handleFetchError(err: any): void {
    const entityLabel = this.formatEntityLabel();
    this.listState.setError(err.message || `Failed to load ${entityLabel}`);
    this.items = [];
  }

  /**
   * Build fetch parameters including filters, pagination, and sorting.
   * Override to add custom parameters.
   */
  protected buildFetchParams(): any {
    const params: any = {
      ...this.listState.getFilters(),
      limit: this.listState.getPageSize(),
      page: this.listState.getCurrentPage()
    };

    if (this.statusFilter) {
      params.status = this.statusFilter;
    }

    if (this.sortKey && this.sortDirection) {
      params.sortBy = this.sortKey;
      params.sortOrder = this.sortDirection;
    }

    return params;
  }

  // ==================== Search & Filter Methods ====================

  onSearchChange(value: string): void {
    this.listState.setSearch(value);
  }

  onStatusFilterChange(): void {
    this.listState.resetToFirstPage();
    this.fetchData();
  }

  clearFilters(): void {
    this.listState.clearSearch();
    this.listState.clearFilters();
    this.statusFilter = '';
    this.sortKey = 'created_at';
    this.sortDirection = 'descending';
    this.onClearFilters();
    this.fetchData();
  }

  /**
   * Hook for subclass to clear additional filters.
   */
  protected onClearFilters(): void {
    // Override in subclass
  }

  hasActiveFilters(): boolean {
    return this.listState.hasActiveFilters() || this.statusFilter !== '';
  }

  // ==================== Sorting Methods ====================

  handleSort(key: string): void {
    if (this.sortKey === key) {
      this.sortDirection = this.sortDirection === 'ascending' ? 'descending' : 'ascending';
    } else {
      this.sortKey = key;
      this.sortDirection = 'ascending';
    }
    this.fetchData();
  }

  // ==================== Pagination Methods ====================

  previousPage(): void {
    this.listState.previousPage();
    this.fetchData();
  }

  nextPage(): void {
    this.listState.nextPage();
    this.fetchData();
  }

  goToPage(page: number): void {
    this.listState.setCurrentPage(page);
    this.fetchData();
  }

  get startIndex(): number {
    return (this.listState.getCurrentPage() - 1) * this.listState.getPageSize() + 1;
  }

  get endIndex(): number {
    return Math.min(
      this.listState.getCurrentPage() * this.listState.getPageSize(),
      this.listState.getTotalItems()
    );
  }

  // ==================== Navigation Methods ====================

  navigateToCreate(): void {
    this.router.navigate([`${this.basePath}/create`]);
  }

  navigateToView(id: number): void {
    this.router.navigate([this.basePath, id]);
  }

  navigateToEdit(id: number): void {
    this.router.navigate([`${this.basePath}/edit`, id]);
  }

  // ==================== Delete Methods ====================

  /**
   * Delete item with double-click confirmation.
   * First click shows warning, second click within 3 seconds confirms deletion.
   */
  deleteItem(id: number, event: Event): void {
    event.stopPropagation();

    if (this.deleteConfirmId === id) {
      // Second click - confirm deletion
      this.clearDeleteConfirmTimeout();
      this.deleteConfirmId = null;
      this.performDelete(id);
    } else {
      // First click - show confirmation
      this.deleteConfirmId = id;
      const entityLabel = this.formatEntityLabel();
      this.toastService.warning(`Click delete again to confirm deletion`);

      this.deleteConfirmTimeout = setTimeout(() => {
        this.deleteConfirmId = null;
      }, 3000);
    }
  }

  private performDelete(id: number): void {
    this.deleteFromService(id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          const entityLabel = this.formatEntityLabel();
          this.toastService.success(`${entityLabel} deleted successfully`);
          this.fetchData();
        },
        error: () => {
          const entityLabel = this.formatEntityLabel();
          this.toastService.error(`Failed to delete ${entityLabel}`);
        }
      });
  }

  private clearDeleteConfirmTimeout(): void {
    if (this.deleteConfirmTimeout) {
      clearTimeout(this.deleteConfirmTimeout);
      this.deleteConfirmTimeout = null;
    }
  }

  isDeletePending(id: number): boolean {
    return this.deleteConfirmId === id;
  }

  // ==================== Utility Methods ====================

  /**
   * Format entity name for display (e.g., 'trf' -> 'Travel request')
   */
  protected formatEntityLabel(): string {
    const labels: Record<string, string> = {
      'trf': 'Travel request',
      'accommodation': 'Accommodation request',
      'transport': 'Transport request',
      'visa': 'Visa application',
      'flight': 'Flight booking',
      'notification': 'Notification'
    };
    return labels[this.entityName] || this.entityName;
  }

  formatStatusDisplay(status: string): string {
    return status.replace(/_/g, ' ');
  }

  /**
   * Math utility for templates
   */
  get Math() {
    return Math;
  }
}
