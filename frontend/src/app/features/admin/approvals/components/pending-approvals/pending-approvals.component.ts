import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, type OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { environment } from '../../../../../../environments/environment';
import { DepartmentNamePipe } from '../../../../../core/pipes/department-name.pipe';
import { AppSettingsService } from '../../../../../core/services/app-settings.service';
import { ToastService } from '../../../../../core/services/toast.service';
import { DateUtilsService } from '../../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../../../shared/components/loading-spinner/loading-spinner.component';
import { NotificationService } from '../../../../notifications/services/notification.service';

interface ApprovableItem {
  id: string;
  requestNumber: string;
  requestorName: string;
  staffId?: string;
  itemType: 'TSR' | 'Visa' | 'Transport';
  purpose: string;
  status: string;
  submittedAt: string;
  amount?: number;
  destination?: string;
  travelType?: string;
  visaType?: string;
  checkInDate?: string;
  checkOutDate?: string;
  location?: string;
  department?: string;
  documentNumber?: string;
}

interface PendingApprovalsResponse {
  data?: ApprovableItem[];
  meta?: {
    pagination?: {
      total_count?: number;
      total_pages?: number;
    };
  };
}

@Component({
  selector: 'app-pending-approvals',
  standalone: true,
  imports: [CommonModule, FormsModule, DepartmentNamePipe, LoadingSpinnerComponent],
  templateUrl: './pending-approvals.component.html',
  styleUrls: ['./pending-approvals.component.scss'],
})
export class PendingApprovalsComponent implements OnInit {
  pendingItems: ApprovableItem[] = [];
  filteredItems: ApprovableItem[] = [];
  isLoading = false;
  error: string | null = null;

  // Filters
  activeTab: 'all' | 'trf' | 'visa' | 'transport' = 'all';
  searchTerm = '';
  statusFilter = '';

  // Tab counts
  tabCounts = {
    all: 0,
    trf: 0,
    transport: 0,
    visa: 0,
  };

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalCount = 0;
  totalPages = 0;

  // Action dialog
  selectedItem: ApprovableItem | null = null;
  showApproveDialog = false;
  showRejectDialog = false;
  approvalComments = '';
  rejectionComments = '';
  isActionPending = false;

  private apiUrl = environment.apiUrl;

  // Dynamic status options derived from real data
  statusOptions: string[] = [];

  private http = inject(HttpClient);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private notificationService = inject(NotificationService);
  private appSettingsService = inject(AppSettingsService);
  dateUtils = inject(DateUtilsService);
  private toastService = inject(ToastService);
  private statusUtils = inject(StatusUtilsService);

  ngOnInit(): void {
    // Check for query params (from notification click)
    this.route.queryParams.subscribe(params => {
      const itemId = params['id'];
      const itemType = params['type'];
      const action = params['action'];

      if (itemId && itemType && action === 'approve') {
        // Set the active tab based on item type
        this.setActiveTabFromType(itemType);

        // Fetch items and then auto-open the approve dialog
        this.fetchPendingItems();
        this.fetchTabCounts();

        // Wait for items to load and then open the dialog
        setTimeout(() => {
          this.openApproveDialogForItem(itemId);
          // Clear query params after opening the dialog. Deliberately NOT
          // passing queryParamsHandling: 'merge' here - merging an empty
          // object into the existing params is a no-op, so ?id=&type=&action=
          // used to stay in the URL forever. That left this branch armed:
          // clicking a second notification-required-approval link (any
          // click that resolves to the exact same /admin/approvals URL,
          // e.g. a second notification for the same item) matched Angular's
          // default onSameUrlNavigation: 'ignore' and silently did nothing,
          // which looked like "the second notification doesn't open" until
          // navigating elsewhere first. Omitting queryParamsHandling makes
          // this a full replace with the given (empty) object, which
          // actually clears the params.
          this.router.navigate([], {
            relativeTo: this.route,
            queryParams: {},
          });
        }, 1000);
      } else {
        this.fetchPendingItems();
        this.fetchTabCounts();
      }
    });
  }

  /**
   * Set active tab based on entity type
   */
  private setActiveTabFromType(type: string): void {
    const tabMap: {
      [key: string]: 'all' | 'trf' | 'visa' | 'transport';
    } = {
      trf: 'trf',
      transport: 'transport',
      visa: 'visa',
      expenses: 'all',
    };
    this.activeTab = tabMap[type] || 'all';
  }

