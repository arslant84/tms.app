import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import type {
  AccommodationRoom,
  AccommodationStaffHouse,
} from '../../../accommodation/services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { DepartmentNamePipe } from '../../../../core/pipes/department-name.pipe';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';
import {
  calculateDaysInMonth,
  getVisibleDays as mapperGetVisibleDays,
  canSlidePrevious as mapperCanSlidePrevious,
  canSlideNext as mapperCanSlideNext,
  computeSlidePreviousOffset,
  computeSlideNextOffset,
  formatDateForInput as mapperFormatDateForInput,
  formatDateForDisplay as mapperFormatDateForDisplay,
  formatDateForAPI as mapperFormatDateForAPI,
  formatDateForComparison as mapperFormatDateForComparison,
  calculateDays as mapperCalculateDays,
  calculateDuration as mapperCalculateDuration,
  getDayName as mapperGetDayName,
  isWeekend as mapperIsWeekend,
  getLocationBadgeClass as mapperGetLocationBadgeClass,
  getDateBookingInfo as mapperGetDateBookingInfo,
  isRoomAvailableForDates,
  validateAssignmentDates,
  type BookedAccommodation,
  type BookingData,
  type PendingAccommodation,
} from './accommodation-processing.mapper';
import { AccommodationProcessingService } from './accommodation-processing.service';

@Component({
  selector: 'app-accommodation-processing',
  standalone: true,
  imports: [CommonModule, FormsModule, DepartmentNamePipe, LoadingSpinnerComponent],
  templateUrl: './accommodation-processing.component.html',
  styleUrl: './accommodation-processing.component.scss',
})
export class AccommodationProcessingComponent implements OnInit {
  activeTab: 'pending' | 'booked' = 'pending';

  // Pending Accommodations
  pendingAccommodations: PendingAccommodation[] = [];
  isLoadingPending = false;
  errorPending: string | null = null;

  // Booked Accommodations
  bookedAccommodations: BookedAccommodation[] = [];
  isLoadingBooked = false;

  // Selected Request for processing
  selectedRequest: PendingAccommodation | null = null;
  isProcessing = false;

  // Available staff houses and rooms
  availableStaffHouses: AccommodationStaffHouse[] = [];
  private allStaffHouses: AccommodationStaffHouse[] = [];
  availableRooms: AccommodationRoom[] = [];
  allRooms: AccommodationRoom[] = [];

  // Booking form fields
  selectedStaffHouse: number | null = null;
  selectedRoom: number | null = null;
  bookingNotes = '';
  checkInDate: string = '';
  checkOutDate: string = '';

  // TSR date constraints (when accommodation is linked to TSR)
  hasTsrReference = false;
  tsrMinDate: string = ''; // TSR departure date
  tsrMaxDate: string = ''; // TSR return date
  tsrDepartureDate: string = '';
  tsrReturnDate: string = '';

  // Calendar state
  currentMonth: Date = new Date();
  selectedLocation: string = 'Turkmenbashy';
  bookings: BookingData[] = [];
  isLoadingBookings = false;

  // Calendar slider state
  currentDateOffset = 0;
  daysToShow = 16; // Show 16 days at a time
  totalDays = 0;
  private cachedDaysInMonth: Date[] = [];

  // Date range for assignment (deprecated - using checkInDate/checkOutDate instead)
  dateRange: { from: Date | null; to: Date | null } = { from: null, to: null };

  constructor(
    private accommodationProcessing: AccommodationProcessingService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private router: Router,
    public dateUtils: DateUtilsService,
    private statusUtils: StatusUtilsService,
    private errorHandler: HttpErrorHandlerService
  ) {}

  ngOnInit(): void {
    this.calculateTotalDays();
    this.loadAccommodationRequests();
    this.fetchStaffHouses();
    this.fetchBookings();
  }

  loadAccommodationRequests(): void {
    this.isLoadingPending = true;
    this.isLoadingBooked = true;
    this.errorPending = null;

    this.accommodationProcessing.loadRequests().subscribe({
      next: ({ pending, booked }) => {
        this.pendingAccommodations = pending;
        this.bookedAccommodations = booked;
        this.isLoadingPending = false;
        this.isLoadingBooked = false;
      },
      error: err => {
        console.error('Failed to fetch accommodation requests:', err);
        this.errorPending = 'Failed to load pending accommodations. Please try again.';
        this.pendingAccommodations = [];
        this.bookedAccommodations = [];
        this.isLoadingPending = false;
        this.isLoadingBooked = false;
      },
    });
  }

