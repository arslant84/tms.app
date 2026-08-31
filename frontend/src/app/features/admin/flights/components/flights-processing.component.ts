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
import {
  ItinerarySegment,
  FlightLegForm,
  emptyLeg as mapperEmptyLeg,
  formatDateForInput as mapperFormatDateForInput,
  legFromSegment as mapperLegFromSegment,
  splitItineraryByDirection as mapperSplitItineraryByDirection,
  legToSegmentPayload as mapperLegToSegmentPayload,
  getValidationIssues as mapperGetValidationIssues,
  isFormValid as mapperIsFormValid,
  getTravelTypeBadgeClass as mapperGetTravelTypeBadgeClass,
  extractErrorMessage as mapperExtractErrorMessage,
} from './flights-processing.mapper';

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
  outboundLegs: FlightLegForm[] = [mapperEmptyLeg()];
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
          if (trf.travel_type === 'Overseas' || trf.travel_type === 'External Parties') return true;
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
          const domesticDetails = trf.domestic_travel_details || trf.domesticTravelDetails;
          const externalDetails =
            trf.external_parties_travel_details || trf.externalPartiesTravelDetails;

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
          } else if (externalDetails?.itinerary?.length) {
            itinerary = externalDetails.itinerary;
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
   * True when the TRF's own itinerary comes back to its starting point -
   * drives whether the Return leg section is shown in the booking form.
   * There's no persisted "trip type" field on the backend (the create
   * wizard collects one locally but never sends it to the API), so this
   * is inferred from the itinerary itself: a round trip's last leg lands
   * back where the first leg departed from.
   */
  get isRoundTrip(): boolean {
    const itinerary = this.selectedTrf?.itinerary;
    if (!itinerary || itinerary.length < 2) {
      return false;
    }
    const origin = itinerary[0].from_location || itinerary[0].from;
    const finalDestination =
      itinerary[itinerary.length - 1].to_location || itinerary[itinerary.length - 1].to;
    return !!origin && !!finalDestination && origin === finalDestination;
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
      const { outbound, returning } = mapperSplitItineraryByDirection(itinerary, this.isRoundTrip);
      this.outboundLegs = outbound.map(segment => mapperLegFromSegment(segment));
      if (this.isRoundTrip && returning.length) {
        this.returnLegs = returning.map(segment => mapperLegFromSegment(segment));
      }
    }

    this.isBookingModalOpen = true;
  }

  closeBookingModal(): void {
    this.isBookingModalOpen = false;
    this.selectedTrf = null;
    this.resetFormFields();
  }

  addOutboundLeg(): void {
    this.outboundLegs.push(mapperEmptyLeg());
  }

  removeOutboundLeg(index: number): void {
    if (this.outboundLegs.length > 1) {
      this.outboundLegs.splice(index, 1);
    }
  }

  addReturnLeg(): void {
    this.returnLegs.push(mapperEmptyLeg());
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
    this.outboundLegs = [mapperEmptyLeg()];
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

  private buildBookingFormData(): FormData {
    const payload = new FormData();
    payload.set('pnr', this.pnr);
    if (this.airline) {
      payload.set('airline', this.airline);
    }
    const segments = [
      ...this.outboundLegs.map((leg, i) => mapperLegToSegmentPayload(leg, 'OUTBOUND', i + 1)),
      ...this.returnLegs.map((leg, i) => mapperLegToSegmentPayload(leg, 'RETURN', i + 1)),
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
        const errorMessage = mapperExtractErrorMessage(err);
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
    return mapperFormatDateForInput(date);
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
    return mapperGetTravelTypeBadgeClass(travelType);
  }

  /**
   * Check if form is valid
   */
  isFormValid(): boolean {
    return mapperIsFormValid(this.validationParams());
  }

  /**
   * Human-readable list of what's still missing, shown next to the
   * Confirm button so a disabled button is never a silent mystery.
   */
  getValidationIssues(): string[] {
    return mapperGetValidationIssues(this.validationParams());
  }

  private validationParams() {
    return {
      pnr: this.pnr,
      airline: this.airline,
      isAirlineRequired: this.isAirlineRequired,
      eTicketFile: this.eTicketFile,
      outboundLegs: this.outboundLegs,
      returnLegs: this.returnLegs,
      isRoundTrip: this.isRoundTrip,
    };
  }

  /**
   * Clear form
   */
  clearForm(): void {
    this.resetFormFields();
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