  /**
   * Open approve dialog for a specific item by ID
   */
  private openApproveDialogForItem(itemId: string): void {
    const item = this.filteredItems.find(i => i.id === itemId);
    if (item) {
      this.openApproveDialog(item);
    } else {
      console.warn(`Could not find item with ID ${itemId} in current items`);
    }
  }

  fetchPendingItems(_forceRefresh = false): void {
    this.isLoading = true;
    this.error = null;

    const typeFilter = this.activeTab === 'all' ? '' : `&type=${this.activeTab}`;
    const url = `${this.apiUrl}/admin/approvals/?page=${this.currentPage}&limit=${this.pageSize}${typeFilter}`;

    this.http.get<PendingApprovalsResponse>(url, { withCredentials: true }).subscribe({
      next: data => {
        this.pendingItems = data.data || [];
        this.totalCount = data.meta?.pagination?.total_count || 0;
        this.totalPages = data.meta?.pagination?.total_pages || 1;
        // Update the count for current tab
        if (this.activeTab === 'all') {
          this.tabCounts.all = this.totalCount;
        }
        this.applyFilters();
        const uniqueStatuses = [
          ...new Set(this.pendingItems.map(i => i.status).filter(Boolean)),
        ].sort();
        if (uniqueStatuses.length > 0) {
          this.statusOptions = uniqueStatuses;
        }
        this.isLoading = false;
      },
      error: err => {
        console.error('Error fetching approvals:', err);
        this.error = err.error?.error || 'Failed to load approval items';
        this.isLoading = false;
      },
    });
  }

  fetchTabCounts(): void {
    // Fetch counts for each tab type
    const types: Array<'trf' | 'transport' | 'visa'> = ['trf', 'transport', 'visa'];

    types.forEach(type => {
      const url = `${this.apiUrl}/admin/approvals/?page=1&limit=1&type=${type}`;
      this.http.get<PendingApprovalsResponse>(url, { withCredentials: true }).subscribe({
        next: data => {
          this.tabCounts[type] = data.meta?.pagination?.total_count || 0;
        },
        error: err => {
          console.error(`Error fetching count for ${type}:`, err);
          this.tabCounts[type] = 0;
        },
      });
    });
  }

  applyFilters(): void {
    let filtered = [...this.pendingItems];

    // Search filter
    if (this.searchTerm) {
      const search = this.searchTerm.toLowerCase();
      filtered = filtered.filter(
        item =>
          item.requestorName?.toLowerCase().includes(search) ||
          item.purpose?.toLowerCase().includes(search) ||
          item.department?.toLowerCase().includes(search) ||
          item.requestNumber?.toLowerCase().includes(search) ||
          item.id?.toLowerCase().includes(search)
      );
    }

    // Status filter
    if (this.statusFilter) {
      filtered = filtered.filter(item => item.status === this.statusFilter);
    }

    this.filteredItems = filtered;
  }

  onTabChange(tab: 'all' | 'trf' | 'visa' | 'transport'): void {
    this.activeTab = tab;
    this.currentPage = 1;
    this.fetchPendingItems();
  }

  onSearchChange(): void {
    this.applyFilters();
  }

  onStatusFilterChange(): void {
    this.applyFilters();
  }

  getItemTypeIcon(itemType: string): string {
    const icons: { [key: string]: string } = {
      TSR: 'bi-airplane',
      Transport: 'bi-truck',
      Visa: 'bi-passport',
    };
    return icons[itemType] || 'bi-file-text';
  }

  /**
   * Get status badge class - delegates to StatusUtilsService so the same
   * status renders the same color everywhere in the app.
   */
  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  viewItem(item: ApprovableItem): void {
    const routes: { [key: string]: string } = {
      TSR: `/trf/${item.id}`,
      Transport: `/transport/${item.id}`,
      Visa: `/visa/${item.id}`,
    };

    const route = routes[item.itemType];
    if (route) {
      this.router.navigate([route]);
    }
  }

  openApproveDialog(item: ApprovableItem): void {
    this.selectedItem = item;
    this.approvalComments = '';
    this.showApproveDialog = true;
  }