  /**
   * Fetch all staff houses
   */
  fetchStaffHouses(): void {
    this.accommodationProcessing.fetchStaffHouses().subscribe({
      next: staffHouses => {
        this.allStaffHouses = staffHouses;
        this.availableStaffHouses = staffHouses;
        this.fetchAllRooms();
      },
      error: err => {
        console.error('Failed to fetch staff houses:', err);
        this.toastService.error('Failed to load staff houses');
      },
    });
  }

  /**
   * Fetch all rooms for calendar display
   */
  fetchAllRooms(): void {
    this.accommodationProcessing.fetchRooms().subscribe({
      next: rooms => {
        this.allRooms = rooms;
      },
      error: err => {
        console.error('Failed to fetch rooms:', err);
      },
    });
  }

  /**
   * Fetch bookings for current month
   */
  fetchBookings(): void {
    this.isLoadingBookings = true;
    // For now, fetch all bookings - in production you'd filter by month
    this.accommodationProcessing.fetchBookings().subscribe({
      next: bookings => {
        this.bookings = bookings;
        this.isLoadingBookings = false;
      },
      error: err => {
        console.error('Failed to fetch bookings:', err);
        this.isLoadingBookings = false;
      },
    });
  }

  /**
   * Fetch rooms for selected staff house and location
   */
  onStaffHouseChange(): void {
    if (!this.selectedStaffHouse) {
      this.availableRooms = [];
      return;
    }

    this.accommodationProcessing.fetchRooms(this.selectedStaffHouse).subscribe({
      next: rooms => {
        // Filter only available rooms
        this.availableRooms = rooms.filter(room => room.status === 'Available');
      },
      error: err => {
        console.error('Failed to fetch rooms:', err);
        this.toastService.error('Failed to load rooms');
        this.availableRooms = [];
      },
    });
  }

  /**
   * Select accommodation request for processing
   */
  selectRequest(request: PendingAccommodation): void {
    // Use setTimeout to avoid ExpressionChangedAfterItHasBeenCheckedError
    setTimeout(() => {
      this.selectedRequest = request;
      this.resetFormFields();

      // Check if accommodation has TSR reference
      this.hasTsrReference = !!request.trfId;

      if (this.hasTsrReference && request.tsrDepartureDate && request.tsrReturnDate) {
        this.applyTsrDateConstraints(request, request.tsrDepartureDate, request.tsrReturnDate);
      } else {
        this.applyFlexibleDates(request);
      }

      // Filter staff houses by location if specified
      if (request.location && request.location !== 'N/A') {
        this.selectedLocation = request.location;
        this.availableStaffHouses = this.allStaffHouses.filter(
          h => h.location === request.location
        );
      } else {
        this.availableStaffHouses = this.allStaffHouses;
      }
    }, 0);
  }

  /**
   * TSR-linked branch of selectRequest: set date constraints from the TSR's
   * travel dates and auto-populate check-in/out from the request (falling
   * back to the TSR dates themselves). Split out of selectRequest to keep
   * its cyclomatic complexity down - no logic changed.
   */
  private applyTsrDateConstraints(
    request: PendingAccommodation,
    tsrDepartureDateStr: string,
    tsrReturnDateStr: string
  ): void {
    const tsrDeparture = new Date(tsrDepartureDateStr);
    const tsrReturn = new Date(tsrReturnDateStr);

    if (!Number.isNaN(tsrDeparture.getTime()) && !Number.isNaN(tsrReturn.getTime())) {
      this.tsrMinDate = this.formatDateForInput(tsrDeparture);
      this.tsrMaxDate = this.formatDateForInput(tsrReturn);
      this.tsrDepartureDate = this.formatDateForInput(tsrDeparture);
      this.tsrReturnDate = this.formatDateForInput(tsrReturn);

      // Auto-populate accommodation dates from TSR dates
      // Use requested dates if available, otherwise use TSR dates
      if (request.checkInDate && request.checkInDate !== 'N/A') {
        const requestedCheckIn = new Date(request.checkInDate);
        if (!Number.isNaN(requestedCheckIn.getTime())) {
          this.checkInDate = this.formatDateForInput(requestedCheckIn);
        } else {
          this.checkInDate = this.tsrMinDate;
        }
      } else {
        this.checkInDate = this.tsrMinDate;
      }

      if (request.checkOutDate && request.checkOutDate !== 'N/A') {
        const requestedCheckOut = new Date(request.checkOutDate);
        if (!Number.isNaN(requestedCheckOut.getTime())) {
          this.checkOutDate = this.formatDateForInput(requestedCheckOut);
        } else {
          this.checkOutDate = this.tsrMaxDate;
        }
      } else {
        this.checkOutDate = this.tsrMaxDate;
      }

      // Update dateRange
      this.dateRange = {
        from: new Date(this.checkInDate),
        to: new Date(this.checkOutDate),
      };

      // Show info message
      this.toastService.info(
        `Dates auto-populated from TSR. You can revise within travel dates: ${this.formatDateForDisplay(tsrDeparture)} to ${this.formatDateForDisplay(tsrReturn)}`
      );
    }
  }

