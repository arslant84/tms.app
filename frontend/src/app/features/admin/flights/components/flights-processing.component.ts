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

interface FlightLegForm {
  flightNumber: string;
  departureAirport: string;
  arrivalAirport: string;
  departureDate: string;
  departureTime: string;
  arrivalDate: string;
  arrivalTime: string;
}

interface FlightSegmentPayload {
  direction: 'OUTBOUND' | 'RETURN';
  sequence: number;
  flightNumber: string;
  departureAirport: string;
  arrivalAirport: string;
  departureDateTime: string;
  arrivalDateTime: string;
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
  isBookingModalOpen = false;

  // Booking form fields
  pnr = '';
  airline = '';
  outboundLegs: FlightLegForm[] = [this.emptyLeg()];
  returnLegs: FlightLegForm[] = [];
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
   * Open the booking modal for a TRF, pre-populating one leg row per
   * itinerary segment. Legs are split into Outbound/Return by grouping
   * consecutive segments that share the itinerary's first travel date
   * (Outbound) vs. every segment after that (Return) - itineraries don't
   * carry an explicit direction flag, so date-grouping is the best
   * available signal. Admins can still add/remove/edit legs afterward.
   */
  openBookingModal(trf: PendingTrf): void {
    this.selectedTrf = trf;
    this.resetFormFields();

    const itinerary = trf.itinerary || [];
    if (itinerary.length > 0) {
      const { outbound, returning } = this.splitItineraryByDirection(itinerary);
      this.outboundLegs = outbound.map(segment => this.legFromSegment(segment));
      if (this.isRoundTrip && returning.length) {
        this.returnLegs = returning.map(segment => this.legFromSegment(segment));
      }
    }

    this.isBookingModalOpen = true;
  }

  closeBookingModal(): void {
    this.isBookingModalOpen = false;
    this.selectedTrf = null;
    this.resetFormFields();
  }

  private splitItineraryByDirection(itinerary: ItinerarySegment[]): {
    outbound: ItinerarySegment[];
    returning: ItinerarySegment[];
  } {
    if (!this.isRoundTrip) {
      return { outbound: itinerary, returning: [] };
    }
    const firstDate = itinerary[0]?.departure_date || itinerary[0]?.date;
    const outbound = itinerary.filter(s => (s.departure_date || s.date) === firstDate);
    const returning = itinerary.filter(s => (s.departure_date || s.date) !== firstDate);
    return { outbound: outbound.length ? outbound : [itinerary[0]], returning };
  }

  private legFromSegment(segment: ItinerarySegment): FlightLegForm {
    const depDate = segment.departure_date || segment.date;
    const arrDate = segment.arrival_date || segment.date;
    return {
      flightNumber: '',
      departureAirport: segment.from_location || segment.from || '',
      arrivalAirport: segment.to_location || segment.to || '',
      departureDate: depDate ? this.formatDateForInput(depDate) : '',
      departureTime: this.parseItineraryTime(segment.etd),
      arrivalDate: arrDate ? this.formatDateForInput(arrDate) : '',
      arrivalTime: this.parseItineraryTime(segment.eta),
    };
  }

  /**
   * The TSR itinerary's ETD/ETA is free text (requestors can type "14:30"
   * or "Morning") - a native <input type="time"> silently drops anything
   * that isn't strict HH:MM, which is why it used to render empty even
   * though a value was set. Normalize real times, and translate the
   * common day-period labels to a representative clock time so the field
   * still starts pre-filled; admins can still edit it before confirming.
   */
  private parseItineraryTime(value?: string): string {
    if (!value) {
      return '';
    }
    const timeMatch = value.trim().match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
    if (timeMatch) {
      return `${timeMatch[1].padStart(2, '0')}:${timeMatch[2]}`;
    }
    const periodDefaults: Record<string, string> = {
      morning: '08:00',
      afternoon: '13:00',
      evening: '18:00',
      night: '21:00',
      noon: '12:00',
      midnight: '00:00',
    };
    return periodDefaults[value.trim().toLowerCase()] || '';
  }

