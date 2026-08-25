import { Component, OnInit } from '@angular/core';
import { lastValueFrom } from 'rxjs';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  AccommodationService,
  AccommodationRoom,
  AccommodationStaffHouse,
  AccommodationBooking,
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
  firstTruthy,
} from './accommodation-processing.mapper';

interface PendingAccommodation {
  id: number;
  request_number: string;
  requestorName: string;
  department: string;
  staffId: string;
  location: string;
  checkInDate: string;
  checkOutDate: string;
  roomType: string;
  status: string;
  requestedDate: string;
  duration: number;
  gender?: string;
  trfId?: number;
  tsrDepartureDate?: string;
  tsrReturnDate?: string;
}

interface BookedAccommodation {
  id: number;
  requestNumber: string;
  requestorName: string;
  staffId: string;
  staffHouseName: string;
  roomName: string;
  location: string;
  checkInDate: string;
  checkOutDate: string;
  status: string;
  notes?: string;
  bookingCount?: number;
}

interface BookingData {
  id: number;
  staff_house_id: number;
  room_id: number;
  date: string;
  status: string;
  guest_name?: string;
  gender?: string;
  trf_id?: number;
  notes?: string;
}

/** Raw accommodation request shape as returned by
 * AccommodationService.getAllRequests() - the same request may carry its
 * check-in/out dates and room details on `additional_data.accommodations[0]`,
 * directly on `additional_data`, or on the request itself, depending on
 * which flow created it. */
interface RawAccommodationAccom {
  location?: string;
  check_in_date?: string;
  checkInDate?: string;
  check_out_date?: string;
  checkOutDate?: string;
  room_type?: string;
  roomType?: string;
  gender?: string;
}