  /**
   * No-TSR branch of selectRequest: dates are flexible, auto-populated
   * from the request if valid. Split out of selectRequest to keep its
   * cyclomatic complexity down - no logic changed.
   */
  private applyFlexibleDates(request: PendingAccommodation): void {
    this.tsrMinDate = '';
    this.tsrMaxDate = '';
    this.tsrDepartureDate = '';
    this.tsrReturnDate = '';

    // Auto-populate date inputs if provided
    if (
      request.checkInDate &&
      request.checkOutDate &&
      request.checkInDate !== 'N/A' &&
      request.checkOutDate !== 'N/A'
    ) {
      const fromDate = new Date(request.checkInDate);
      const toDate = new Date(request.checkOutDate);

      if (!Number.isNaN(fromDate.getTime()) && !Number.isNaN(toDate.getTime())) {
        this.checkInDate = this.formatDateForInput(fromDate);
        this.checkOutDate = this.formatDateForInput(toDate);
        this.dateRange = { from: fromDate, to: toDate };
      } else {
        this.checkInDate = '';
        this.checkOutDate = '';
        this.dateRange = { from: null, to: null };
      }
    } else {
      this.checkInDate = '';
      this.checkOutDate = '';
      this.dateRange = { from: null, to: null };
    }
  }

  /**
   * Handle date change
   */
  onDateChange(): void {
    // Update dateRange object for backward compatibility
    if (this.checkInDate && this.checkOutDate) {
      this.dateRange = {
        from: new Date(this.checkInDate),
        to: new Date(this.checkOutDate),
      };
    }
  }

  /**
   * Calculate number of nights
   */
  calculateDays(): number {
    return mapperCalculateDays(this.checkInDate, this.checkOutDate);
  }

  /**
   * Format date for input type="date" (YYYY-MM-DD)
   */
  formatDateForInput(date: Date): string {
    return mapperFormatDateForInput(date);
  }

  /**
   * Format date for display (readable format)
   */
  formatDateForDisplay(date: Date | string): string {
    return mapperFormatDateForDisplay(date);
  }

  /**
   * Reset form fields
   */
  resetFormFields(): void {
    this.selectedStaffHouse = null;
    this.selectedRoom = null;
    this.bookingNotes = '';
    this.checkInDate = '';
    this.checkOutDate = '';
    this.availableRooms = [];
  }

  /**
   * Check if room is available for the selected date range
   */
  checkRoomAvailability(roomId: number): boolean {
    return isRoomAvailableForDates(roomId, this.dateRange.from, this.dateRange.to, this.bookings);
  }

