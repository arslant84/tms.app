import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { AccommodationService } from '../../services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { AuthService } from '../../../../core/services/auth.service';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { WorkflowInstance } from '../../../../core/models/workflow.models';
import {
  AccommodationRequestBackend,
  AccommodationRequestDetails,
  DailyBooking,
  ApprovalStep,
  accommodationToFrontend,
  calculateNights,
  getStatusBadgeClass,
  isCancellable,
  isDeletable,
  formatTime12Hour,
} from '../../models/accommodation.model';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { DepartmentNamePipe } from '../../../../core/pipes/department-name.pipe';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';

@Component({
  selector: 'app-accommodation-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    WorkflowStatusComponent,
    DepartmentNamePipe,
    LoadingSpinnerComponent,
  ],
  templateUrl: './accommodation-detail.component.html',
  styleUrls: ['./accommodation-detail.component.scss'],
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

  // Room details cache
  roomDetails: { type: string; capacity: number } | null = null;

  // Workflow properties
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private accommodationService: AccommodationService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService,
    private authService: AuthService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService,
    private errorHandler: HttpErrorHandlerService
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
      next: data => {
        // Convert backend format to frontend format
        this.request = accommodationToFrontend(data as unknown as AccommodationRequestBackend);
        this.calculateDerivedValues();
        this.loading = false;
      },
      error: err => {
        this.error =
          'Failed to load accommodation request: ' +
          (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
      },
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
      this.request.dailyBookings && this.request.dailyBookings.length > 0
    );

    // Check if rejected
    this.isRejected = this.request.status === 'Rejected' && !!this.request.rejectionDetails;

    // Check if has admin notes
    this.hasAdminNotes = !!(this.request.notes && this.request.notes.trim().length > 0);

    // Fetch room details if we have bookings with a room ID
    this.loadRoomDetails();
  }

  loadRoomDetails(): void {
    if (!this.request?.dailyBookings || this.request.dailyBookings.length === 0) {
      return;
    }

    const firstBooking = this.request.dailyBookings[0];
    if (!firstBooking.roomId) {
      return;
    }

    // Fetch room details from the backend
    this.accommodationService.getRoomById(firstBooking.roomId).subscribe({
      next: room => {
        this.roomDetails = {
          type: room.room_type || 'Single',
          capacity: room.capacity || 1,
        };
      },
      error: () => {
        // Silently fail and use defaults if room details can't be fetched
        this.roomDetails = {
          type: 'Single',
          capacity: 1,
        };
      },
    });
  }

  /**
   * The signed-in user created this request. Owner-only actions
   * (Cancel/Delete) are gated on this so a viewer with read access - an
   * approver, an admin browsing, anyone else - can't act on someone
   * else's request. Accommodation requests have no owning User FK on the
   * backend (see docs/CODEBASE_REFACTOR_ROADMAP.md item 6) - ownership is
   * determined the same way the backend's own get_queryset does, by
   * matching staff_id or full name against the current user.
   */
  get isOwner(): boolean {
    if (!this.request) return false;
    const currentUser = this.authService.getCurrentUser();
    if (!currentUser) return false;
    return (
      (!!currentUser.staff_id && currentUser.staff_id === this.request.requestorId) ||
      currentUser.name === this.request.requestorName
    );
  }

  canCancel(): boolean {
    if (!this.isOwner) return false;
    return this.request ? isCancellable(this.request.status) : false;
  }

  canDelete(): boolean {
    if (!this.isOwner) return false;
    return this.request ? isDeletable(this.request.status) : false;
  }

  getStatusClass(): string {
    return this.request ? getStatusBadgeClass(this.request.status) : 'badge-secondary';
  }

  private navigateBack(): void {
    // Accommodation requests are created and reached exclusively via their
    // linked TSR now, so "back" returns to that TSR rather than a standalone
    // accommodation list (which no longer exists).
    if (this.request?.trfId) {
      this.router.navigate(['/trf', this.request.trfId]);
    } else {
      this.router.navigate(['/dashboard']);
    }
  }

  goBack(): void {
    this.navigateBack();
  }

  onCancel(): void {
    this.confirmationService
      .confirmCancel(
        'Are you sure you want to cancel this accommodation request? This action cannot be undone.'
      )
      .subscribe(confirmed => {
        if (confirmed) {
          this.accommodationService.cancelRequest(this.requestId).subscribe({
            next: () => {
              this.toastService.success('Accommodation request cancelled successfully');
              this.navigateBack();
            },
            error: err => {
              this.toastService.error(
                this.errorHandler.getErrorMessage(err, 'Failed to cancel request')
              );
            },
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
            this.navigateBack();
          },
          error: err => {
            this.toastService.error(
              this.errorHandler.getErrorMessage(err, 'Failed to delete request')
            );
          },
        });
      }
    });
  }

  onExportPdf(): void {
    if (!this.requestId) return;

    this.accommodationService.exportToPdf(this.requestId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `Accommodation-${this.request?.requestNumber || this.requestId}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('PDF exported successfully');
      },
      error: (err: HttpErrorResponse) => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to export PDF'));
      },
    });
  }

  // ========== HELPER METHODS ==========

  formatDateLong(dateValue: Date | string | null | undefined): string {
    if (!dateValue) return 'N/A';
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    if (Number.isNaN(date.getTime())) return 'Invalid Date';
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }

  formatDateWithOrdinal(dateValue: Date | string | null | undefined): string {
    if (!dateValue) return 'N/A';
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    if (Number.isNaN(date.getTime())) return 'Invalid Date';

    const day = date.getDate();
    const ordinal = this.getOrdinal(day);

    return `${date.toLocaleDateString('en-US', { month: 'long' })} ${day}${ordinal}, ${date.getFullYear()}`;
  }

  getOrdinal(day: number): string {
    if (day > 3 && day < 21) return 'th';
    switch (day % 10) {
      case 1:
        return 'st';
      case 2:
        return 'nd';
      case 3:
        return 'rd';
      default:
        return 'th';
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
    // Use actual booking dates instead of requested dates
    const actualDates = this.getActualBookingDates();
    const checkIn = this.dateUtils.formatDate(actualDates.checkIn);
    const checkOut = this.dateUtils.formatDate(actualDates.checkOut);
    return `${staffHouse} - ${room} (${checkIn} - ${checkOut})`;
  }

  /**
   * Get actual booking dates from daily bookings (not user requested dates)
   * Each daily booking represents a night stay, so:
   * - Check-in = first booking date
   * - Check-out = day AFTER the last booking date
   */
  getActualBookingDates(): { checkIn: Date | string | null; checkOut: Date | string | null } {
    if (!this.request?.dailyBookings || this.request.dailyBookings.length === 0) {
      // Fall back to requested dates if no bookings exist yet
      return {
        checkIn: this.request?.requestedCheckInDate || null,
        checkOut: this.request?.requestedCheckOutDate || null,
      };
    }

    // Sort bookings by date to get first and last
    const sortedBookings = [...this.request.dailyBookings].sort((a, b) => {
      const dateA = new Date(a.date).getTime();
      const dateB = new Date(b.date).getTime();
      return dateA - dateB;
    });

    // Check-out is the day AFTER the last booking (each booking = 1 night stay)
    const lastBookingDate = new Date(sortedBookings[sortedBookings.length - 1].date);
    const checkOutDate = new Date(lastBookingDate);
    checkOutDate.setDate(checkOutDate.getDate() + 1);

    return {
      checkIn: sortedBookings[0].date,
      checkOut: checkOutDate,
    };
  }

  getRoomInfo(): {
    name: string;
    type: string;
    capacity: number;
    location: string;
    gender: string;
  } | null {
    if (!this.request?.dailyBookings || this.request.dailyBookings.length === 0) {
      return null;
    }

    const firstBooking = this.request.dailyBookings[0];
    return {
      name: firstBooking.roomName || 'N/A',
      type: this.roomDetails?.type || 'Single',
      capacity: this.roomDetails?.capacity || 1,
      location: this.request.location,
      gender: this.request.requestorGender,
    };
  }

  getBookingNotes(): { date: string; note: string }[] {
    if (!this.request?.dailyBookings) return [];

    return this.request.dailyBookings
      .filter(b => b.notes && b.notes.trim().length > 0)
      .map(b => ({
        date: this.dateUtils.formatDate(b.date),
        note: b.notes!,
      }));
  }

  getBookingStatus(booking: DailyBooking): { text: string; class: string } {
    const statusMap: Record<string, { text: string; class: string }> = {
      Confirmed: { text: 'Confirmed', class: 'badge-success' },
      Pending: { text: 'Pending', class: 'badge-warning' },
      'Checked-in': { text: 'Checked In', class: 'badge-info' },
      'Checked-out': { text: 'Checked Out', class: 'badge-secondary' },
      Cancelled: { text: 'Cancelled', class: 'badge-danger' },
      Blocked: { text: 'Blocked', class: 'badge-dark' },
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

  formatTime(timeStr: string | null | undefined): string {
    return formatTime12Hour(timeStr || undefined);
  }

  getCheckInStatus(booking: DailyBooking): { label: string; class: string } {
    if (booking.status === 'Checked-in' || booking.status === 'Checked-out') {
      return {
        label: 'Checked In',
        class: 'status-checked-in',
      };
    }
    return {
      label: 'Not Checked In',
      class: 'status-not-checked-in',
    };
  }

  getCheckOutStatus(booking: DailyBooking): { label: string; class: string } {
    if (booking.status === 'Checked-out') {
      return {
        label: 'Checked Out',
        class: 'status-checked-out',
      };
    }
    return {
      label: 'Not Checked Out',
      class: 'status-not-checked-out',
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
      class: getStatusBadgeClass(this.request.status),
    };
  }

  // Check if there's a TRF link to display
  hasTrfLink(): boolean {
    return !!this.request?.trfId;
  }

  getTrfLink(): string {
    return `/trf/${this.request?.trfId}`;
  }

  // Get location icon based on location type
  getLocationIcon(): string {
    if (!this.request) return 'bi-geo-alt';

    const locationIcons: Record<string, string> = {
      Ashgabat: 'bi-building',
      Kiyanly: 'bi-house',
      Turkmenbashy: 'bi-bank',
    };

    return locationIcons[this.request.location] || 'bi-geo-alt';
  }

  // Get room type icon
  getRoomTypeIcon(roomType?: string): string {
    if (!roomType) return 'bi-door-open';

    const roomTypeIcons: Record<string, string> = {
      Hotel: 'bi-building',
      'Staff House': 'bi-house-door',
      'PKC Camp': 'bi-tree',
    };

    return roomTypeIcons[roomType] || 'bi-door-open';
  }

  // Group bookings by date for better display
  getBookingsByDate(): { date: string; bookings: DailyBooking[] }[] {
    if (!this.request?.dailyBookings) return [];

    const grouped = new Map<string, DailyBooking[]>();

    this.request.dailyBookings.forEach(booking => {
      const dateKey = this.dateUtils.formatDate(booking.date);
      if (!grouped.has(dateKey)) {
        grouped.set(dateKey, []);
      }
      grouped.get(dateKey)!.push(booking);
    });

    return Array.from(grouped.entries()).map(([date, bookings]) => ({
      date,
      bookings,
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
    this.workflowService
      .getInstances({
        entity_type: 'accommodation',
        object_id: this.requestId,
      })
      .subscribe({
        next: instances => {
          // Find workflow instance for this specific request
          const instance = instances.find(
            i => i.object_id === this.requestId || i.entity_info?.id === this.requestId
          );

          if (instance && instance.id) {
            // Load full workflow details
            this.workflowService.getInstance(instance.id).subscribe({
              next: workflow => {
                this.workflow = workflow;
                this.workflowLoading = false;
              },
              error: () => {
                this.workflowLoading = false;
              },
            });
          } else {
            this.workflowLoading = false;
          }
        },
        error: () => {
          this.workflowLoading = false;
        },
      });
  }

  getWorkflowStatus(): string {
    if (!this.workflow) return '';

    const status = this.workflow.status;
    const currentStep = this.workflow.current_step_order;
    // The template's real, configured step count - not step_executions.length,
    // which only counts steps reached so far (see trf-detail.component.ts's
    // getWorkflowStatus for the full explanation).
    const totalSteps =
      this.workflow.workflow_template_detail?.step_count ||
      this.workflow.step_executions?.length ||
      0;

    if (status === 'approved') return 'Approved';
    if (status === 'rejected') return 'Rejected';
    if (status === 'cancelled') return 'Cancelled';
    if (status === 'in_progress') return `Pending Approval (Step ${currentStep} of ${totalSteps})`;
    if (status === 'pending') return 'Pending Approval';

    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  getWorkflowStatusClass(): string {
    return this.statusUtils.getWorkflowStatusClass(this.workflow?.status);
  }
}
