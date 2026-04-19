import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { VisaService, VisaApplication } from '../../services/visa.service';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { WorkflowInstanceList } from '../../../../core/models/workflow.models';
import { ToastService } from '../../../../core/services/toast.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { ListStateService } from '../../../../core/services/list-state.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';


@Component({
  selector: 'app-visa-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './visa-list.component.html',
  styleUrl: './visa-list.component.scss'
})
export class VisaListComponent implements OnInit, OnDestroy {
  applications: VisaApplication[] = [];
  filterStatus = '';
  filterVisaType = '';

  private destroy$ = new Subject<void>();

  // Workflow data
  workflowMap: Map<number, WorkflowInstanceList> = new Map();

  Math = Math; // Expose Math to template

  // Filter options populated dynamically from actual data
  statuses: string[] = [];
  visaTypes: string[] = [];

  // Create list state service manually (not via DI)
  listState = new ListStateService({ pageSize: 10 });

  constructor(
    private visaService: VisaService,
    public workflowService: WorkflowService,
    private toastService: ToastService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    this.listState.search$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => { this.fetchApplications(); });

    this.fetchApplications();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.listState.destroy();
  }

  onSearchChange(value: string): void {
    this.listState.setSearch(value);
  }

  onFilterChange(): void {
    this.listState.resetToFirstPage();
    this.fetchApplications();
  }

  fetchApplications(): void {
    this.listState.setLoading(true);

    // Add filter parameters to the request
    const filters = {
      ...this.listState.getFilters(),
      ...(this.filterStatus && { status: this.filterStatus }),
      ...(this.filterVisaType && { visa_type: this.filterVisaType })
    };

    this.visaService.getAllApplications(filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.applications = response.results || response;
          this.listState.setTotalItems(response.count || this.applications.length);
          this.listState.setLoading(false);

          if (this.statuses.length === 0) {
            this.statuses = [...new Set(this.applications.map(i => i.status ?? '').filter(Boolean))].sort();
          }
          if (this.visaTypes.length === 0) {
            this.visaTypes = [...new Set(this.applications.map(i => i.visa_type ?? '').filter(Boolean))].sort();
          }

          this.loadWorkflowInstances();
        },
        error: (error) => {
          // Handle "Invalid page" error from DRF pagination
          if (error.error?.detail === 'Invalid page.' || error.statusText === 'Not Found') {
            // Reset to first page and retry
            this.listState.resetToFirstPage();
            this.fetchApplications();
            return;
          }

          this.listState.setLoading(false);
        }
      });
  }

  loadWorkflowInstances(): void {
    if (this.applications.length === 0) return;

    // Fetch all workflow instances for visa applications
    this.workflowService.getInstances({
      entity_type: 'visaapplication'
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: any) => {
          // Handle both paginated response and array response
          const instances = Array.isArray(response) ? response : (response.results || []);

          // Create a map of entity_id to workflow instance
          this.workflowMap.clear();

          instances.forEach((instance: any) => {
            const entityId = instance.object_id || instance.entity_info?.id || instance.entity_id;
            if (entityId) {
              this.workflowMap.set(entityId, instance);
            }
          });
        },
        error: (err) => {
        }
      });
  }

  getWorkflowForApplication(appId: number): WorkflowInstanceList | undefined {
    return this.workflowMap.get(appId);
  }

  getDisplayStatus(app: VisaApplication): string {
    const workflow = this.getWorkflowForApplication(app.id!);
    if (workflow) {
      // For terminal states (approved, rejected, cancelled), use workflow status
      // For in_progress, use app.status which contains the detailed step name
      if (['approved', 'rejected', 'cancelled'].includes(workflow.status)) {
        return this.workflowService.getWorkflowStatus(workflow);
      }
      // Use application status for in-progress workflows (contains step details)
      return app.status || this.workflowService.getWorkflowStatus(workflow);
    }
    return app.status || 'Draft';
  }

  getDisplayStatusClass(app: VisaApplication): string {
    const workflow = this.getWorkflowForApplication(app.id!);
    if (workflow) {
      return this.workflowService.getWorkflowStatusClass(workflow);
    }
    return this.getStatusBadgeClass(app.status || 'Draft');
  }

  onPageChange(page: number): void {
    this.listState.setCurrentPage(page);
    this.fetchApplications();
  }

  previousPage(): void {
    this.listState.previousPage();
    this.fetchApplications();
  }

  nextPage(): void {
    this.listState.nextPage();
    this.fetchApplications();
  }

  goToPage(page: number): void {
    this.listState.setCurrentPage(page);
    this.fetchApplications();
  }

  navigateToDetail(id: number): void {
    // Navigation handled by routerLink in template
  }

  navigateToEdit(id: number): void {
    // Navigation handled by routerLink in template
  }

  private deleteConfirmId: number | null = null;
  private deleteConfirmTimeout: any = null;

  deleteApplication(id: number, event: Event): void {
    event.stopPropagation();

    // If this is the second click on the same item within 3 seconds, proceed with deletion
    if (this.deleteConfirmId === id) {
      clearTimeout(this.deleteConfirmTimeout);
      this.deleteConfirmId = null;

      this.visaService.deleteApplication(id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            this.toastService.success('Visa application deleted successfully');
            this.fetchApplications();
          },
          error: (error) => {
            this.toastService.error('Failed to delete visa application');
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


  getStatusBadgeClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Check if any filters are currently active
   */
  hasActiveFilters(): boolean {
    return this.listState.hasActiveFilters() || this.filterStatus !== '' || this.filterVisaType !== '';
  }

  /**
   * Clear all active filters and reset to first page
   */
  clearFilters(): void {
    this.listState.clearSearch();
    this.listState.clearFilters();
    this.filterStatus = '';
    this.filterVisaType = '';
    this.fetchApplications();
  }
}
