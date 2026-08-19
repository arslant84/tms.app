import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TrfService } from '../../../trf-management/services/trf.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { DepartmentNamePipe } from '../../../../core/pipes/department-name.pipe';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';

interface ItinerarySegment {
  from_location?: string;
  from?: string;
  to_location?: string;
  to?: string;
  departure_date?: string;
  arrival_date?: string;
  date?: string;
  etd?: string;
  eta?: string;
}

interface PendingTrf {
  id: string;
  request_number?: string;
  requestorName: string;
  department: string;
  staffId: string;
  purpose: string;
  travelType: string;
  status: string;
  destinationSummary: string;
  requestedDate: string;
  itinerary?: ItinerarySegment[];
  tripType?: 'One Way' | 'Round Trip';
}

interface BookedFlight {
  id: string;
  trfId: string;
  trfRequestNumber?: string;
  flightNumber: string;
  airline: string;
  departureLocation: string;
  arrivalLocation: string;
  departureDate: string;
  arrivalDate: string;
  bookingReference: string;
  status: string;
  remarks?: string;
  requestorName: string;
  staffId: string;
  travelType: string;
  department: string;
}

@Component({
  selector: 'app-flights-processing',
  standalone: true,
  imports: [CommonModule, FormsModule, DepartmentNamePipe, LoadingSpinnerComponent],
  templateUrl: './flights-processing.component.html',
  styleUrl: './flights-processing.component.scss',
})
export class FlightsProcessingComponent implements OnInit {
  activeTab: 'pending' | 'booked' = 'pending';

  // Pending TRFs
  pendingTrfs: PendingTrf[] = [];
  filteredPendingTrfs: PendingTrf[] = [];
  isLoadingPending = false;
  errorPending: string | null = null;

  // Booked Flights
  bookedFlights: BookedFlight[] = [];
  isLoadingBooked = false;

  // Selected TRF for booking
  selectedTrf: PendingTrf | null = null;
  isProcessing = false;

  // Booking form fields
  pnr = '';
  airline = '';
  flightNumber = '';
  departureAirport = '';
  arrivalAirport = '';
  departureDate: string = '';
  departureTime = '';
  arrivalDate: string = '';
  arrivalTime = '';
  returnFlightNumber = '';
  returnDepartureDate = '';
  returnDepartureTime = '';
  returnArrivalDate = '';
  returnArrivalTime = '';
  eTicketFile: File | null = null;
  flightNotes = '';

  // Search and filter
  searchTerm = '';
  statusFilter = 'all';

  constructor(
    private trfService: TrfService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private router: Router,
    public dateUtils: DateUtilsService,
    private statusUtils: StatusUtilsService,
    private errorHandler: HttpErrorHandlerService
  ) {}

  ngOnInit(): void {
    this.loadAll();
  }

