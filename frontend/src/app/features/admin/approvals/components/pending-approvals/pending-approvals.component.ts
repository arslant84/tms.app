import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { environment } from '../../../../../../environments/environment';

interface ApprovableItem {
  id: string;
  requestorName: string;
  itemType: 'TSR' | 'Claim' | 'Visa' | 'Accommodation' | 'Transport';
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
  transportType?: string;
  documentNumber?: string;
}

@Component({
  selector: 'app-pending-approvals',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pending-approvals.component.html',
  styleUrls: ['./pending-approvals.component.scss']
})
export class PendingApprovalsComponent implements OnInit {
  pendingItems: ApprovableItem[] = [];
  filteredItems: ApprovableItem[] = [];
  isLoading = false;
  error: string | null = null;

  // Filters
  activeTab: 'all' | 'trf' | 'claim' | 'visa' | 'accommodation' | 'transport' = 'all';
  searchTerm = '';
  statusFilter = '';

  // Tab counts
  tabCounts = {
    all: 0,
    trf: 0,
    transport: 0,
    visa: 0,
    accommodation: 0,
    claim: 0
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

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.fetchPendingItems();
    this.fetchTabCounts();
  }

  fetchPendingItems(forceRefresh = false): void {
    this.isLoading = true;
    this.error = null;

    const typeFilter = this.activeTab === 'all' ? '' : `&type=${this.activeTab}`;
    const url = `${this.apiUrl}/admin/approvals/?page=${this.currentPage}&limit=${this.pageSize}${typeFilter}`;

    this.http.get<any>(url, { withCredentials: true }).subscribe({
      next: (data) => {
        console.log('=== PENDING APPROVALS PAGE DEBUG ===');
        console.log('API URL:', url);
        console.log('Full Response:', data);
        console.log('Total Count from API:', data.totalCount);
        console.log('Items Count:', data.items?.length);
        console.log('====================================');
        this.pendingItems = data.items || [];
        this.totalCount = data.totalCount || 0;
        this.totalPages = data.totalPages || 1;
        // Update the count for current tab
        if (this.activeTab === 'all') {
          this.tabCounts.all = this.totalCount;
        }
        this.applyFilters();
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error fetching approvals:', err);
        this.error = err.error?.error || 'Failed to load approval items';
        this.isLoading = false;
      }
    });
  }

  fetchTabCounts(): void {
    // Fetch counts for each tab type
    const types: Array<'trf' | 'transport' | 'visa' | 'accommodation' | 'claim'> =
      ['trf', 'transport', 'visa', 'accommodation', 'claim'];

    types.forEach(type => {
      const url = `${this.apiUrl}/admin/approvals/?page=1&limit=1&type=${type}`;
      this.http.get<any>(url, { withCredentials: true }).subscribe({
        next: (data) => {
          this.tabCounts[type] = data.totalCount || 0;
        },
        error: (err) => {
          console.error(`Error fetching count for ${type}:`, err);
          this.tabCounts[type] = 0;
        }
      });
    });
  }

  applyFilters(): void {
    let filtered = [...this.pendingItems];

    // Search filter
    if (this.searchTerm) {
      const search = this.searchTerm.toLowerCase();
      filtered = filtered.filter(item =>
        item.requestorName?.toLowerCase().includes(search) ||
        item.purpose?.toLowerCase().includes(search) ||
        item.department?.toLowerCase().includes(search) ||
        item.id?.toLowerCase().includes(search)
      );
    }

    // Status filter
    if (this.statusFilter) {
      filtered = filtered.filter(item => item.status === this.statusFilter);
    }

    this.filteredItems = filtered;
  }

