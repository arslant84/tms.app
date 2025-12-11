import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, forkJoin } from 'rxjs';
import { VisaService, VisaApplication } from '../visa.service';
import { WorkflowService } from '../../core/services/workflow.service';
import { WorkflowInstanceList } from '../../core/models/workflow.models';
import { ToastService } from '../../core/services/toast.service';

@Component({
  selector: 'app-visa-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './visa-list.component.html',
  styleUrl: './visa-list.component.scss'
})
export class VisaListComponent implements OnInit, OnDestroy {
  applications: VisaApplication[] = [];
  isLoading = false;
  searchTerm = '';
  filterStatus = '';
  filterVisaType = '';

  // Workflow data
  workflowMap: Map<number, WorkflowInstanceList> = new Map();

  // Pagination
  currentPage = 1;
  pageSize = 10;
  totalCount = 0;
  Math = Math; // Expose Math to template

  // Filter options
  statuses = [
    'Pending Department Focal',
    'Submitted',
    'Under Review',
    'Approved',
    'Rejected',
    'Cancelled',
    'Processing',
    'Completed'
  ];

  visaTypes = [
    'Tourist',
    'Business',
    'Work',
    'Student',
    'Transit',
    'Diplomatic',
    'Official'
  ];

  private searchSubject = new Subject<string>();
  private destroy$ = new Subject<void>();

  constructor(
    private visaService: VisaService,
    public workflowService: WorkflowService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.setupSearch();
    this.fetchApplications();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  setupSearch(): void {
    this.searchSubject.pipe(
      debounceTime(500),
      distinctUntilChanged()
    ).subscribe(searchTerm => {
      this.searchTerm = searchTerm;
      this.resetToFirstPage();
      this.fetchApplications();
    });
  }

  onSearchChange(value: string): void {
    this.searchSubject.next(value);
  }

  onFilterChange(): void {
    this.resetToFirstPage();
    this.fetchApplications();
  }

  fetchApplications(): void {
    this.isLoading = true;
    const filters = {
      status: this.filterStatus,
      visa_type: this.filterVisaType,
      search: this.searchTerm,
      page: this.currentPage,
      page_size: this.pageSize
    };

    this.visaService.getAllApplications(filters).subscribe({
      next: (response) => {
        this.applications = response.results || response;
        this.totalCount = response.count || this.applications.length;
        this.isLoading = false;

        // Load workflow instances for each application
        this.loadWorkflowInstances();
      },
      error: (error) => {
        console.error('Error fetching visa applications:', error);
        this.isLoading = false;
      }
    });
  }

  loadWorkflowInstances(): void {
    if (this.applications.length === 0) return;

    // Fetch all workflow instances for visa applications
    this.workflowService.getInstances({
      entity_type: 'visaapplication'
    }).subscribe({
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
        console.error('Error loading workflow instances:', err);
      }
    });
  }

  getWorkflowForApplication(appId: number): WorkflowInstanceList | undefined {
    return this.workflowMap.get(appId);
  }

  getDisplayStatus(app: VisaApplication): string {
    const workflow = this.getWorkflowForApplication(app.id!);
    if (workflow) {
      return this.workflowService.getWorkflowStatus(workflow);
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

  resetToFirstPage(): void {
    this.currentPage = 1;
  }

  onPageChange(page: number): void {
    this.currentPage = page;
    this.fetchApplications();
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.fetchApplications();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.fetchApplications();
    }
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.fetchApplications();
    }
  }

  getPageNumbers(): number[] {
    const maxPagesToShow = 5;
    const pages: number[] = [];

    if (this.totalPages <= maxPagesToShow) {
      for (let i = 1; i <= this.totalPages; i++) {
        pages.push(i);
      }
    } else {
      const half = Math.floor(maxPagesToShow / 2);
      let start = Math.max(1, this.currentPage - half);
      let end = Math.min(this.totalPages, start + maxPagesToShow - 1);

      if (end - start < maxPagesToShow - 1) {
        start = Math.max(1, end - maxPagesToShow + 1);
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
    }

    return pages;
  }

  get totalPages(): number {
    return Math.ceil(this.totalCount / this.pageSize);
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

      this.visaService.deleteApplication(id).subscribe({
        next: () => {
          this.toastService.success('Visa application deleted successfully');
          this.fetchApplications();
        },
        error: (error) => {
          console.error('Error deleting visa application:', error);
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

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  getStatusBadgeClass(status: string): string {
    const statusMap: { [key: string]: string } = {
      'Pending Department Focal': 'badge-pending',
      'Pending Manager': 'badge-pending',
      'Pending HOD': 'badge-pending',
      'Pending Visa Clerk': 'badge-pending',
      'Submitted': 'badge-info',
      'Under Review': 'badge-info',
      'Approved': 'badge-success',
      'Rejected': 'badge-danger',
      'Cancelled': 'badge-secondary',
      'Processing': 'badge-processing',
      'Completed': 'badge-success',
      'Draft': 'badge-draft'
    };
    return statusMap[status] || 'badge-secondary';
  }

  /**
   * Check if any filters are currently active
   */
  hasActiveFilters(): boolean {
    return this.searchTerm !== '' || this.filterStatus !== '' || this.filterVisaType !== '';
  }

  /**
   * Clear all active filters and reset to first page
   */
  clearFilters(): void {
    this.searchTerm = '';
    this.filterStatus = '';
    this.filterVisaType = '';
    this.resetToFirstPage();
    this.fetchApplications();
  }
}
