import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AccommodationService, AccommodationRequest, AccommodationRoom, AccommodationStaffHouse } from '../../accommodation/services/accommodation.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-accommodation-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './accommodation-admin.component.html',
  styleUrl: './accommodation-admin.component.scss'
})
export class AccommodationAdminComponent implements OnInit {
  requests: AccommodationRequest[] = [];
  filteredRequests: AccommodationRequest[] = [];
  selectedRequest: AccommodationRequest | null = null;

  // Filter criteria
  filterCriteria = {
    status: 'all',
    search: '',
    dateFrom: '',
    dateTo: ''
  };

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalRequests = 0;

  // Loading states
  loading: boolean = true;
  error: string = '';
  processingId: number | null = null;

  // Assign room modal
  showAssignRoomModal: boolean = false;
  staffHouses: AccommodationStaffHouse[] = [];
  availableRooms: AccommodationRoom[] = [];
  roomAssignment = {
    staff_house: null as number | null,
    room: null as number | null,
    check_in_date: '',
    check_out_date: '',
    notes: ''
  };

  // Status options for filter
  statusOptions = [
    { value: 'all', label: 'All Statuses' },
    { value: 'Pending Approval', label: 'Pending Approval' },
    { value: 'Approved', label: 'Approved' },
    { value: 'Confirmed', label: 'Confirmed' },
    { value: 'Checked In', label: 'Checked In' },
    { value: 'Checked Out', label: 'Checked Out' },
    { value: 'Rejected', label: 'Rejected' },
    { value: 'Cancelled', label: 'Cancelled' }
  ];

  constructor(
    private accommodationService: AccommodationService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadRequests();
    this.loadStaffHouses();
  }

  /**
   * Load accommodation requests from API
   */
  loadRequests(): void {
    this.loading = true;
    this.error = '';

    const filters: any = {
      page: this.currentPage,
      page_size: this.pageSize
    };

    if (this.filterCriteria.status !== 'all') {
      filters.status = this.filterCriteria.status;
    }

    if (this.filterCriteria.search) {
      filters.search = this.filterCriteria.search;
    }

    this.accommodationService.getAllRequests(filters).subscribe({
      next: (response) => {
        this.requests = response.results || response;
        this.totalRequests = response.count || this.requests.length;
        this.filteredRequests = [...this.requests];
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load accommodation requests: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading requests:', err);
      }
    });
  }

  /**
   * Load staff houses
   */
  loadStaffHouses(): void {
    this.accommodationService.getAllStaffHouses().subscribe({
      next: (houses) => {
        this.staffHouses = houses;
      },
      error: (err) => {
        console.error('Error loading staff houses:', err);
      }
    });
  }

  /**
   * Load available rooms for selected staff house
   */
  loadAvailableRooms(): void {
    if (!this.roomAssignment.staff_house) {
      this.availableRooms = [];
      return;
    }

    this.accommodationService.getAllRooms(this.roomAssignment.staff_house).subscribe({
      next: (rooms) => {
        this.availableRooms = rooms.filter(room => room.status === 'Available');
      },
      error: (err) => {
        console.error('Error loading rooms:', err);
        this.toastService.error('Failed to load rooms');
      }
    });
  }

  /**
   * Apply filters
   */
  applyFilters(): void {
    this.currentPage = 1;
    this.loadRequests();
  }

  /**
   * Reset filters
   */
  resetFilters(): void {
    this.filterCriteria = {
      status: 'all',
      search: '',
      dateFrom: '',
      dateTo: ''
    };
    this.currentPage = 1;
    this.loadRequests();
  }

  /**
   * Change page
   */
  changePage(page: number): void {
    this.currentPage = page;
    this.loadRequests();
  }

  /**
   * View request details
   */
  viewRequest(request: AccommodationRequest): void {
    this.router.navigate(['/accommodation', request.id]);
  }

  /**
   * Open assign room modal
   */
  openAssignRoomModal(request: AccommodationRequest): void {
    this.selectedRequest = request;
    this.roomAssignment = {
      staff_house: null,
      room: null,
      check_in_date: '',
      check_out_date: '',
      notes: ''
    };
    this.availableRooms = [];
    this.showAssignRoomModal = true;
  }