  /**
   * Assign room to accommodation request
   */
  assignRoom(): void {
    // Validate inputs
    if (!this.selectedRequest) {
      this.toastService.error('Please select a request');
      return;
    }

    if (!this.selectedRoom) {
      this.toastService.error('Please select a room');
      return;
    }

    if (!this.checkInDate || !this.checkOutDate) {
      this.toastService.error('Please select check-in and check-out dates');
      return;
    }

    // Validate date range
    const checkIn = new Date(this.checkInDate);
    const checkOut = new Date(this.checkOutDate);

    const dateError = validateAssignmentDates(
      checkIn,
      checkOut,
      this.hasTsrReference,
      this.tsrMinDate,
      this.tsrMaxDate
    );
    if (dateError) {
      this.toastService.error(dateError);
      return;
    }

    // Check availability
    if (!this.checkRoomAvailability(this.selectedRoom)) {
      this.toastService.error('Selected room is not available for the chosen dates');
      return;
    }

    this.isProcessing = true;

    // Get staff house and room names
    const staffHouse = this.availableStaffHouses.find(h => h.id === this.selectedStaffHouse);
    const room = this.availableRooms.find(r => r.id === this.selectedRoom);
    const selectedRoomId = this.selectedRoom;
    const requestToAssign = this.selectedRequest;

    const assignmentData = {
      staff_house: this.selectedStaffHouse!,
      room: selectedRoomId,
      start_date: this.checkInDate,
      end_date: this.checkOutDate,
      notes: this.bookingNotes,
      assigned_room_info: `${staffHouse?.name} - ${room?.name} (${this.formatDateForDisplay(checkIn)} - ${this.formatDateForDisplay(checkOut)})`,
    };

    // Call the backend assign endpoint which creates daily booking records
    this.accommodationProcessing.assignRoom(requestToAssign.id, assignmentData).subscribe({
      next: response => {
        this.toastService.success(
          response.message || `Room assigned successfully for ${requestToAssign.requestorName}`
        );
        this.loadAccommodationRequests();
        this.fetchBookings();
        this.selectedRequest = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: err => {
        console.error('Failed to assign accommodation:', err);
        this.toastService.error(
          this.errorHandler.getErrorMessage(err, 'Failed to assign accommodation')
        );
        this.isProcessing = false;
      },
    });
  }

  /**
   * Reject accommodation request (No rooms available)
   */
  noRoomsAvailable(): void {
    if (!this.selectedRequest) {
      this.toastService.error('No request selected');
      return;
    }

    this.confirmationService
      .confirm({
        title: 'Reject Request',
        message: `Reject accommodation request ${this.selectedRequest.request_number} due to no available rooms?`,
        confirmText: 'Reject',
        type: 'danger',
      })
      .subscribe(confirmed => {
        if (!confirmed) return;
        this.executeNoRoomsAvailable();
      });
  }

  private executeNoRoomsAvailable(): void {
    if (!this.selectedRequest) return;
    this.isProcessing = true;
    const requestToReject = this.selectedRequest;

    this.accommodationProcessing.rejectNoRoomsAvailable(requestToReject.id).subscribe({
      next: () => {
        this.toastService.success(
          `Request ${requestToReject.request_number} rejected due to no available rooms`
        );
        this.loadAccommodationRequests();
        this.selectedRequest = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: err => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to reject request'));
        this.isProcessing = false;
      },
    });
  }

  /**
   * Cancel booking
   */
  cancelBooking(booking: BookedAccommodation): void {
    this.confirmationService
      .confirm({
        title: 'Cancel Booking',
        message: `Cancel room booking for ${booking.requestorName}?`,
        confirmText: 'Cancel Booking',
        type: 'warning',
      })
      .subscribe(confirmed => {
        if (!confirmed) return;
        this.executeCancelBooking(booking);
      });
  }

  private executeCancelBooking(booking: BookedAccommodation): void {
    this.isProcessing = true;

    // Three phases, matching accommodation-processing.service.ts's
    // fetchRelatedBookings/deleteBookings/restoreApprovedStatus split -
    // each phase keeps its own original error handling: a failure
    // fetching bookings shows "...for cancellation"; a failure deleting
    // them shows the generic "Failed to cancel booking"; a failure
    // restoring the request's status shows no toast at all (a
    // pre-existing quirk, preserved rather than "fixed" here).
    this.accommodationProcessing.fetchRelatedBookings(booking).then(
      relatedBookings => {
        this.accommodationProcessing
          .deleteBookings(relatedBookings)
          .then(() =>
            this.accommodationProcessing.restoreApprovedStatus(booking).then(
              () => {
                this.toastService.success(
                  `Booking for ${booking.requestorName} cancelled successfully`
                );
                this.loadAccommodationRequests();
                this.fetchBookings();
                this.isProcessing = false;
              },
              () => {
                this.isProcessing = false;
              }
            )
          )
          .catch(err => {
            console.error('Failed to delete bookings:', err);
            this.toastService.error('Failed to cancel booking');
            this.isProcessing = false;
          });
      },
      () => {
        this.toastService.error('Failed to fetch bookings for cancellation');
        this.isProcessing = false;
      }
    );
  }

  /**
   * Calculate duration between two dates
   */
  calculateDuration(checkIn: string, checkOut: string): number {
    return mapperCalculateDuration(checkIn, checkOut);
  }

  /**
   * Switch tab
   */
  switchTab(tab: 'pending' | 'booked'): void {
    this.activeTab = tab;
  }

  /**
   * View request details
   */
  viewRequest(requestId: number): void {
    this.router.navigate(['/accommodation', requestId]);
  }

  /**
   * Navigate back to overview
   */
  goToOverview(): void {
    this.router.navigate(['/admin/accommodation']);
  }

  /**
   * Calendar Navigation
   */
  previousMonth(): void {
    const prevMonth = new Date(this.currentMonth);
    prevMonth.setMonth(prevMonth.getMonth() - 1);
    this.currentMonth = prevMonth;
    this.currentDateOffset = 0; // Reset slider
    this.calculateTotalDays(); // Recalculate total days for new month
    this.fetchBookings();
  }

  nextMonth(): void {
    const nextMonth = new Date(this.currentMonth);
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    this.currentMonth = nextMonth;
    this.currentDateOffset = 0; // Reset slider
    this.calculateTotalDays(); // Recalculate total days for new month
    this.fetchBookings();
  }

  /**
   * Get days in current month for calendar
   * Returns cached array to prevent state changes during rendering
   */
  getDaysInMonth(): Date[] {
    return this.cachedDaysInMonth;
  }

  /**
   * Calculate total days in current month and cache the days array
   */
  private calculateTotalDays(): void {
    const year = this.currentMonth.getFullYear();
    const month = this.currentMonth.getMonth();
    this.cachedDaysInMonth = calculateDaysInMonth(year, month);
    this.totalDays = this.cachedDaysInMonth.length;
  }

  /**
   * Get visible days for the current slider position
   */
  getVisibleDays(): Date[] {
    return mapperGetVisibleDays(this.cachedDaysInMonth, this.currentDateOffset, this.daysToShow);
  }

  /**
   * Navigate to previous set of days
   */
  slidePrevious(): void {
    if (this.canSlidePrevious()) {
      this.currentDateOffset = computeSlidePreviousOffset(this.currentDateOffset, this.daysToShow);
    }
  }

  /**
   * Navigate to next set of days
   */
  slideNext(): void {
    if (this.canSlideNext()) {
      this.currentDateOffset = computeSlideNextOffset(
        this.currentDateOffset,
        this.daysToShow,
        this.totalDays
      );
    }
  }

  /**
   * Check if can slide to previous days
   */
  canSlidePrevious(): boolean {
    return mapperCanSlidePrevious(this.currentDateOffset);
  }

  /**
   * Check if can slide to next days
   */
  canSlideNext(): boolean {
    return mapperCanSlideNext(this.currentDateOffset, this.daysToShow, this.totalDays);
  }

  /**
   * Get rooms filtered by location
   */
  getRoomsByLocation(): AccommodationRoom[] {
    return this.allRooms.filter(room => {
      const staffHouse = this.availableStaffHouses.find(h => h.id === room.staff_house);
      return staffHouse?.location === this.selectedLocation;
    });
  }

  /**
   * Get booking info for a specific date and room
   */
  getDateBookingInfo(
    date: Date,
    roomId: number
  ): { isOccupied: boolean; status: string | null; guestName: string | null } {
    return mapperGetDateBookingInfo(date, roomId, this.bookings);
  }

  /**
   * Get staff house name by ID
   */
  getStaffHouseName(staffHouseId: number): string {
    const staffHouse = this.availableStaffHouses.find(h => h.id === staffHouseId);
    return staffHouse?.name || 'Unknown';
  }

  /**
   * Format date for display
   */
  formatDateForAPI(date: Date): string {
    return mapperFormatDateForAPI(date);
  }

  formatDateForComparison(date: Date): string {
    return mapperFormatDateForComparison(date);
  }

  /**
   * Get status badge class - delegates to StatusUtilsService so the same
   * status renders the same color everywhere in the app.
   */
  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Get location badge class
   */
  getLocationBadgeClass(location: string): string {
    return mapperGetLocationBadgeClass(location);
  }

  /**
   * Retry loading pending accommodations
   */
  retryPending(): void {
    this.loadAccommodationRequests();
  }

  /**
   * Get day of week name
   */
  getDayName(date: Date): string {
    return mapperGetDayName(date);
  }

  /**
   * Check if date is weekend
   */
  isWeekend(date: Date): boolean {
    return mapperIsWeekend(date);
  }
}
