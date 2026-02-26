import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApprovalsService, ApprovalRequest } from '../services/approvals.service';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmationService } from '../../../core/services/confirmation.service';
import { CurrencyFormatPipe } from '../../../core/pipes/currency-format.pipe';
import { DateUtilsService } from '../../../core/utils/date-utils.service';

@Component({
  selector: 'app-pending-approvals',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyFormatPipe],
  templateUrl: './pending-approvals.component.html',
  styleUrl: './pending-approvals.component.scss'
})
export class PendingApprovalsComponent implements OnInit {
  pendingRequests: ApprovalRequest[] = [];
  filteredRequests: ApprovalRequest[] = [];
  selectedRequest: ApprovalRequest | null = null;

  // Tab management
  activeTab: 'all' | 'trf' | 'accommodation' | 'transport' | 'visa' | 'expense' = 'all';

  // Filter criteria
  filterCriteria = {
    department: 'all',
    priority: 'all',
    search: ''
  };

  // For comments when approving/rejecting
  approvalComment: string = '';
  isProcessing: boolean = false;
  loading: boolean = true;
  error: string = '';

  constructor(
    private approvalsService: ApprovalsService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private router: Router,
    public dateUtils: DateUtilsService
  ) {}

  ngOnInit(): void {
    this.loadPendingApprovals();
  }
  
  /**
   * Load pending approvals from API
   */
  loadPendingApprovals(): void {
    this.loading = true;
    this.error = '';

    const loadObservable = this.activeTab === 'all'
      ? this.approvalsService.getAllPendingApprovals()
      : this.approvalsService.getPendingApprovalsByType(this.activeTab);

    loadObservable.subscribe({
      next: (approvals) => {
        this.pendingRequests = approvals;
        this.applyFilters();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load pending approvals: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading pending approvals:', err);
      }
    });
  }

  /**
   * Switch active tab
   */
  switchTab(tab: 'all' | 'trf' | 'accommodation' | 'transport' | 'visa' | 'expense'): void {
    this.activeTab = tab;
    this.selectedRequest = null;
    this.loadPendingApprovals();
  }

  /**
   * Get count for a specific tab
   */
  getTabCount(type: string): number {
    if (type === 'all') return this.pendingRequests.length;
    return this.pendingRequests.filter(req => req.type === type).length;
  }
  
  /**
   * Apply filters to the requests
   */
  applyFilters(): void {
    this.filteredRequests = this.pendingRequests.filter(request => {
      // Department filter
      if (this.filterCriteria.department !== 'all' &&
          request.requester.department.toLowerCase() !== this.filterCriteria.department.toLowerCase()) {
        return false;
      }

      // Priority filter
      if (this.filterCriteria.priority !== 'all' && request.priority !== this.filterCriteria.priority) {
        return false;
      }

      // Search filter (search in title and requester name)
      if (this.filterCriteria.search) {
        const searchTerm = this.filterCriteria.search.toLowerCase();
        return request.title.toLowerCase().includes(searchTerm) ||
               request.requester.name.toLowerCase().includes(searchTerm);
      }

      return true;
    });
  }

  /**
   * Reset all filters
   */
  resetFilters(): void {
    this.filterCriteria = {
      department: 'all',
      priority: 'all',
      search: ''
    };
    this.applyFilters();
  }
  
  /**
   * Select a request to view details
   */
  selectRequest(request: ApprovalRequest): void {
    this.selectedRequest = request;
    this.approvalComment = '';
  }

  /**
   * Close the details panel
   */
  closeDetails(): void {
    this.selectedRequest = null;
  }

  /**
   * View full details of request
   */
  viewFullDetails(): void {
    if (!this.selectedRequest) return;

    const routes: { [key: string]: string } = {
      trf: `/trf/${this.selectedRequest.id}`,
      accommodation: `/accommodation/${this.selectedRequest.id}`,
      transport: `/transport/${this.selectedRequest.id}`,
      visa: `/visa/${this.selectedRequest.id}`,
      expense: `/expenses/${this.selectedRequest.id}`
    };

    const route = routes[this.selectedRequest.type];
    if (route) {
      this.router.navigate([route]);
    }
  }

