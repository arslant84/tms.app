import { BehaviorSubject, Subject, Observable } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

/**
 * Paginated List State Configuration
 */
export interface ListStateConfig {
  pageSize?: number;
  searchDebounceMs?: number;
}

/**
 * Filter parameters for API requests
 */
export interface ListFilters {
  search?: string;
  page?: number;
  page_size?: number;
  [key: string]: any; // Allow additional filter fields
}

/**
 * Reusable List State Service
 *
 * Handles common list functionality:
 * - Search with debouncing
 * - Pagination
 * - Filtering
 * - Loading states
 *
 * Usage in component:
 * ```typescript
 * export class MyListComponent implements OnInit, OnDestroy {
 *   listState = new ListStateService({ pageSize: 20 });
 *   items: MyItem[] = [];
 *
 *   ngOnInit() {
 *     this.listState.search$.subscribe(() => this.loadItems());
 *     this.listState.filters$.subscribe(() => this.loadItems());
 *     this.loadItems();
 *   }
 *
 *   loadItems() {
 *     this.listState.setLoading(true);
 *     this.myService.getAll(this.listState.getFilters()).subscribe({
 *       next: (response) => {
 *         this.items = response.results;
 *         this.listState.setTotalItems(response.count);
 *         this.listState.setLoading(false);
 *       },
 *       error: () => this.listState.setLoading(false)
 *     });
 *   }
 *
 *   ngOnDestroy() {
 *     this.listState.destroy();
 *   }
 * }
 * ```
 *
 * NOTE: This service is NOT provided via dependency injection.
 * Create it manually in your component as shown above.
 */
export class ListStateService {
  // Configuration
  private config: Required<ListStateConfig>;

  // State
  private currentPage$ = new BehaviorSubject<number>(1);
  private totalItems$ = new BehaviorSubject<number>(0);
  private loading$ = new BehaviorSubject<boolean>(false);
  private error$ = new BehaviorSubject<string>('');

  // Search
  private searchTerm$ = new BehaviorSubject<string>('');
  private searchSubject = new Subject<string>();

  // Filters
  private filters$ = new BehaviorSubject<{ [key: string]: any }>({});

  // Observables for components
  readonly currentPage: Observable<number> = this.currentPage$.asObservable();
  readonly totalItems: Observable<number> = this.totalItems$.asObservable();
  readonly loading: Observable<boolean> = this.loading$.asObservable();
  readonly error: Observable<string> = this.error$.asObservable();
  readonly searchTerm: Observable<string> = this.searchTerm$.asObservable();
  readonly search$: Observable<string>;
  readonly filters: Observable<{ [key: string]: any }> = this.filters$.asObservable();

  constructor(config: ListStateConfig = {}) {
    this.config = {
      pageSize: config.pageSize || 10,
      searchDebounceMs: config.searchDebounceMs || 500
    };

    // Setup debounced search
    this.search$ = this.searchSubject.pipe(
      debounceTime(this.config.searchDebounceMs),
      distinctUntilChanged()
    );
  }

  // ========== SEARCH METHODS ==========

  /**
   * Set search term (triggers debounced search)
   */
  setSearch(value: string): void {
    this.searchSubject.next(value);
    this.searchTerm$.next(value);
    this.resetToFirstPage();
  }

  /**
   * Get current search term
   */
  getSearchTerm(): string {
    return this.searchTerm$.value;
  }

  /**
   * Clear search term
   */
  clearSearch(): void {
    this.setSearch('');
  }

  // ========== FILTER METHODS ==========

  /**
   * Set a filter value
   */
  setFilter(key: string, value: any): void {
    const currentFilters = this.filters$.value;
    this.filters$.next({ ...currentFilters, [key]: value });
    this.resetToFirstPage();
  }

  /**
   * Set multiple filters at once
   */
  setFilters(filters: { [key: string]: any }): void {
    this.filters$.next({ ...filters });
    this.resetToFirstPage();
  }

  /**
   * Get current filter value
   */
  getFilter(key: string): any {
    return this.filters$.value[key];
  }

  /**
   * Get all current filters
   */
  getAllFilters(): { [key: string]: any } {
    return this.filters$.value;
  }

  /**
   * Clear all filters
   */
  clearFilters(): void {
    this.filters$.next({});
    this.resetToFirstPage();
  }