  onTabChange(tab: 'all' | 'trf' | 'claim' | 'visa' | 'accommodation' | 'transport'): void {
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
      'TSR': 'bi-airplane',
      'Transport': 'bi-truck',
      'Visa': 'bi-passport',
      'Accommodation': 'bi-house-door',
      'Claim': 'bi-receipt'
    };
    return icons[itemType] || 'bi-file-text';
  }

  getStatusClass(status: string): string {
    const statusMap: { [key: string]: string } = {
      'Pending': 'badge-warning',
      'Pending Department Focal': 'badge-warning',
      'Pending HOD': 'badge-info',
      'Pending Travel Desk': 'badge-info',
      'Pending Finance': 'badge-info',
      'Pending Line Manager': 'badge-warning',
      'Approved': 'badge-success',
      'Rejected': 'badge-danger',
      'Draft': 'badge-secondary',
      'Submitted': 'badge-primary',
      'Under Review': 'badge-info'
    };
    return statusMap[status] || 'badge-secondary';
  }

  viewItem(item: ApprovableItem): void {
    const routes: { [key: string]: string } = {
      'TSR': `/trf/${item.id}`,
      'Transport': `/transport/${item.id}`,
      'Visa': `/visa/${item.id}`,
      'Accommodation': `/accommodation/${item.id}`,
      'Claim': `/expense-claims/${item.id}`
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
      'TSR': 'trf/travel-requests',
      'Transport': 'transport/requests',
      'Visa': 'visa/applications',
      'Accommodation': 'trf/travel-requests', // Accommodation uses TRF
      'Claim': 'expenses/claims'
    };

    const path = apiPaths[this.selectedItem.itemType];
    const url = `${this.apiUrl}/${path}/${this.selectedItem.id}/approve/`;

    // Get current step role from status
    const stepRole = this.extractRoleFromStatus(this.selectedItem.status);

    this.http.post(url, {
      step_role: stepRole,
      comments: this.approvalComments
    }).subscribe({
      next: () => {
        console.log('Item approved successfully');
        this.closeDialogs();
        this.fetchPendingItems(true);
        this.isActionPending = false;
      },
      error: (err) => {
        console.error('Error approving item:', err);
        const errorMsg = err.error?.error || err.error?.detail || 'Unknown error';

        // Handle specific error cases
        if (errorMsg.includes('No pending approval step')) {
          alert('This item has already been processed or is not awaiting your approval.');
          this.closeDialogs();
          this.fetchPendingItems(true); // Refresh to remove it from the list
        } else {
          alert('Failed to approve: ' + errorMsg);
        }
        this.isActionPending = false;
      }
    });
  }

  rejectItem(): void {
    if (!this.selectedItem || !this.rejectionComments) {
      alert('Rejection comments are required');
      return;
    }

    this.isActionPending = true;
    const apiPaths: { [key: string]: string } = {
      'TSR': 'trf/travel-requests',
      'Transport': 'transport/requests',
      'Visa': 'visa/applications',
      'Accommodation': 'trf/travel-requests',
      'Claim': 'expenses/claims'
    };

    const path = apiPaths[this.selectedItem.itemType];
    const url = `${this.apiUrl}/${path}/${this.selectedItem.id}/reject/`;

    const stepRole = this.extractRoleFromStatus(this.selectedItem.status);

    this.http.post(url, {
      step_role: stepRole,
      comments: this.rejectionComments
    }).subscribe({
      next: () => {
        console.log('Item rejected successfully');
        this.closeDialogs();
        this.fetchPendingItems(true);
        this.isActionPending = false;
      },
      error: (err) => {
        console.error('Error rejecting item:', err);
        alert('Failed to reject: ' + (err.error?.error || 'Unknown error'));
        this.isActionPending = false;
      }
    });
  }

  private extractRoleFromStatus(status: string): string {
    // Extract the role from status like "Pending Department Focal" -> "Department Focal"
    if (status.startsWith('Pending ')) {
      return status.substring(8); // Remove "Pending "
    }
    // Default roles for non-specific statuses
    return 'Department Focal';
  }

  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'Invalid Date';
    }
  }

  formatCurrency(amount: number | undefined): string {
    if (amount === undefined || amount === null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  }

  getItemTypeLabel(itemType: string): string {
    const labels: { [key: string]: string } = {
      'TSR': 'Travel Request',
      'Transport': 'Transport Request',
      'Visa': 'Visa Application',
      'Accommodation': 'Accommodation',
      'Claim': 'Expense Claim'
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