  private loadAll(): void {
    this.isLoadingPending = true;
    this.isLoadingBooked = true;
    this.errorPending = null;

    this.trfService.getAllTrfs({ adminView: true, page_size: 1000 }).subscribe({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      next: (response: any) => {
        const trfs = response.results || response.trfs || [];

        // Pending: Approved TRFs requiring flights
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const approvedTrfs = trfs.filter((trf: any) => {
          if (trf.status !== 'Approved') return false;
          if (
            trf.travel_type === 'Overseas' ||
            trf.travel_type === 'Home Leave' ||
            trf.travel_type === 'External Parties'
          )
            return true;
          if (trf.travel_type === 'Domestic' && trf.domestic_travel_details?.itinerary?.length > 0)
            return true;
          return false;
        });

        // eslint-disable-next-line complexity, @typescript-eslint/no-explicit-any
        const mappedTrfs = approvedTrfs.map((trf: any) => {
          let destinationSummary = 'N/A';
          let requestedDate = trf.submitted_at || trf.created_at;
          let itinerary: ItinerarySegment[] | undefined;

          const overseasDetails = trf.overseas_travel_details || trf.overseasTravelDetails;
          const homeLeaveDetails = trf.home_leave_details || trf.overseasTravelDetails;
          const domesticDetails = trf.domestic_travel_details || trf.domesticTravelDetails;
          const externalDetails =
            trf.external_parties_travel_details || trf.externalPartiesTravelDetails;
          const tripType: 'One Way' | 'Round Trip' =
            overseasDetails?.tripType ||
            homeLeaveDetails?.tripType ||
            domesticDetails?.tripType ||
            externalDetails?.tripType ||
            'One Way';

          if (overseasDetails?.itinerary?.length) {
            itinerary = overseasDetails.itinerary;
            if (itinerary) {
              destinationSummary = itinerary
                .map(
                  (s: ItinerarySegment) => `${s.from_location || s.from} → ${s.to_location || s.to}`
                )
                .join(', ');
              requestedDate = itinerary[0]?.departure_date || itinerary[0]?.date || requestedDate;
            }
          } else if (homeLeaveDetails?.itinerary?.length) {
            itinerary = homeLeaveDetails.itinerary;
            if (itinerary) {
              destinationSummary = itinerary
                .map(
                  (s: ItinerarySegment) => `${s.from_location || s.from} → ${s.to_location || s.to}`
                )
                .join(', ');
              requestedDate = itinerary[0]?.departure_date || itinerary[0]?.date || requestedDate;
            }
          } else if (domesticDetails?.itinerary?.length) {
            itinerary = domesticDetails.itinerary;
            if (itinerary) {
              destinationSummary = itinerary
                .map(
                  (s: ItinerarySegment) => `${s.from_location || s.from} → ${s.to_location || s.to}`
                )
                .join(', ');
              requestedDate = itinerary[0]?.departure_date || itinerary[0]?.date || requestedDate;
            }
          } else if (trf.purpose) {
            destinationSummary = trf.purpose.substring(0, 50) + '...';
          }

          return {
            id: trf.id,
            request_number: trf.request_number,
            requestorName: trf.requestor_name || 'N/A',
            department: trf.department || 'N/A',
            staffId: trf.staff_id || 'N/A',
            purpose: trf.purpose || 'N/A',
            travelType: trf.travel_type,
            status: trf.status,
            destinationSummary,
            requestedDate,
            itinerary,
            tripType,
          };
        });

        this.pendingTrfs = mappedTrfs;
        this.filteredPendingTrfs = mappedTrfs;
        this.applyFilters();

        // Booked: TRFs with flight bookings
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const bookedTrfs = trfs.filter((trf: any) => trf.has_flight_booking && trf.flight_details);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        this.bookedFlights = bookedTrfs.map((trf: any) => ({
          id: trf.flight_details.id,
          trfId: trf.id,
          trfRequestNumber: trf.request_number,
          flightNumber: trf.flight_details.flightNumber || 'N/A',
          airline: trf.flight_details.airline || 'N/A',
          departureLocation: trf.flight_details.departureLocation || 'N/A',
          arrivalLocation: trf.flight_details.arrivalLocation || 'N/A',
          departureDate: trf.flight_details.departureDate,
          arrivalDate: trf.flight_details.arrivalDate,
          bookingReference: trf.flight_details.bookingReference || trf.flight_details.pnr || 'N/A',
          status: trf.flight_details.status || 'Booked',
          remarks: trf.flight_details.remarks,
          requestorName: trf.requestor_name || 'N/A',
          staffId: trf.staff_id || 'N/A',
          travelType: trf.travel_type,
          department: trf.department || 'N/A',
        }));

        this.isLoadingPending = false;
        this.isLoadingBooked = false;
      },
      error: err => {
        console.error('Failed to fetch TRFs:', err);
        this.errorPending = 'Failed to load TRFs. Please try again.';
        this.pendingTrfs = [];
        this.bookedFlights = [];
        this.isLoadingPending = false;
        this.isLoadingBooked = false;
      },
    });
  }

  /**
   * True when the TRF's own itinerary is Round Trip - drives whether the
   * Return segment row is shown in the booking form (auto, not a manual
   * add/remove toggle).
   */
  get isRoundTrip(): boolean {
    return this.selectedTrf?.tripType === 'Round Trip';
  }