  /**
   * Close assign room modal
   */
  closeAssignRoomModal(): void {
    this.showAssignRoomModal = false;
    this.selectedRequest = null;
    this.roomAssignment = {
      staff_house: null,
      room: null,
      check_in_date: '',
      check_out_date: '',
      notes: ''
    };
    this.availableRooms = [];
  }

  /**
   * Assign room to request
   */
  assignRoom(): void {
    if (!this.selectedRequest) return;

    if (!this.roomAssignment.staff_house || !this.roomAssignment.room ||
        !this.roomAssignment.check_in_date || !this.roomAssignment.check_out_date) {
      this.toastService.error('Please fill in all required fields');
      return;
    }

    this.processingId = this.selectedRequest.id;

    const bookingData = {
      accommodation_request: this.selectedRequest.id,
      staff_house: this.roomAssignment.staff_house,
      room: this.roomAssignment.room,
      date: this.roomAssignment.check_in_date,
      status: 'Confirmed',
      notes: this.roomAssignment.notes
    };

    this.accommodationService.createBooking(bookingData).subscribe({
      next: () => {
        this.toastService.success('Room assigned successfully');
        this.closeAssignRoomModal();
        this.processingId = null;
        this.loadRequests();
      },
      error: (err) => {
        this.toastService.error('Failed to assign room: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error assigning room:', err);
      }
    });
  }

  /**
   * Approve request
   */
  approveRequest(request: AccommodationRequest): void {
    if (!confirm(`Are you sure you want to approve request #${request.id}?`)) {
      return;
    }

    this.processingId = request.id;

    this.accommodationService.approveRequest(request.id, 'Approved by Admin').subscribe({
      next: () => {
        this.toastService.success('Request approved successfully');
        this.processingId = null;
        this.loadRequests();
      },
      error: (err) => {
        this.toastService.error('Failed to approve request: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error approving request:', err);
      }
    });
  }

  /**
   * Reject request
   */
  rejectRequest(request: AccommodationRequest): void {
    const reason = prompt('Please provide a reason for rejection:');

    if (!reason || reason.trim() === '') {
      this.toastService.error('Rejection reason is required');
      return;
    }

    this.processingId = request.id;

    this.accommodationService.rejectRequest(request.id, reason).subscribe({
      next: () => {
        this.toastService.success('Request rejected successfully');
        this.processingId = null;
        this.loadRequests();
      },
      error: (err) => {
        this.toastService.error('Failed to reject request: ' + (err.error?.message || err.message || 'Unknown error'));
        this.processingId = null;
        console.error('Error rejecting request:', err);
      }
    });
  }

  /**
   * Get status badge class
   */
  getStatusClass(status: string): string {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('checked out')) return 'badge bg-success';
    if (statusLower.includes('checked in')) return 'badge bg-info';
    if (statusLower.includes('confirmed') || statusLower.includes('approved')) return 'badge bg-primary';
    if (statusLower.includes('rejected')) return 'badge bg-danger';
    if (statusLower.includes('cancelled')) return 'badge bg-secondary';
    if (statusLower.includes('pending')) return 'badge bg-warning';
    return 'badge bg-secondary';
  }

  /**
   * Format currency
   */
  formatCurrency(amount: number | null | undefined): string {
    if (amount === null || amount === undefined) return 'N/A';
    return amount.toLocaleString('en-MY', { style: 'currency', currency: 'MYR' });
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
   * Check if request can be approved
   */
  canApprove(request: AccommodationRequest): boolean {
    return request.status === 'Pending Approval';
  }

  /**
   * Check if room can be assigned
   */
  canAssignRoom(request: AccommodationRequest): boolean {
    return request.status === 'Approved' || request.status === 'Confirmed';
  }

  /**
   * Check if request is processing
   */
  isProcessing(requestId: number): boolean {
    return this.processingId === requestId;
  }

  /**
   * Get total pages
   */
  get totalPages(): number {
    return Math.ceil(this.totalRequests / this.pageSize);
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
}
