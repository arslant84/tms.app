import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { VisaService, VisaApplication } from '../../../visa/visa.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-visa-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './visa-admin.component.html',
  styleUrl: './visa-admin.component.scss'
})
export class VisaAdminComponent implements OnInit {
  applications: VisaApplication[] = [];
  filteredApplications: VisaApplication[] = [];
  selectedApplication: VisaApplication | null = null;

  // Filter criteria
  filterCriteria = {
    status: 'all',
    visaType: 'all',
    search: '',
    dateFrom: '',
    dateTo: ''
  };

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalApplications = 0;

  // Loading states
  loading: boolean = true;
  error: string = '';
  processingId: number | null = null;

  // Process application modal
  showProcessModal: boolean = false;
  processAction: 'approve' | 'reject' | 'complete' | null = null;
  processComments: string = '';

  // Status options for filter
  statusOptions = [
    { value: 'all', label: 'All Statuses' },
    { value: 'Pending Department Focal', label: 'Pending Department Focal' },
    { value: 'Submitted', label: 'Submitted' },
    { value: 'Under Review', label: 'Under Review' },
    { value: 'Approved', label: 'Approved' },
    { value: 'Rejected', label: 'Rejected' },
    { value: 'Cancelled', label: 'Cancelled' },
    { value: 'Processing', label: 'Processing' },
    { value: 'Completed', label: 'Completed' }
  ];

  // Visa type options
  visaTypeOptions = [
    { value: 'all', label: 'All Types' },
    { value: 'Tourist', label: 'Tourist' },
    { value: 'Business', label: 'Business' },
    { value: 'Work', label: 'Work' },
    { value: 'Student', label: 'Student' },
    { value: 'Transit', label: 'Transit' },
    { value: 'Diplomatic', label: 'Diplomatic' },
    { value: 'Official', label: 'Official' }
  ];

  constructor(
    private visaService: VisaService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadApplications();
  }

  /**
   * Load visa applications from API
   */
  loadApplications(): void {
    this.loading = true;
    this.error = '';

    const filters: any = {
      page: this.currentPage,
      page_size: this.pageSize
    };

    if (this.filterCriteria.status !== 'all') {
      filters.status = this.filterCriteria.status;
    }

    if (this.filterCriteria.visaType !== 'all') {
      filters.visa_type = this.filterCriteria.visaType;
    }

    if (this.filterCriteria.search) {
      filters.search = this.filterCriteria.search;
    }

    this.visaService.getAllApplications(filters).subscribe({
      next: (response) => {
        this.applications = response.results || response;
        this.totalApplications = response.count || this.applications.length;
        this.filteredApplications = [...this.applications];
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load visa applications: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading applications:', err);
      }
    });
  }

  /**
   * Apply filters
   */
  applyFilters(): void {
    this.currentPage = 1;
    this.loadApplications();
  }

  /**
   * Reset filters
   */
  resetFilters(): void {
    this.filterCriteria = {
      status: 'all',
      visaType: 'all',
      search: '',
      dateFrom: '',
      dateTo: ''
    };
    this.currentPage = 1;
    this.loadApplications();
  }

  /**
   * Change page
   */
  changePage(page: number): void {
    this.currentPage = page;
    this.loadApplications();
  }

  /**
   * View application details
   */
  viewApplication(application: VisaApplication): void {
    this.router.navigate(['/visa', application.id]);
  }

  /**
   * Open process modal
   */
  openProcessModal(application: VisaApplication, action: 'approve' | 'reject' | 'complete'): void {
    this.selectedApplication = application;
    this.processAction = action;
    this.processComments = '';
    this.showProcessModal = true;
  }

  /**
   * Close process modal
   */
  closeProcessModal(): void {
    this.showProcessModal = false;
    this.selectedApplication = null;
    this.processAction = null;
    this.processComments = '';
  }