  /**
   * Airline is only required for Overseas travel - domestic routes have a
   * single national carrier, so it isn't worth forcing admins to retype it.
   */
  get isAirlineRequired(): boolean {
    return this.selectedTrf?.travelType === 'Overseas';
  }

  /**
   * Select TRF for booking. Outbound is always the first itinerary segment;
   * Return (shown only when the TRF is Round Trip) is the last segment -
   * the itinerary always has >=2 segments for Round Trip TRFs.
   */
  selectTrf(trf: PendingTrf): void {
    this.selectedTrf = trf;
    this.resetFormFields();

    if (!trf.itinerary || trf.itinerary.length === 0) {
      return;
    }

    this.populateOutboundSegment(trf.itinerary[0]);

    if (this.isRoundTrip && trf.itinerary.length >= 2) {
      this.populateReturnSegment(trf.itinerary[trf.itinerary.length - 1]);
    }
  }

  private populateOutboundSegment(segment: ItinerarySegment): void {
    this.departureAirport = segment.from_location || segment.from || '';
    this.arrivalAirport = segment.to_location || segment.to || '';
    const depDate = segment.departure_date || segment.date;
    if (depDate) {
      this.departureDate = this.formatDateForInput(depDate);
    }
    if (segment.etd) {
      this.departureTime = segment.etd;
    }
    const arrDate = segment.arrival_date || segment.date;
    if (arrDate) {
      this.arrivalDate = this.formatDateForInput(arrDate);
    }
    if (segment.eta) {
      this.arrivalTime = segment.eta;
    }
  }

  private populateReturnSegment(segment: ItinerarySegment): void {
    const depDate = segment.departure_date || segment.date;
    if (depDate) {
      this.returnDepartureDate = this.formatDateForInput(depDate);
    }
    if (segment.etd) {
      this.returnDepartureTime = segment.etd;
    }
    const arrDate = segment.arrival_date || segment.date;
    if (arrDate) {
      this.returnArrivalDate = this.formatDateForInput(arrDate);
    }
    if (segment.eta) {
      this.returnArrivalTime = segment.eta;
    }
  }

