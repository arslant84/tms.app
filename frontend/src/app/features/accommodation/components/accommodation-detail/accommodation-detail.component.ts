import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { AccommodationService } from '../../services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { ApprovalActionsComponent } from '../../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../../../core/models/workflow.models';
import {
  AccommodationRequestDetails,
  DailyBooking,
  ApprovalStep,
  accommodationToFrontend,
  calculateNights,
  getStatusBadgeClass,
  isEditable,
  isCancellable,
  isDeletable,
  formatTime12Hour
} from '../../models/accommodation.model';

@Component({
  selector: 'app-accommodation-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, WorkflowStatusComponent, ApprovalActionsComponent],
  templateUrl: './accommodation-detail.component.html',
  styleUrls: ['./accommodation-detail.component.scss']
})
export class AccommodationDetailComponent implements OnInit {
  request: AccommodationRequestDetails | null = null;
  loading: boolean = true;
  error: string = '';
  requestId!: number;

  // Calculated values
  numberOfNights: number = 0;
  hasAssignment: boolean = false;
  hasBookingRecords: boolean = false;
  isRejected: boolean = false;
  hasAdminNotes: boolean = false;

  // Workflow properties
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;
  currentStepExecution: WorkflowStepExecution | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private accommodationService: AccommodationService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.requestId = +params['id'];
      if (this.requestId) {
        this.loadRequestDetails();
        this.loadWorkflow();
      }
    });
  }

  loadRequestDetails(): void {
    this.loading = true;
    this.error = '';

    this.accommodationService.getRequestById(this.requestId).subscribe({
      next: (data) => {
        // Convert backend format to frontend format
        this.request = accommodationToFrontend(data as any);
        this.calculateDerivedValues();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load accommodation request: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading accommodation request:', err);
      }
    });
  }

  calculateDerivedValues(): void {
    if (!this.request) return;

    // Calculate nights
    this.numberOfNights = calculateNights(
      this.request.requestedCheckInDate,
      this.request.requestedCheckOutDate
    );

    // Check if has assignment
    this.hasAssignment = !!(
      this.request.assignedRoomId &&
      this.request.assignedRoomName &&
      this.request.assignedStaffHouseId &&
      this.request.assignedStaffHouseName
    );

    // Check if has booking records
    this.hasBookingRecords = !!(
      this.request.dailyBookings &&
      this.request.dailyBookings.length > 0
    );

    // Check if rejected
    this.isRejected = this.request.status === 'Rejected' && !!this.request.rejectionDetails;

    // Check if has admin notes
    this.hasAdminNotes = !!(this.request.notes && this.request.notes.trim().length > 0);
  }

  canEdit(): boolean {
    return this.request ? isEditable(this.request.status) : false;
  }

  canCancel(): boolean {
    return this.request ? isCancellable(this.request.status) : false;
  }

  canDelete(): boolean {
    return this.request ? isDeletable(this.request.status) : false;
  }

  getStatusClass(): string {
    return this.request ? getStatusBadgeClass(this.request.status) : 'badge-secondary';
  }

  goBack(): void {
    this.router.navigate(['/accommodation']);
  }

  onEdit(): void {
    // Check if request can be edited
    if (!this.canEdit()) {
      this.toastService.error(
        'This accommodation request cannot be edited because it has been approved. ' +
        'Approved requests can only be viewed, not modified.'
      );
      return;
    }

    this.router.navigate(['/accommodation/edit', this.requestId]);
  }

  onCancel(): void {
    this.confirmationService.confirmDestructive('Cancel', 'this accommodation request').subscribe(confirmed => {
      if (confirmed) {
        this.accommodationService.cancelRequest(this.requestId).subscribe({
          next: () => {
            this.toastService.success('Accommodation request cancelled successfully');
            this.router.navigate(['/accommodation']);
          },
          error: (err) => {
            this.toastService.error('Failed to cancel request: ' + (err.error?.message || err.message));
            console.error('Error cancelling request:', err);
          }
        });
      }
    });
  }

  onDelete(): void {
    this.confirmationService.confirmDelete('this accommodation request').subscribe(confirmed => {
      if (confirmed) {
        this.accommodationService.deleteRequest(this.requestId).subscribe({
          next: () => {
            this.toastService.success('Accommodation request deleted successfully');
            this.router.navigate(['/accommodation']);
          },
          error: (err) => {
            this.toastService.error('Failed to delete request: ' + (err.error?.message || err.message));
            console.error('Error deleting request:', err);
          }
        });
      }
    });
  }

  onPrint(): void {
    window.print();
  }

  // ========== HELPER METHODS ==========

  formatDate(dateValue: Date | string | null | undefined): string {
    if (!dateValue) return 'N/A';
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    if (isNaN(date.getTime())) return 'Invalid Date';
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  formatDateLong(dateValue: Date | string | null | undefined): string {
    if (!dateValue) return 'N/A';
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    if (isNaN(date.getTime())) return 'Invalid Date';
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }

  formatDateWithOrdinal(dateValue: Date | string | null | undefined): string {
    if (!dateValue) return 'N/A';
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    if (isNaN(date.getTime())) return 'Invalid Date';

    const day = date.getDate();
    const ordinal = this.getOrdinal(day);
    const monthYear = date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });

    return `${date.toLocaleDateString('en-US', { month: 'long' })} ${day}${ordinal}, ${date.getFullYear()}`;
  }

  getOrdinal(day: number): string {
    if (day > 3 && day < 21) return 'th';
    switch (day % 10) {
      case 1: return 'st';
      case 2: return 'nd';
      case 3: return 'rd';
      default: return 'th';
    }
  }

  getAssignmentDate(): Date | string | null {
    // Get assignment date from the first daily booking's created_at or use current date
    if (this.request?.dailyBookings && this.request.dailyBookings.length > 0) {
      return this.request.dailyBookings[0].createdAt || new Date();
    }
    return this.request?.lastUpdatedDate || null;
  }

  getAssignmentDetails(): string {
    if (!this.hasAssignment) return 'N/A';
    const staffHouse = this.request?.assignedStaffHouseName || 'N/A';
    const room = this.request?.assignedRoomName || 'N/A';
    const checkIn = this.formatDate(this.request?.requestedCheckInDate);
    const checkOut = this.formatDate(this.request?.requestedCheckOutDate);
    return `${staffHouse} - ${room} (${checkIn} - ${checkOut})`;
  }

  getRoomInfo(): { name: string; type: string; capacity: number; location: string; gender: string } | null {
    if (!this.request?.dailyBookings || this.request.dailyBookings.length === 0) {
      return null;
    }

    const firstBooking = this.request.dailyBookings[0];
    return {
      name: firstBooking.roomName || 'N/A',
      type: 'Single', // TODO: Get from room details
      capacity: 1,    // TODO: Get from room details
      location: this.request.location,
      gender: this.request.requestorGender
    };
  }

  getBookingNotes(): { date: string; note: string }[] {
    if (!this.request?.dailyBookings) return [];

    return this.request.dailyBookings
      .filter(b => b.notes && b.notes.trim().length > 0)
      .map(b => ({
        date: this.formatDate(b.date),
        note: b.notes!
      }));
  }

  getBookingStatus(booking: DailyBooking): { text: string; class: string } {
    const statusMap: Record<string, { text: string; class: string }> = {
      'Confirmed': { text: 'Confirmed', class: 'badge-success' },
      'Pending': { text: 'Pending', class: 'badge-warning' },
      'Checked-in': { text: 'Checked In', class: 'badge-info' },
      'Checked-out': { text: 'Checked Out', class: 'badge-secondary' },
      'Cancelled': { text: 'Cancelled', class: 'badge-danger' },
      'Blocked': { text: 'Blocked', class: 'badge-dark' }
    };

    return statusMap[booking.status] || { text: booking.status, class: 'badge-secondary' };
  }

  getReadyStatus(booking: DailyBooking): { text: string; class: string } {
    // Assuming "Ready" means the booking is confirmed and ready for check-in
    if (booking.status === 'Confirmed' || booking.status === 'Pending') {
      return { text: 'Ready', class: 'badge-ready' };
    }
    return { text: 'Not Ready', class: 'badge-secondary' };
  }

  formatDateTime(dateValue: Date | string | null | undefined): string {
    if (!dateValue) return 'N/A';
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    if (isNaN(date.getTime())) return 'Invalid Date';
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  }

  formatTime(timeStr: string | null | undefined): string {
    return formatTime12Hour(timeStr || undefined);
  }

  getCheckInStatus(booking: DailyBooking): { label: string; class: string } {
    if (booking.status === 'Checked-in' || booking.status === 'Checked-out') {
      return {
        label: 'Checked In',
        class: 'status-checked-in'
      };
    }
    return {
      label: 'Not Checked In',
      class: 'status-not-checked-in'
    };
  }

  getCheckOutStatus(booking: DailyBooking): { label: string; class: string } {
    if (booking.status === 'Checked-out') {
      return {
        label: 'Checked Out',
        class: 'status-checked-out'
      };
    }
    return {
      label: 'Not Checked Out',
      class: 'status-not-checked-out'
    };
  }

  getApprovalStepStatus(step: ApprovalStep): { icon: string; class: string } {
    if (step.status === 'Approved') {
      return { icon: 'bi-check-circle-fill', class: 'status-approved' };
    } else if (step.status === 'Rejected') {
      return { icon: 'bi-x-circle-fill', class: 'status-rejected' };
    } else {
      return { icon: 'bi-clock', class: 'status-pending' };
    }
  }

  // Status badge variant for template
  getStatusBadge(): { text: string; class: string } {
    if (!this.request) {
      return { text: 'Unknown', class: 'badge-secondary' };
    }

    return {
      text: this.request.status,
      class: getStatusBadgeClass(this.request.status)
    };
  }

  // Check if there's a TRF link to display
  hasTrfLink(): boolean {
    return !!(this.request?.trfId);
  }

  getTrfLink(): string {
    return `/trf/${this.request?.trfId}`;
  }

  // Get location icon based on location type
  getLocationIcon(): string {
    if (!this.request) return 'bi-geo-alt';

    const locationIcons: Record<string, string> = {
      'Ashgabat': 'bi-building',
      'Kiyanly': 'bi-house',
      'Turkmenbashy': 'bi-bank'
    };

    return locationIcons[this.request.location] || 'bi-geo-alt';
  }

  // Get room type icon
  getRoomTypeIcon(roomType?: string): string {
    if (!roomType) return 'bi-door-open';

    const roomTypeIcons: Record<string, string> = {
      'Single': 'bi-person',
      'Double': 'bi-people',
      'Suite': 'bi-house-door',
      'Tent': 'bi-triangle'
    };

    return roomTypeIcons[roomType] || 'bi-door-open';
  }

  // Group bookings by date for better display
  getBookingsByDate(): { date: string; bookings: DailyBooking[] }[] {
    if (!this.request?.dailyBookings) return [];

    const grouped = new Map<string, DailyBooking[]>();

    this.request.dailyBookings.forEach(booking => {
      const dateKey = this.formatDate(booking.date);
      if (!grouped.has(dateKey)) {
        grouped.set(dateKey, []);
      }
      grouped.get(dateKey)!.push(booking);
    });

    return Array.from(grouped.entries()).map(([date, bookings]) => ({
      date,
      bookings
    }));
  }

  // Calculate total nights from daily bookings
  getTotalNightsFromBookings(): number {
    if (!this.request?.dailyBookings) return 0;
    return this.request.dailyBookings.length;
  }

  // ==================== Workflow Methods ====================

  loadWorkflow(): void {
    this.workflowLoading = true;

    // Try to get workflow for this accommodation request
    this.workflowService.getInstances({
      entity_type: 'accommodation'
    }).subscribe({
      next: (response: any) => {
        // Check if response is an array or paginated object
        const instances = Array.isArray(response) ? response : (response.results || []);

        // Find workflow instance for this specific request
        const instance = instances.find((i: any) =>
          i.object_id === this.requestId ||
          i.entity_info?.id === this.requestId ||
          i.entity_id === this.requestId
        );

        if (instance && instance.id) {
          // Load full workflow details
          this.workflowService.getInstance(instance.id).subscribe({
            next: (workflow) => {
              this.workflow = workflow;
              this.updateCurrentStepExecution();
              this.workflowLoading = false;
            },
            error: (err) => {
              console.error('Error loading workflow details:', err);
              this.workflowLoading = false;
            }
          });
        } else {
          this.workflowLoading = false;
        }
      },
      error: (err) => {
        console.error('Error loading workflow:', err);
        this.workflowLoading = false;
      }
    });
  }

  updateCurrentStepExecution(): void {
    if (!this.workflow?.step_executions) {
      this.currentStepExecution = null;
      return;
    }

    this.currentStepExecution = this.workflow.step_executions.find(
      step => step.status === 'pending' &&
              step.workflow_step_detail?.step_order === this.workflow?.current_step_order &&
              step.can_action === true
    ) || null;
  }

  onWorkflowApproved(): void {
    this.toastService.success('Approval successful');
    this.loadRequestDetails();
    this.loadWorkflow();
  }

  onWorkflowRejected(): void {
    this.toastService.success('Request rejected');
    this.loadRequestDetails();
    this.loadWorkflow();
  }

  onWorkflowDelegated(): void {
    this.toastService.success('Successfully delegated');
    this.loadWorkflow();
  }

  getWorkflowStatus(): string {
    if (!this.workflow) return '';

    const status = this.workflow.status;
    const currentStep = this.workflow.current_step_order;
    const totalSteps = this.workflow.step_executions?.length || 0;

    if (status === 'approved') return 'Approved';
    if (status === 'rejected') return 'Rejected';
    if (status === 'cancelled') return 'Cancelled';
    if (status === 'in_progress') return `Pending Approval (Step ${currentStep} of ${totalSteps})`;
    if (status === 'pending') return 'Pending Approval';

    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  getWorkflowStatusClass(): string {
    if (!this.workflow) return 'badge-secondary';

    const status = this.workflow.status;
    if (status === 'approved') return 'badge-success';
    if (status === 'rejected') return 'badge-danger';
    if (status === 'cancelled') return 'badge-secondary';
    if (status === 'in_progress' || status === 'pending') return 'badge-warning';

    return 'badge-info';
  }
}