  /**
   * Approve a request
   */
  approveRequest(): void {
    if (!this.selectedRequest) return;

    this.confirmationService.confirm({
      title: 'Confirm Approval',
      message: 'Are you sure you want to approve this request?',
      confirmText: 'Approve',
      type: 'success'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeApproveRequest();
    });
  }

  private executeApproveRequest(): void {
    if (!this.selectedRequest) return;
    this.isProcessing = true;

    // Extract step role from current approval step or use default
    const stepRole = this.extractStepRole(this.selectedRequest.currentApprovalStep);

    this.approvalsService.approveRequest(
      this.selectedRequest.type,
      this.selectedRequest.id,
      this.approvalComment,
      stepRole
    ).subscribe({
      next: () => {
        this.toastService.success('Request approved successfully');

        // Remove from pending list
        this.pendingRequests = this.pendingRequests.filter(r => r.id !== this.selectedRequest!.id);
        this.applyFilters();

        this.isProcessing = false;
        this.selectedRequest = null;
        this.approvalComment = '';
      },
      error: (err) => {
        this.toastService.error('Failed to approve request: ' + (err.error?.message || err.message || 'Unknown error'));
        this.isProcessing = false;
        console.error('Error approving request:', err);
      }
    });
  }

  /**
   * Reject a request
   */
  rejectRequest(): void {
    if (!this.selectedRequest) return;

    if (!this.approvalComment || this.approvalComment.trim() === '') {
      this.toastService.error('Please provide a reason for rejection');
      return;
    }

    this.confirmationService.confirm({
      title: 'Confirm Rejection',
      message: 'Are you sure you want to reject this request?',
      confirmText: 'Reject',
      type: 'danger'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeRejectRequest();
    });
  }

  private executeRejectRequest(): void {
    if (!this.selectedRequest) return;
    this.isProcessing = true;

    // Extract step role from current approval step or use default
    const stepRole = this.extractStepRole(this.selectedRequest.currentApprovalStep);

    this.approvalsService.rejectRequest(
      this.selectedRequest.type,
      this.selectedRequest.id,
      this.approvalComment,
      stepRole
    ).subscribe({
      next: () => {
        this.toastService.success('Request rejected successfully');

        // Remove from pending list
        this.pendingRequests = this.pendingRequests.filter(r => r.id !== this.selectedRequest!.id);
        this.applyFilters();

        this.isProcessing = false;
        this.selectedRequest = null;
        this.approvalComment = '';
      },
      error: (err) => {
        this.toastService.error('Failed to reject request: ' + (err.error?.message || err.message || 'Unknown error'));
        this.isProcessing = false;
        console.error('Error rejecting request:', err);
      }
    });
  }
  
  /**
   * Extract step role from current approval step string
   * Dynamically extracts role name from status like "Pending Department Focal" -> "Department Focal"
   */
  private extractStepRole(currentStep?: string): string | undefined {
    if (!currentStep) {
      // Don't default to a hardcoded role - let the backend determine the current step
      return undefined;
    }

    // Extract role from status strings like "Pending {RoleName}"
    if (currentStep.startsWith('Pending ')) {
      return currentStep.substring(8); // Remove "Pending " prefix
    }

    // If status doesn't follow "Pending X" pattern, return as-is
    // The backend will handle validation
    return currentStep;
  }

  /**
   * Get CSS class based on priority
   */
  getPriorityClass(priority: string): string {
    switch(priority) {
      case 'high': return 'priority-high';
      case 'medium': return 'priority-medium';
      case 'low': return 'priority-low';
      default: return '';
    }
  }

  /**
   * Get icon based on request type
   */
  getTypeIcon(type: string): string {
    switch(type) {
      case 'trf': return 'bi-airplane';
      case 'accommodation': return 'bi-building';
      case 'transport': return 'bi-truck';
      case 'visa': return 'bi-file-text';
      case 'expense': return 'bi-file-text';
      default: return 'bi-file-earmark';
    }
  }

  /**
   * Check if a request is overdue
   */
  isOverdue(request: ApprovalRequest): boolean {
    if (!request.deadline) return false;

    const deadlineDate = new Date(request.deadline);
    const today = new Date();

    return deadlineDate < today;
  }

}
