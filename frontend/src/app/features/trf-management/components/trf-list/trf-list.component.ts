import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TrfService } from '../../services/trf.service';
import { TravelRequestForm } from '../../../../core/models/trf.model';
import { ToastService } from '../../../../core/services/toast.service';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { finalize, takeUntil } from 'rxjs/operators';
import { Subject } from 'rxjs';
import { filter } from 'rxjs/operators';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { ListStateService } from '../../../../core/services/list-state.service';

// Base statuses that don't come from workflow (Draft, Approved, Rejected, etc.)
const BASE_STATUSES = ['Draft', 'Approved', 'Rejected', 'Cancelled', 'Completed'];

export const TRAVEL_TYPES = [
  'Domestic',
  'International',
  'Local',
  'Field Visit'
];

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
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './trf-list.component.html',
  styleUrls: ['./trf-list.component.scss']
})
export class TrfListComponent implements OnInit, OnDestroy {
  // Filter properties
  statusFilter = '';
  travelTypeFilter = '';

  private destroy$ = new Subject<void>();

  // TRF data
  trfs: TrfListItem[] = [];

  // Sort configuration
  sortKey: string | null = 'submitted_at';
  sortDirection: 'ascending' | 'descending' = 'descending';

  // Dynamic statuses loaded from workflow template
  trfStatuses: string[] = [...BASE_STATUSES];
  readonly TRAVEL_TYPES = TRAVEL_TYPES;

  // Create list state service manually (not via DI)
  listState = new ListStateService({ pageSize: 10 });

  constructor(
    private router: Router,
    private trfService: TrfService,
    private toastService: ToastService,
    private workflowService: WorkflowService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    // Load workflow statuses dynamically
    this.loadWorkflowStatuses();

    // Subscribe to debounced search changes
    this.listState.search$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.fetchTrfs();
      });

    // Refresh list when navigating back to this page
    this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd),
        filter((event: any) => event.url === '/trf' || event.url.startsWith('/trf?')),
        takeUntil(this.destroy$)
      )
      .subscribe(() => {
        this.fetchTrfs();
      });

    // Load initial data
    this.fetchTrfs();
  }

  /**
   * Load workflow statuses dynamically from workflow template
   */
  private loadWorkflowStatuses(): void {
    this.workflowService.getTemplates({ entity_type: 'travelrequest', is_active: true })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (templates) => {
          if (templates && templates.length > 0) {
            const template = templates[0];
            // Build statuses from workflow steps
            const workflowStatuses: string[] = ['Draft'];

            if (template.steps && template.steps.length > 0) {
              // Sort steps by order and create "Pending {step_name}" statuses
              const sortedSteps = [...template.steps].sort((a, b) => a.step_order - b.step_order);
              for (const step of sortedSteps) {
                workflowStatuses.push(`Pending ${step.step_name}`);
              }
            }

            // Add terminal statuses
            workflowStatuses.push('Approved', 'Rejected', 'Cancelled', 'Completed');
            this.trfStatuses = workflowStatuses;
          }
        },
        error: (err) => {
          console.error('Error loading workflow statuses:', err);
          // Keep default statuses on error
        }
      });
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

    const params: any = {
      ...this.listState.getFilters(),
      limit: this.listState.getPageSize()
    };

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
        takeUntil(this.destroy$),
        finalize(() => {
          this.listState.setLoading(false);
        })
      )
      .subscribe({
        next: (response: any) => {
          // Handle both array response and paginated response
          if (Array.isArray(response)) {
            // Direct array response from Django
            this.trfs = response;
            this.listState.setTotalItems(response.length);
          } else {
            // Paginated response
            this.trfs = response.results || response.trfs || [];
            this.listState.setTotalItems(response.count || response.totalCount || 0);
          }
        },
        error: (err) => {
          this.listState.setError(err.message || 'Failed to load TRFs');
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
  private deleteConfirmTimeout: any = null;

  deleteTrf(id: number, event: Event): void {
    event.stopPropagation();

    // If this is the second click on the same item within 3 seconds, proceed with deletion
    if (this.deleteConfirmId === id) {
      clearTimeout(this.deleteConfirmTimeout);
      this.deleteConfirmId = null;

      this.trfService.deleteTrf(id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            this.toastService.success('Travel request deleted successfully');
            this.fetchTrfs();
          },
          error: (error: any) => {
            this.toastService.error('Failed to delete travel request');
          }
        });
    } else {
      // First click - show confirmation toast
      this.deleteConfirmId = id;
      this.toastService.warning('Click delete again to confirm deletion');

      // Reset confirmation after 3 seconds
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