  /**
   * Clear a specific filter
   */
  clearFilter(key: string): void {
    const currentFilters = { ...this.filters$.value };
    delete currentFilters[key];
    this.filters$.next(currentFilters);
    this.resetToFirstPage();
  }

  /**
   * Check if any filters are active
   */
  hasActiveFilters(): boolean {
    const filters = this.filters$.value;
    return Object.keys(filters).some(key => {
      const value = filters[key];
      return value !== '' && value !== null && value !== undefined;
    }) || this.searchTerm$.value !== '';
  }

  // ========== PAGINATION METHODS ==========

  /**
   * Get current page number
   */
  getCurrentPage(): number {
    return this.currentPage$.value;
  }

  /**
   * Set current page
   */
  setCurrentPage(page: number): void {
    if (page >= 1 && page <= this.getTotalPages()) {
      this.currentPage$.next(page);
    }
  }

  /**
   * Go to next page
   */
  nextPage(): void {
    const nextPage = this.currentPage$.value + 1;
    if (nextPage <= this.getTotalPages()) {
      this.currentPage$.next(nextPage);
    }
  }

  /**
   * Go to previous page
   */
  previousPage(): void {
    const prevPage = this.currentPage$.value - 1;
    if (prevPage >= 1) {
      this.currentPage$.next(prevPage);
    }
  }

  /**
   * Reset to first page
   */
  resetToFirstPage(): void {
    this.currentPage$.next(1);
  }

  /**
   * Get total number of pages
   */
  getTotalPages(): number {
    return Math.ceil(this.totalItems$.value / this.config.pageSize);
  }

  /**
   * Get page size
   */
  getPageSize(): number {
    return this.config.pageSize;
  }

  /**
   * Set total items count (from API response)
   */
  setTotalItems(count: number): void {
    this.totalItems$.next(count);
  }

  /**
   * Get total items count
   */
  getTotalItems(): number {
    return this.totalItems$.value;
  }

  /**
   * Get array of page numbers for pagination UI
   * @param maxPagesToShow Maximum number of page buttons to show (default: 5)
   */
  getPageNumbers(maxPagesToShow: number = 5): number[] {
    const totalPages = this.getTotalPages();
    const currentPage = this.currentPage$.value;
    const pages: number[] = [];

    if (totalPages <= maxPagesToShow) {
      // Show all pages
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Show subset with current page in middle
      const half = Math.floor(maxPagesToShow / 2);
      let start = Math.max(1, currentPage - half);
      let end = Math.min(totalPages, start + maxPagesToShow - 1);

      // Adjust if we're at the end
      if (end - start < maxPagesToShow - 1) {
        start = Math.max(1, end - maxPagesToShow + 1);
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
    }

    return pages;
  }

  /**
   * Check if there is a next page
   */
  hasNextPage(): boolean {
    return this.currentPage$.value < this.getTotalPages();
  }

  /**
   * Check if there is a previous page
   */
  hasPreviousPage(): boolean {
    return this.currentPage$.value > 1;
  }

  // ========== LOADING & ERROR STATE ==========

  /**
   * Set loading state
   */
  setLoading(loading: boolean): void {
    this.loading$.next(loading);
  }

  /**
   * Get current loading state
   */
  isLoading(): boolean {
    return this.loading$.value;
  }

  /**
   * Set error message
   */
  setError(error: string): void {
    this.error$.next(error);
  }

  /**
   * Clear error message
   */
  clearError(): void {
    this.error$.next('');
  }

  /**
   * Get current error message
   */
  getError(): string {
    return this.error$.value;
  }

  // ========== UTILITY METHODS ==========

  /**
   * Get complete filter object for API requests
   * Includes search, pagination, and custom filters
   */
  getFilters(): ListFilters {
    const search = this.searchTerm$.value;
    const filters = this.filters$.value;

    return {
      ...(search && { search }),
      page: this.currentPage$.value,
      page_size: this.config.pageSize,
      ...filters
    };
  }

  /**
   * Cleanup subscriptions
   * Call this in ngOnDestroy
   */
  destroy(): void {
    this.currentPage$.complete();
    this.totalItems$.complete();
    this.loading$.complete();
    this.error$.complete();
    this.searchTerm$.complete();
    this.searchSubject.complete();
    this.filters$.complete();
  }
}