  /**
   * Handle e-ticket file selection
   */
  onETicketSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.eTicketFile = input.files?.[0] || null;
  }

  /**
   * Reset form fields
   */
  resetFormFields(): void {
    this.pnr = '';
    this.airline = '';
    this.flightNumber = '';
    this.departureAirport = '';
    this.arrivalAirport = '';
    this.departureDate = '';
    this.departureTime = '';
    this.arrivalDate = '';
    this.arrivalTime = '';
    this.returnFlightNumber = '';
    this.returnDepartureDate = '';
    this.returnDepartureTime = '';
    this.returnArrivalDate = '';
    this.returnArrivalTime = '';
    this.eTicketFile = null;
    this.flightNotes = '';
  }

  /**
   * Validate the four HH:MM time inputs - type="time" can be bypassed via
   * paste, so this catches anything the browser's own picker wouldn't.
   */
  private validateTimeFields(): boolean {
    const timePattern = /^\d{2}:\d{2}(:\d{2})?$/;
    const checks: Array<[string, string]> = [
      [this.departureTime, 'departure time'],
      [this.arrivalTime, 'arrival time'],
      [this.returnDepartureTime, 'return departure time'],
      [this.returnArrivalTime, 'return arrival time'],
    ];
    for (const [value, label] of checks) {
      if (value && !timePattern.test(value)) {
        this.toastService.error(`Invalid ${label}. Please use HH:MM format.`);
        return false;
      }
    }
    return true;
  }

  private buildBookingFormData(): FormData {
    const payload = new FormData();
    payload.set('pnr', this.pnr);
    if (this.airline) {
      payload.set('airline', this.airline);
    }
    payload.set('flightNumber', this.flightNumber);
    payload.set('departureAirport', this.departureAirport);
    payload.set('arrivalAirport', this.arrivalAirport);
    if (this.departureDate) {
      payload.set('departureDateTime', `${this.departureDate}T${this.departureTime || '00:00'}`);
    }
    if (this.arrivalDate) {
      payload.set('arrivalDateTime', `${this.arrivalDate}T${this.arrivalTime || '00:00'}`);
    }
    if (this.isRoundTrip) {
      this.appendReturnSegment(payload);
    }
    if (this.eTicketFile) {
      payload.set('eTicket', this.eTicketFile);
    }
    payload.set('flightNotes', this.flightNotes);
    return payload;
  }

  private appendReturnSegment(payload: FormData): void {
    payload.set('returnFlightNumber', this.returnFlightNumber);
    if (this.returnDepartureDate) {
      payload.set(
        'returnDepartureDateTime',
        `${this.returnDepartureDate}T${this.returnDepartureTime || '00:00'}`
      );
    }
    if (this.returnArrivalDate) {
      payload.set(
        'returnArrivalDateTime',
        `${this.returnArrivalDate}T${this.returnArrivalTime || '00:00'}`
      );
    }
  }

  /**
   * Book flight for selected TRF
   */
  bookFlight(): void {
    if (!this.selectedTrf || this.selectedTrf.status !== 'Approved') {
      this.toastService.error('Flights can only be booked for Approved TRFs');
      return;
    }

    if (!this.validateTimeFields()) {
      return;
    }

    this.isProcessing = true;
    const payload = this.buildBookingFormData();

    this.trfService.bookFlight(this.selectedTrf.id, payload).subscribe({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      next: (_response: any) => {
        const trfDisplay = this.selectedTrf!.request_number || this.selectedTrf!.id;
        this.toastService.success(`Flight booked successfully for TRF ${trfDisplay}`);
        this.loadAll();
        this.selectedTrf = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: err => {
        const errorMessage = this.extractErrorMessage(err);
        this.toastService.error(errorMessage);
        this.isProcessing = false;
      },
    });
  }

  /**
   * Cancel TRF (No flights available)
   */
  noFlightsAvailable(): void {
    if (!this.selectedTrf || this.selectedTrf.status !== 'Approved') {
      this.toastService.error('This action can only be performed on Approved TRFs');
      return;
    }

    const trfDisplay = this.selectedTrf.request_number || this.selectedTrf.id;
    this.confirmationService
      .confirm({
        title: 'Cancel TRF',
        message: `Cancel TRF ${trfDisplay} due to no available flights?`,
        confirmText: 'Cancel TRF',
        type: 'danger',
      })
      .subscribe(confirmed => {
        if (!confirmed) return;
        this.executeNoFlightsAvailable(trfDisplay);
      });
  }

  private executeNoFlightsAvailable(trfDisplay: string): void {
    if (!this.selectedTrf) return;
    this.isProcessing = true;

    this.trfService
      .rejectTrf(
        this.selectedTrf.id,
        'No flights available for requested travel dates and destinations. Request cancelled by Flight Admin.'
      )
      .subscribe({
        next: () => {
          this.toastService.success(`TRF ${trfDisplay} cancelled due to no available flights`);
          this.loadAll();
          this.selectedTrf = null;
          this.resetFormFields();
          this.isProcessing = false;
        },
        error: err => {
          this.toastService.error(
            this.errorHandler.getErrorMessage(err, 'Failed to cancel request')
          );
          this.isProcessing = false;
        },
      });
  }

  /**
   * Cancel booking
   */
  cancelBooking(flight: BookedFlight): void {
    const trfDisplay = flight.trfRequestNumber || flight.trfId;
    this.confirmationService
      .confirm({
        title: 'Cancel Booking',
        message: `Cancel flight booking for TRF ${trfDisplay}?`,
        confirmText: 'Cancel Booking',
        type: 'danger',
      })
      .subscribe(confirmed => {
        if (!confirmed) return;
        this.executeCancelBooking(flight, trfDisplay);
      });
  }

  private executeCancelBooking(flight: BookedFlight, trfDisplay: string): void {
    this.isProcessing = true;

    this.trfService.cancelFlightBooking(flight.id).subscribe({
      next: () => {
        this.toastService.success(`Flight booking for TRF ${trfDisplay} cancelled successfully`);
        this.loadAll();
        this.isProcessing = false;
      },
      error: err => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to cancel booking'));
        this.isProcessing = false;
      },
    });
  }

  /**
   * Switch tab
   */
  switchTab(tab: 'pending' | 'booked'): void {
    this.activeTab = tab;
  }

  /**
   * View TRF details
   */
  viewTrf(trfId: string): void {
    this.router.navigate(['/trf', trfId]);
  }

  /**
   * Navigate back to overview
   */
  goToOverview(): void {
    this.router.navigate(['/admin/flights']);
  }

  /**
   * Format date for input field (YYYY-MM-DD)
   */
  formatDateForInput(date: string | Date): string {
    if (!date) return '';
    try {
      const d = typeof date === 'string' ? new Date(date) : date;
      return d.toISOString().split('T')[0];
    } catch {
      return '';
    }
  }

  /**
   * Get status badge class - delegates to StatusUtilsService so the same
   * status renders the same color everywhere in the app.
   */
  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Retry loading pending TRFs
   */
  retryPending(): void {
    this.loadAll();
  }

  /**
   * Get travel type badge class
   */
  getTravelTypeBadgeClass(travelType: string): string {
    switch (travelType) {
      case 'Overseas':
        return 'badge-blue';
      case 'Home Leave':
        return 'badge-purple';
      case 'Domestic':
        return 'badge-green';
      default:
        return 'badge-gray';
    }
  }

  /**
   * Check if form is valid
   */
  isFormValid(): boolean {
    return this.isOutboundValid() && (!this.isRoundTrip || this.isReturnSegmentValid());
  }

  private isOutboundValid(): boolean {
    return !!(
      this.pnr &&
      (!this.isAirlineRequired || this.airline) &&
      this.flightNumber &&
      this.departureAirport &&
      this.arrivalAirport &&
      this.departureDate &&
      this.departureTime &&
      this.arrivalDate &&
      this.arrivalTime &&
      this.eTicketFile
    );
  }

  private isReturnSegmentValid(): boolean {
    return !!(
      this.returnFlightNumber &&
      this.returnDepartureDate &&
      this.returnDepartureTime &&
      this.returnArrivalDate &&
      this.returnArrivalTime
    );
  }

  /**
   * Clear form
   */
  clearForm(): void {
    this.resetFormFields();
  }

  /**
   * Extract error message from HTTP error response
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private extractErrorMessage(err: any): string {
    // Handle various Django REST framework error response formats
    if (err.error) {
      // Direct error message
      if (typeof err.error === 'string') {
        return err.error;
      }
      // { error: "message" } format
      if (err.error.error) {
        return err.error.error;
      }
      // { detail: "message" } format (DRF default)
      if (err.error.detail) {
        return err.error.detail;
      }
      // { message: "message" } format
      if (err.error.message) {
        return err.error.message;
      }
      // { non_field_errors: ["message"] } format
      if (err.error.non_field_errors && Array.isArray(err.error.non_field_errors)) {
        return err.error.non_field_errors.join(', ');
      }
      // { field: ["error1", "error2"] } format - extract first field error
      const keys = Object.keys(err.error);
      if (keys.length > 0 && Array.isArray(err.error[keys[0]])) {
        return `${keys[0]}: ${err.error[keys[0]].join(', ')}`;
      }
    }
    // Fallback to HTTP status message
    if (err.message) {
      return err.message;
    }
    return 'An unexpected error occurred. Please try again.';
  }

  /**
   * Apply search and status filters
   */
  applyFilters(): void {
    let filtered = [...this.pendingTrfs];

    // Apply status filter
    if (this.statusFilter !== 'all') {
      filtered = filtered.filter(trf => trf.status === this.statusFilter);
    }

    // Apply search term
    if (this.searchTerm) {
      const searchLower = this.searchTerm.toLowerCase();
      filtered = filtered.filter(
        trf =>
          trf.request_number?.toLowerCase().includes(searchLower) ||
          trf.requestorName.toLowerCase().includes(searchLower) ||
          trf.destinationSummary.toLowerCase().includes(searchLower) ||
          trf.department.toLowerCase().includes(searchLower)
      );
    }

    this.filteredPendingTrfs = filtered;
  }
}