  openRejectDialog(item: ApprovableItem): void {
    this.selectedItem = item;
    this.rejectionComments = '';
    this.showRejectDialog = true;
  }

  closeDialogs(): void {
    this.showApproveDialog = false;
    this.showRejectDialog = false;
    this.selectedItem = null;
    this.approvalComments = '';
    this.rejectionComments = '';
  }

  approveItem(): void {
    if (!this.selectedItem) return;

    this.isActionPending = true;
    const apiPaths: { [key: string]: string } = {
      TSR: 'trf/travel-requests',
      Transport: 'transport/requests',
      Visa: 'visa/applications',
    };

    const path = apiPaths[this.selectedItem.itemType];
    const url = `${this.apiUrl}/${path}/${this.selectedItem.id}/approve/`;

    // Get current step role from status
    const stepRole = this.extractRoleFromStatus(this.selectedItem.status);

    this.http
      .post(url, {
        step_role: stepRole,
        comments: this.approvalComments,
      })
      .subscribe({
        next: () => {
          this.closeDialogs();
          this.fetchPendingItems(true);
          // Refresh notifications to remove the actioned notification
          this.notificationService.refreshNotifications();
          this.isActionPending = false;
        },
        error: err => {
          console.error('Error approving item:', err);
          const errorMsg = err.error?.error || err.error?.detail || 'Unknown error';

          // Handle specific error cases
          if (errorMsg.includes('No pending approval step')) {
            this.toastService.warning(
              'This item has already been processed or is not awaiting your approval.'
            );
            this.closeDialogs();
            this.fetchPendingItems(true); // Refresh to remove it from the list
            // Refresh notifications
            this.notificationService.refreshNotifications();
          } else {
            this.toastService.error('Failed to approve: ' + errorMsg);
          }
          this.isActionPending = false;
        },
      });
  }

  rejectItem(): void {
    if (!this.selectedItem || !this.rejectionComments) {
      this.toastService.warning('Rejection comments are required');
      return;
    }

    this.isActionPending = true;
    const apiPaths: { [key: string]: string } = {
      TSR: 'trf/travel-requests',
      Transport: 'transport/requests',
      Visa: 'visa/applications',
    };

    const path = apiPaths[this.selectedItem.itemType];
    const url = `${this.apiUrl}/${path}/${this.selectedItem.id}/reject/`;

    const stepRole = this.extractRoleFromStatus(this.selectedItem.status);

    this.http
      .post(url, {
        step_role: stepRole,
        comments: this.rejectionComments,
      })
      .subscribe({
        next: () => {
          this.closeDialogs();
          this.fetchPendingItems(true);
          // Refresh notifications to remove the actioned notification
          this.notificationService.refreshNotifications();
          this.isActionPending = false;
        },
        error: err => {
          console.error('Error rejecting item:', err);
          this.toastService.error('Failed to reject: ' + (err.error?.error || 'Unknown error'));
          this.isActionPending = false;
        },
      });
  }

  private extractRoleFromStatus(status: string): string | undefined {
    // Extract the role from status like "Pending Department Focal" -> "Department Focal"
    if (status.startsWith('Pending ')) {
      return status.substring(8); // Remove "Pending "
    }
    // Don't default to a hardcoded role - let the backend determine the current step
    return undefined;
  }

  formatCurrency(amount: number | null | undefined, currency?: string | null): string {
    if (amount === null || amount === undefined || isNaN(amount)) {
      return 'N/A';
    }

    const currencyCode = currency || this.appSettingsService.getDefaultCurrency();

    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(amount);
    } catch (error) {
      console.error('Error formatting currency:', error);
      return `${currencyCode} ${amount.toFixed(2)}`;
    }
  }

  getItemTypeLabel(itemType: string): string {
    const labels: { [key: string]: string } = {
      TSR: 'Travel Request',
      Transport: 'Transport Request',
      Visa: 'Visa Application',
    };
    return labels[itemType] || itemType;
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.fetchPendingItems();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.fetchPendingItems();
    }
  }

  get startIndex(): number {
    return (this.currentPage - 1) * this.pageSize + 1;
  }

  get endIndex(): number {
    return Math.min(this.currentPage * this.pageSize, this.totalCount);
  }
}