  private emptyLeg(): FlightLegForm {
    return {
      flightNumber: '',
      departureAirport: '',
      arrivalAirport: '',
      departureDate: '',
      departureTime: '',
      arrivalDate: '',
      arrivalTime: '',
    };
  }

  addOutboundLeg(): void {
    this.outboundLegs.push(this.emptyLeg());
  }

  removeOutboundLeg(index: number): void {
    if (this.outboundLegs.length > 1) {
      this.outboundLegs.splice(index, 1);
    }
  }

  addReturnLeg(): void {
    this.returnLegs.push(this.emptyLeg());
  }

  removeReturnLeg(index: number): void {
    this.returnLegs.splice(index, 1);
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
    this.outboundLegs = [this.emptyLeg()];
    this.returnLegs = [];
    this.eTicketFile = null;
    this.flightNotes = '';
  }

  /**
   * Validate every leg's HH:MM time inputs - type="time" can be bypassed
   * via paste, so this catches anything the browser's own picker wouldn't.
   */
  private validateTimeFields(): boolean {
    const timePattern = /^\d{2}:\d{2}(:\d{2})?$/;
    for (const leg of [...this.outboundLegs, ...this.returnLegs]) {
      if (leg.departureTime && !timePattern.test(leg.departureTime)) {
        this.toastService.error('Invalid departure time. Please use HH:MM format.');
        return false;
      }
      if (leg.arrivalTime && !timePattern.test(leg.arrivalTime)) {
        this.toastService.error('Invalid arrival time. Please use HH:MM format.');
        return false;
      }
    }
    return true;
  }

  private legToSegmentPayload(
    leg: FlightLegForm,
    direction: 'OUTBOUND' | 'RETURN',
    sequence: number
  ): FlightSegmentPayload {
    return {
      direction,
      sequence,
      flightNumber: leg.flightNumber,
      departureAirport: leg.departureAirport,
      arrivalAirport: leg.arrivalAirport,
      departureDateTime: leg.departureDate
        ? `${leg.departureDate}T${leg.departureTime || '00:00'}`
        : '',
      arrivalDateTime: leg.arrivalDate ? `${leg.arrivalDate}T${leg.arrivalTime || '00:00'}` : '',
    };
  }

  private buildBookingFormData(): FormData {
    const payload = new FormData();
    payload.set('pnr', this.pnr);
    if (this.airline) {
      payload.set('airline', this.airline);
    }
    const segments = [
      ...this.outboundLegs.map((leg, i) => this.legToSegmentPayload(leg, 'OUTBOUND', i + 1)),
      ...this.returnLegs.map((leg, i) => this.legToSegmentPayload(leg, 'RETURN', i + 1)),
    ];
    payload.set('segments', JSON.stringify(segments));
    if (this.eTicketFile) {
      payload.set('eTicket', this.eTicketFile);
    }
    payload.set('flightNotes', this.flightNotes);
    return payload;
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
    const trfDisplay = this.selectedTrf.request_number || this.selectedTrf.id;

    this.trfService.bookFlight(this.selectedTrf.id, payload).subscribe({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      next: (_response: any) => {
        this.toastService.success(`Flight booked successfully for TRF ${trfDisplay}`);
        this.loadAll();
        this.closeBookingModal();
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
    if (!this.pnr || (this.isAirlineRequired && !this.airline) || !this.eTicketFile) {
      return false;
    }
    if (!this.outboundLegs.length || !this.outboundLegs.every(leg => this.isLegValid(leg))) {
      return false;
    }
    if (this.isRoundTrip) {
      return this.returnLegs.length > 0 && this.returnLegs.every(leg => this.isLegValid(leg));
    }
    return true;
  }

  private isLegValid(leg: FlightLegForm): boolean {
    return !!(
      leg.flightNumber &&
      leg.departureAirport &&
      leg.arrivalAirport &&
      leg.departureDate &&
      leg.departureTime &&
      leg.arrivalDate &&
      leg.arrivalTime
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
