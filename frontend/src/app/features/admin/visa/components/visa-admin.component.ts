import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { VisaService, VisaApplication } from '../../../visa/services/visa.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';

@Component({
  selector: 'app-visa-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './visa-admin.component.html',
  styleUrl: './visa-admin.component.scss'
})
export class VisaAdminComponent implements OnInit {
  // Stats
  stats = {
    total: 0,
    pending: 0,
    approved: 0,
    processing: 0,
    completed: 0,
    rejected: 0
  };

  // Tab state
  activeTab: 'applications' | 'approvals' = 'applications';

  // Applications
  applications: VisaApplication[] = [];
  filteredApplications: VisaApplication[] = [];
  selectedApplication: VisaApplication | null = null;
  loadingApplications = false;

  // Filter criteria
  filterCriteria = {
    status: 'all',
    visaType: 'all',
    destination: 'all',
    search: ''
  };

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalApplications = 0;

  // Loading states
  error: string = '';
  processingId: number | null = null;

  // Process application modal
  showProcessModal: boolean = false;
  processAction: 'approve' | 'reject' | 'complete' | null = null;
  processComments: string = '';

  // Processing details fields (for complete action)
  visaNumber: string = '';
  visaValidFrom: string = '';
  visaValidTo: string = '';

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
    private confirmationService: ConfirmationService,
    public router: Router,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    this.fetchStats();
    this.loadApplications();
  }

  /**
   * Fetch visa application statistics
   */
  fetchStats(): void {
    this.visaService.getAllApplications({ adminView: true }).subscribe({
      next: (response: any) => {
        const applications = response.results || response || [];

        this.stats.total = applications.length;
        this.stats.pending = applications.filter((app: any) =>
          app.status && (app.status.toLowerCase().includes('pending') || app.status === 'Submitted')
        ).length;
        this.stats.approved = applications.filter((app: any) =>
          app.status === 'Approved'
        ).length;
        this.stats.processing = applications.filter((app: any) =>
          app.status && (app.status.toLowerCase().includes('processing') || app.status === 'Under Review')
        ).length;
        this.stats.completed = applications.filter((app: any) =>
          app.status === 'Completed'
        ).length;
        this.stats.rejected = applications.filter((app: any) =>
          app.status === 'Rejected' || app.status === 'Cancelled'
        ).length;
      },
      error: (err) => {
        // Keep default values on error
      }
    });
  }

  /**
   * Set active tab
   */
  setActiveTab(tab: 'applications' | 'approvals'): void {
    this.activeTab = tab;
  }

  /**
   * Load visa applications from API
   */
  loadApplications(): void {
    this.loadingApplications = true;
    this.error = '';

    const filters: any = {
      page: this.currentPage,
      page_size: this.pageSize,
      adminView: true  // Show all visa applications for admin processing
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
        this.applyClientSideFilters();
        this.loadingApplications = false;
      },
      error: (err) => {
        this.error = 'Failed to load visa applications: ' + (err.error?.message || err.message || 'Unknown error');
        this.loadingApplications = false;
      }
    });
  }

  /**
   * Apply client-side filters
   */
  applyClientSideFilters(): void {
    this.filteredApplications = this.applications.filter(app => {
      const matchesDestination = this.filterCriteria.destination === 'all' ||
        app.destination === this.filterCriteria.destination;
      return matchesDestination;
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
      destination: 'all',
      search: ''
    };
    this.currentPage = 1;
    this.loadApplications();
  }

  /**
   * Get unique destinations
   */
  get uniqueDestinations(): string[] {
    const destinations = this.applications
      .map(app => app.destination)
      .filter((dest, index, self) => dest && self.indexOf(dest) === index);
    return Array.from(new Set(destinations));
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
    this.visaNumber = '';
    this.visaValidFrom = '';
    this.visaValidTo = '';
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
      // Complete - use the proper complete endpoint
      const completionData: any = {};
      if (this.processComments) {
        completionData.additional_comments = this.processComments;
      }

      // Add processing details if any field is provided
      if (this.visaNumber || this.visaValidFrom || this.visaValidTo || this.processComments) {
        completionData.processing_details = {
          visa_number: this.visaNumber,
          visa_valid_from: this.visaValidFrom,
          visa_valid_to: this.visaValidTo,
          processing_notes: this.processComments,
          completed_by_admin: true,
          completed_at: new Date().toISOString()
        };
      }

      action$ = this.visaService.completeApplication(this.selectedApplication.id, completionData);
    }

    action$.subscribe({
      next: (response) => {
        const actionLabel = this.processAction === 'approve' ? 'approved' :
                           this.processAction === 'reject' ? 'rejected' : 'completed';
        this.toastService.success(`Application ${actionLabel} successfully`);
        this.closeProcessModal();
        this.processingId = null;
        this.fetchStats(); // Refresh stats
        this.loadApplications();
      },
      error: (err) => {
        this.toastService.error('Failed to process application: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
      }
    });
  }

  /**
   * Start processing
   */
  startProcessing(application: VisaApplication): void {
    this.confirmationService.confirm({
      title: 'Start Processing',
      message: `Start processing application #${application.id}?`,
      confirmText: 'Start',
      type: 'info'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeStartProcessing(application);
    });
  }

  private executeStartProcessing(application: VisaApplication): void {
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
      }
    });
  }

  /**
   * Badge classes
   */
  getStatusBadgeClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  getVisaTypeBadgeClass(visaType: string): string {
    return this.statusUtils.getVisaTypeBadgeClass(visaType);
  }

  getDestinationBadgeClass(destination: string): string {
    // Simple hash-based color assignment
    const hash = destination?.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) || 0;
    const colors = ['badge-blue', 'badge-green', 'badge-purple', 'badge-amber', 'badge-indigo'];
    return colors[hash % colors.length];
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