  /**
   * Process application
   */
  processApplication(): void {
    if (!this.selectedApplication || !this.processAction) return;

    if (this.processAction === 'reject' && !this.processComments.trim()) {
      this.toastService.error('Please provide rejection comments');
      return;
    }

    this.processingId = this.selectedApplication.id;

    let action$;
    if (this.processAction === 'approve') {
      action$ = this.visaService.approveApplication(this.selectedApplication.id, this.processComments);
    } else if (this.processAction === 'reject') {
      action$ = this.visaService.rejectApplication(this.selectedApplication.id, this.processComments);
    } else {
      // Complete - update status to 'Completed'
      action$ = this.visaService.updateApplication(this.selectedApplication.id, {
        status: 'Completed',
        additional_comments: this.processComments,
        processing_completed_at: new Date().toISOString()
      });
    }

    action$.subscribe({
      next: () => {
        const actionLabel = this.processAction === 'approve' ? 'approved' :
                           this.processAction === 'reject' ? 'rejected' : 'completed';
        this.toastService.success(`Application ${actionLabel} successfully`);
        this.closeProcessModal();
        this.processingId = null;
        this.loadApplications();
      },
      error: (err) => {
        this.toastService.error('Failed to process application: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error processing application:', err);
      }
    });
  }

  /**
   * Start processing
   */
  startProcessing(application: VisaApplication): void {
    if (!confirm(`Start processing application #${application.id}?`)) {
      return;
    }

    this.processingId = application.id;

    this.visaService.updateApplication(application.id, {
      status: 'Processing',
      processing_started_at: new Date().toISOString()
    }).subscribe({
      next: () => {
        this.toastService.success('Application moved to processing');
        this.processingId = null;
        this.loadApplications();
      },
      error: (err) => {
        this.toastService.error('Failed to start processing: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error starting processing:', err);
      }
    });
  }

  /**
   * Get status badge class
   */
  getStatusClass(status: string): string {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('completed')) return 'badge bg-success';
    if (statusLower.includes('approved')) return 'badge bg-primary';
    if (statusLower.includes('processing') || statusLower.includes('under review')) return 'badge bg-info';
    if (statusLower.includes('rejected')) return 'badge bg-danger';
    if (statusLower.includes('cancelled')) return 'badge bg-secondary';
    if (statusLower.includes('pending') || statusLower.includes('submitted')) return 'badge bg-warning';
    return 'badge bg-secondary';
  }

  /**
   * Get visa type badge
   */
  getVisaTypeBadge(visaType: string): string {
    const typeLower = visaType.toLowerCase();
    if (typeLower === 'business' || typeLower === 'work') return 'badge bg-primary';
    if (typeLower === 'diplomatic' || typeLower === 'official') return 'badge bg-warning text-dark';
    if (typeLower === 'student') return 'badge bg-info';
    if (typeLower === 'tourist' || typeLower === 'transit') return 'badge bg-secondary';
    return 'badge bg-secondary';
  }

  /**
   * Format date
   */
  formatDate(date: string | Date | null | undefined): string {
    if (!date) return 'N/A';
    try {
      const d = typeof date === 'string' ? new Date(date) : date;
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return 'Invalid Date';
    }
  }

  /**
   * Check if application can be approved
   */
  canApprove(application: VisaApplication): boolean {
    return application.status === 'Submitted' || application.status === 'Under Review';
  }

  /**
   * Check if application can be rejected
   */
  canReject(application: VisaApplication): boolean {
    return application.status === 'Submitted' || application.status === 'Under Review';
  }

  /**
   * Check if processing can be started
   */
  canStartProcessing(application: VisaApplication): boolean {
    return application.status === 'Approved';
  }

  /**
   * Check if application can be completed
   */
  canComplete(application: VisaApplication): boolean {
    return application.status === 'Processing';
  }

  /**
   * Check if application is processing
   */
  isProcessing(applicationId: number): boolean {
    return this.processingId === applicationId;
  }

  /**
   * Get total pages
   */
  get totalPages(): number {
    return Math.ceil(this.totalApplications / this.pageSize);
  }

  /**
   * Get page numbers for pagination
   */
  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxPages = 5;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxPages / 2));
    let endPage = Math.min(this.totalPages, startPage + maxPages - 1);

    if (endPage - startPage + 1 < maxPages) {
      startPage = Math.max(1, endPage - maxPages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    return pages;
  }

  /**
   * Get action label for modal
   */
  getActionLabel(): string {
    if (this.processAction === 'approve') return 'Approve';
    if (this.processAction === 'reject') return 'Reject';
    if (this.processAction === 'complete') return 'Complete';
    return '';
  }
}