interface RawAccommodationRequest {
  id: number;
  status?: string;
  request_number?: string;
  requestor_name?: string;
  department?: string;
  staff_id?: string;
  submitted_at?: string;
  created_at?: string;
  trf?: number | null;
  tsr_departure_date?: string;
  tsr_return_date?: string;
  additional_comments?: string;
  check_in_date?: string;
  requested_check_in_date?: string;
  check_out_date?: string;
  requested_check_out_date?: string;
  additional_data?: RawAccommodationAccom & {
    accommodations?: RawAccommodationAccom[];
    requested_check_in_date?: string;
    requestedCheckInDate?: string;
    requested_check_out_date?: string;
    requestedCheckOutDate?: string;
  };
}

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
    private accommodationService: AccommodationService,
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

  private extractDates(req: RawAccommodationRequest): {
    checkInDate: string;
    checkOutDate: string;
  } {
    const additionalData = req.additional_data || {};
    const firstAccom = (additionalData.accommodations || [])[0] || {};
    const checkInDate = firstTruthy(
      'N/A',
      firstAccom.check_in_date,
      firstAccom.checkInDate,
      additionalData.check_in_date,
      additionalData.checkInDate,
      additionalData.requested_check_in_date,
      additionalData.requestedCheckInDate,
      req.check_in_date,
      req.requested_check_in_date
    );
    const checkOutDate = firstTruthy(
      'N/A',
      firstAccom.check_out_date,
      firstAccom.checkOutDate,
      additionalData.check_out_date,
      additionalData.checkOutDate,
      additionalData.requested_check_out_date,
      additionalData.requestedCheckOutDate,
      req.check_out_date,
      req.requested_check_out_date
    );
    return { checkInDate, checkOutDate };
  }

  loadAccommodationRequests(): void {
    this.isLoadingPending = true;
    this.isLoadingBooked = true;
    this.errorPending = null;

    this.accommodationService.getAllRequests({ adminView: true, page_size: 1000 }).subscribe({
      next: (response: RawAccommodationRequest[] | { results: RawAccommodationRequest[] }) => {
        const requests: RawAccommodationRequest[] = Array.isArray(response)
          ? response
          : response.results;

        this.pendingAccommodations = requests
          .filter(req => req.status === 'Approved')
          .map(req => {
            const additionalData = req.additional_data || {};
            const firstAccom = (additionalData.accommodations || [])[0] || {};
            const { checkInDate, checkOutDate } = this.extractDates(req);
            return {
              id: req.id,
              request_number: req.request_number || `ACC-${req.id}`,
              requestorName: firstTruthy('N/A', req.requestor_name),
              department: firstTruthy('N/A', req.department),
              staffId: firstTruthy('N/A', req.staff_id),
              location: firstTruthy('N/A', firstAccom.location, additionalData.location),
              checkInDate,
              checkOutDate,
              roomType: firstTruthy('Any', firstAccom.room_type, firstAccom.roomType),
              status: req.status ?? '',
              requestedDate: firstTruthy('', req.submitted_at, req.created_at),
              duration: this.calculateDuration(checkInDate, checkOutDate),
              gender: firstTruthy('N/A', firstAccom.gender, additionalData.gender),
              trfId: req.trf || undefined,
              tsrDepartureDate: req.tsr_departure_date || '',
              tsrReturnDate: req.tsr_return_date || '',
            };
          });

        this.bookedAccommodations = requests
          .filter(req => req.status === 'Accommodation Assigned')
          .map(req => {
            const additionalData = req.additional_data || {};
            const firstAccom = (additionalData.accommodations || [])[0] || {};
            const { checkInDate, checkOutDate } = this.extractDates(req);
            return {
              id: req.id,
              requestNumber: req.request_number || `ACC-${req.id}`,
              requestorName: firstTruthy('N/A', req.requestor_name),
              staffId: firstTruthy('N/A', req.staff_id),
              staffHouseName: 'Not assigned',
              roomName: 'Not assigned',
              location: firstTruthy('N/A', firstAccom.location, additionalData.location),
              checkInDate,
              checkOutDate,
              status: firstTruthy('Confirmed', req.status),
              notes: req.additional_comments,
            };
          });

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
    this.accommodationService.getAllStaffHouses().subscribe({
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
    this.accommodationService.getAllRooms().subscribe({
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
    this.accommodationService.getAllBookings({}).subscribe({
      next: (bookings: AccommodationBooking[] | { results?: AccommodationBooking[] }) => {
        // Handle both array and paginated response
        const bookingsList: AccommodationBooking[] = Array.isArray(bookings)
          ? bookings
          : bookings.results || [];

        this.bookings = bookingsList.map(b => ({
          id: b.id,
          staff_house_id: b.staff_house,
          room_id: b.room,
          date: b.date,
          status: b.status,
          guest_name: b.staff_name,
          trf_id: b.trf,
          notes: b.notes,
        }));

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

    this.accommodationService.getAllRooms(this.selectedStaffHouse).subscribe({
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
    if (!this.dateRange.from || !this.dateRange.to) return true;

    const startDate = new Date(this.dateRange.from);
    const endDate = new Date(this.dateRange.to);
    const currentDate = new Date(startDate);

    while (currentDate <= endDate) {
      const dateStr = this.formatDateForComparison(currentDate);
      const isBooked = this.bookings.some(
        b =>
          b.room_id === roomId &&
          this.formatDateForComparison(new Date(b.date)) === dateStr &&
          b.status !== 'Cancelled'
      );

      if (isBooked) return false;
      currentDate.setDate(currentDate.getDate() + 1);
    }

    return true;
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

    // Allow same-day checkout (checkOut == checkIn is valid)
    if (checkOut < checkIn) {
      this.toastService.error('Check-out date cannot be before check-in date');
      return;
    }

    // If TSR reference exists, validate dates are within TSR travel dates
    if (this.hasTsrReference && this.tsrMinDate && this.tsrMaxDate) {
      const tsrMin = new Date(this.tsrMinDate);
      const tsrMax = new Date(this.tsrMaxDate);

      if (checkIn < tsrMin || checkIn > tsrMax) {
        this.toastService.error(
          `Check-in date must be within TSR travel dates (${this.formatDateForDisplay(tsrMin)} - ${this.formatDateForDisplay(tsrMax)})`
        );
        return;
      }

      if (checkOut < tsrMin || checkOut > tsrMax) {
        this.toastService.error(
          `Check-out date must be within TSR travel dates (${this.formatDateForDisplay(tsrMin)} - ${this.formatDateForDisplay(tsrMax)})`
        );
        return;
      }

      if (checkOut > tsrMax) {
        this.toastService.error(
          `Check-out date cannot be after TSR return date (${this.formatDateForDisplay(tsrMax)})`
        );
        return;
      }
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

    const assignmentData = {
      staff_house: this.selectedStaffHouse!,
      room: this.selectedRoom,
      start_date: this.checkInDate,
      end_date: this.checkOutDate,
      notes: this.bookingNotes,
      assigned_room_info: `${staffHouse?.name} - ${room?.name} (${this.formatDateForDisplay(checkIn)} - ${this.formatDateForDisplay(checkOut)})`,
    };

    // Call the backend assign endpoint which creates daily booking records
    this.accommodationService
      .assignAccommodation(this.selectedRequest.id, assignmentData)
      .subscribe({
        next: response => {
          this.toastService.success(
            response.message ||
              `Room assigned successfully for ${this.selectedRequest!.requestorName}`
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

    this.accommodationService
      .rejectRequest(
        this.selectedRequest.id,
        'No rooms available for requested dates and location. Request rejected by Accommodation Admin.'
      )
      .subscribe({
        next: () => {
          this.toastService.success(
            `Request ${this.selectedRequest!.request_number} rejected due to no available rooms`
          );
          this.loadAccommodationRequests();
          this.selectedRequest = null;
          this.resetFormFields();
          this.isProcessing = false;
        },
        error: err => {
          this.toastService.error(
            this.errorHandler.getErrorMessage(err, 'Failed to reject request')
          );
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

    // Find and delete all booking records for this accommodation
    this.accommodationService.getAllBookings({ status: 'Confirmed' }).subscribe({
      next: (bookings: AccommodationBooking[] | { results?: AccommodationBooking[] }) => {
        const bookingsList: AccommodationBooking[] = Array.isArray(bookings)
          ? bookings
          : bookings.results || [];
        const relatedBookings = bookingsList.filter(b => b.trf === booking.id);

        const deletePromises = relatedBookings.map(b =>
          lastValueFrom(this.accommodationService.deleteBooking(b.id))
        );

        Promise.all(deletePromises)
          .then(() => {
            // Update request status back to Approved
            this.accommodationService.updateRequest(booking.id, { status: 'Approved' }).subscribe({
              next: () => {
                this.toastService.success(
                  `Booking for ${booking.requestorName} cancelled successfully`
                );
                this.loadAccommodationRequests();
                this.fetchBookings();
                this.isProcessing = false;
              },
              error: () => {
                this.isProcessing = false;
              },
            });
          })
          .catch(err => {
            console.error('Failed to delete bookings:', err);
            this.toastService.error('Failed to cancel booking');
            this.isProcessing = false;
          });
      },
      error: () => {
        this.toastService.error('Failed to fetch bookings for cancellation');
        this.isProcessing = false;
      },
    });
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
    const dateStr = this.formatDateForComparison(date);
    const booking = this.bookings.find(
      b =>
        b.room_id === roomId &&
        this.formatDateForComparison(new Date(b.date)) === dateStr &&
        b.status !== 'Cancelled'
    );

    if (booking) {
      return {
        isOccupied: true,
        status: booking.status,
        guestName: booking.guest_name || 'Unknown',
      };
    }

    return { isOccupied: false, status: null, guestName: null };
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
