import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TrfService } from '../../trf-management/services/trf.service';
import { ToastService } from '../../../core/services/toast.service';

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
  travelType: string;
  department: string;
}

@Component({
  selector: 'app-flights-processing',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './flights-processing.component.html',
  styleUrl: './flights-processing.component.scss'
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
  flightNotes = '';

  // Search and filter
  searchTerm = '';
  statusFilter = 'all';

  constructor(
    private trfService: TrfService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.fetchPendingTrfs();
    this.fetchBookedFlights();
  }

  /**
   * Fetch pending TRFs (Approved status, requiring flights)
   */
  fetchPendingTrfs(): void {
    this.isLoadingPending = true;
    this.errorPending = null;

    this.trfService.getAllTrfs().subscribe({
      next: (response: any) => {
        const trfs = response.results || response.trfs || [];

        // Filter for Approved TRFs requiring flights (Overseas, Home Leave, Domestic with itinerary)
        const approvedTrfs = trfs.filter((trf: any) => {
          if (trf.status !== 'Approved') return false;

          if (trf.travel_type === 'Overseas' || trf.travel_type === 'Home Leave Passage') {
            return true;
          }

          if (trf.travel_type === 'Domestic' && trf.domestic_travel_details?.itinerary?.length > 0) {
            return true;
          }

          return false;
        });

        const mappedTrfs = approvedTrfs.map((trf: any) => {
          let destinationSummary = 'N/A';
          let requestedDate = trf.submitted_at || trf.created_at;
          let itinerary: ItinerarySegment[] | undefined;

          // Support both snake_case (list API) and camelCase (detail API) formats
          const overseasDetails = trf.overseas_travel_details || trf.overseasTravelDetails;
          const homeLeaveDetails = trf.home_leave_details || trf.overseasTravelDetails; // Home leave reuses overseas structure
          const domesticDetails = trf.domestic_travel_details || trf.domesticTravelDetails;

          if (overseasDetails?.itinerary?.length) {
            itinerary = overseasDetails.itinerary;
            if (itinerary) {
              destinationSummary = itinerary
                .map(s => `${s.from_location || s.from} → ${s.to_location || s.to}`)
                .join(', ');
              requestedDate = itinerary[0]?.departure_date || itinerary[0]?.date || requestedDate;
            }
          } else if (homeLeaveDetails?.itinerary?.length) {
            itinerary = homeLeaveDetails.itinerary;
            if (itinerary) {
              destinationSummary = itinerary
                .map(s => `${s.from_location || s.from} → ${s.to_location || s.to}`)
                .join(', ');
              requestedDate = itinerary[0]?.departure_date || itinerary[0]?.date || requestedDate;
            }
          } else if (domesticDetails?.itinerary?.length) {
            itinerary = domesticDetails.itinerary;
            if (itinerary) {
              destinationSummary = itinerary
                .map(s => `${s.from_location || s.from} → ${s.to_location || s.to}`)
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
            itinerary
          };
        });

        this.pendingTrfs = mappedTrfs;
        this.filteredPendingTrfs = mappedTrfs;
        this.applyFilters();
        this.isLoadingPending = false;
      },
      error: (err) => {
        console.error('Failed to fetch pending TRFs:', err);
        this.errorPending = 'Failed to load TRFs. Please try again.';
        this.pendingTrfs = [];
        this.isLoadingPending = false;
      }
    });
  }

  /**
   * Fetch booked flights
   */
  fetchBookedFlights(): void {
    this.isLoadingBooked = true;

    this.trfService.getAllTrfs().subscribe({
      next: (response: any) => {
        const trfs = response.results || response.trfs || [];

        // Filter for TRFs with flight bookings
        const bookedTrfs = trfs.filter((trf: any) =>
          trf.has_flight_booking && trf.flight_details
        );

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
          travelType: trf.travel_type,
          department: trf.department || 'N/A'
        }));

        this.isLoadingBooked = false;
      },
      error: (err) => {
        console.error('Failed to fetch booked flights:', err);
        this.bookedFlights = [];
        this.isLoadingBooked = false;
      }
    });
  }

  /**
   * Select TRF for booking
   */
  selectTrf(trf: PendingTrf): void {
    this.selectedTrf = trf;
    this.resetFormFields();

    // Auto-populate from itinerary if available
    if (trf.itinerary && trf.itinerary.length > 0) {
      const firstSegment = trf.itinerary[0];
      const lastSegment = trf.itinerary[trf.itinerary.length - 1];

      // Departure details
      if (firstSegment.from_location || firstSegment.from) {
        this.departureAirport = firstSegment.from_location || firstSegment.from || '';
      }
      if (firstSegment.departure_date || firstSegment.date) {
        const depDate = firstSegment.departure_date || firstSegment.date;
        if (depDate) {
          this.departureDate = this.formatDateForInput(depDate);
        }
      }
      if (firstSegment.etd) {
        this.departureTime = firstSegment.etd;
      }

      // Arrival details
      if (lastSegment.to_location || lastSegment.to) {
        this.arrivalAirport = lastSegment.to_location || lastSegment.to || '';
      }
      if (lastSegment.arrival_date || lastSegment.date) {
        const arrDate = lastSegment.arrival_date || lastSegment.date;
        if (arrDate) {
          this.arrivalDate = this.formatDateForInput(arrDate);
        }
      }
      if (lastSegment.eta) {
        this.arrivalTime = lastSegment.eta;
      }
    }
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
    this.flightNotes = '';
  }

  /**
   * Book flight for selected TRF
   */
  bookFlight(): void {
    if (!this.selectedTrf || this.selectedTrf.status !== 'Approved') {
      this.toastService.error('Flights can only be booked for Approved TRFs');
      return;
    }

    this.isProcessing = true;

    const payload = {
      pnr: this.pnr,
      airline: this.airline,
      flightNumber: this.flightNumber,
      departureAirport: this.departureAirport,
      arrivalAirport: this.arrivalAirport,
      departureDateTime: this.departureDate ? `${this.departureDate}T${this.departureTime || '00:00'}` : undefined,
      arrivalDateTime: this.arrivalDate ? `${this.arrivalDate}T${this.arrivalTime || '00:00'}` : undefined,
      flightNotes: this.flightNotes
    };

    this.trfService.bookFlight(this.selectedTrf.id, payload).subscribe({
      next: (response: any) => {
        const trfDisplay = this.selectedTrf!.request_number || this.selectedTrf!.id;
        this.toastService.success(`Flight booked successfully for TRF ${trfDisplay}`);
        this.fetchPendingTrfs();
        this.fetchBookedFlights();
        this.selectedTrf = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to book flight: ' + (err.error?.error || err.message || 'Unknown error'));
        this.isProcessing = false;
      }
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
    if (!confirm(`Cancel TRF ${trfDisplay} due to no available flights?`)) {
      return;
    }

    this.isProcessing = true;

    this.trfService.rejectTrf(this.selectedTrf.id, 'No flights available for requested travel dates and destinations. Request cancelled by Flight Admin.').subscribe({
      next: () => {
        this.toastService.success(`TRF ${trfDisplay} cancelled due to no available flights`);
        this.fetchPendingTrfs();
        this.selectedTrf = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to cancel request: ' + (err.error?.error || err.message || 'Unknown error'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Cancel booking
   */
  cancelBooking(flight: BookedFlight): void {
    const trfDisplay = flight.trfRequestNumber || flight.trfId;
    if (!confirm(`Cancel flight booking for TRF ${trfDisplay}?`)) {
      return;
    }

    this.isProcessing = true;

    this.trfService.cancelFlightBooking(flight.id).subscribe({
      next: () => {
        this.toastService.success(`Flight booking for TRF ${trfDisplay} cancelled successfully`);
        this.fetchPendingTrfs();
        this.fetchBookedFlights();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to cancel booking: ' + (err.error?.error || err.message || 'Unknown error'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Switch tab
   */
  switchTab(tab: 'pending' | 'booked'): void {
    this.activeTab = tab;
    if (tab === 'pending' && this.pendingTrfs.length === 0) {
      this.fetchPendingTrfs();
    } else if (tab === 'booked' && this.bookedFlights.length === 0) {
      this.fetchBookedFlights();
    }
  }

  /**
   * View TRF details
   */
  viewTrf(trfId: string): void {
    this.router.navigate(['/trf/view', trfId]);
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
   * Get status badge class
   */
  getStatusClass(status: string): string {
    const statusLower = status.toLowerCase();
    if (statusLower === 'approved') return 'badge-success';
    if (statusLower === 'booked') return 'badge-success';
    return 'badge-secondary';
  }

  /**
   * Retry loading pending TRFs
   */
  retryPending(): void {
    this.fetchPendingTrfs();
  }

  /**
   * Get travel type badge class
   */
  getTravelTypeBadgeClass(travelType: string): string {
    switch (travelType) {
      case 'Overseas': return 'badge-blue';
      case 'Home Leave Passage': return 'badge-purple';
      case 'Domestic': return 'badge-green';
      default: return 'badge-gray';
    }
  }

  /**
   * Check if form is valid
   */
  isFormValid(): boolean {
    return !!(
      this.pnr &&
      this.airline &&
      this.flightNumber &&
      this.departureAirport &&
      this.arrivalAirport &&
      this.departureDate &&
      this.departureTime &&
      this.arrivalDate &&
      this.arrivalTime
    );
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
      filtered = filtered.filter(trf =>
        trf.request_number?.toLowerCase().includes(searchLower) ||
        trf.requestorName.toLowerCase().includes(searchLower) ||
        trf.destinationSummary.toLowerCase().includes(searchLower) ||
        trf.department.toLowerCase().includes(searchLower)
      );
    }

    this.filteredPendingTrfs = filtered;
  }
}
