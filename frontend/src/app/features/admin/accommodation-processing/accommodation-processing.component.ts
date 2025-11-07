import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AccommodationService, AccommodationRequest, AccommodationRoom, AccommodationStaffHouse } from '../../accommodation/services/accommodation.service';
import { ToastService } from '../../../core/services/toast.service';

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
}

interface BookedAccommodation {
  id: number;
  requestNumber: string;
  requestorName: string;
  staffHouseName: string;
  roomName: string;
  location: string;
  checkInDate: string;
  checkOutDate: string;
  status: string;
  notes?: string;
}

@Component({
  selector: 'app-accommodation-processing',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './accommodation-processing.component.html',
  styleUrl: './accommodation-processing.component.scss'
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
  availableRooms: AccommodationRoom[] = [];

  // Booking form fields
  selectedStaffHouse: number | null = null;
  selectedRoom: number | null = null;
  bookingNotes = '';

  constructor(
    private accommodationService: AccommodationService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.fetchPendingAccommodations();
    this.fetchBookedAccommodations();
    this.fetchStaffHouses();
  }

  /**
   * Fetch pending accommodation requests (Approved status)
   */
  fetchPendingAccommodations(): void {
    this.isLoadingPending = true;
    this.errorPending = null;

    this.accommodationService.getAllRequests({ status: 'Approved' }).subscribe({
      next: (response: any) => {
        const requests = response.results || response;

        this.pendingAccommodations = requests.map((req: any) => {
          // Extract accommodation details from additional_data
          const additionalData = req.additional_data || {};
          const accommodations = additionalData.accommodations || [];

          // Get the first accommodation for display
          const firstAccom = accommodations[0] || {};

          return {
            id: req.id,
            request_number: req.request_number || `ACC-${req.id}`,
            requestorName: req.requestor_name || 'N/A',
            department: req.department || 'N/A',
            staffId: req.staff_id || 'N/A',
            location: firstAccom.location || additionalData.location || 'N/A',
            checkInDate: firstAccom.check_in_date || 'N/A',
            checkOutDate: firstAccom.check_out_date || 'N/A',
            roomType: firstAccom.room_type || 'Any',
            status: req.status,
            requestedDate: req.submitted_at || req.created_at,
            duration: this.calculateDuration(firstAccom.check_in_date, firstAccom.check_out_date)
          };
        });

        this.isLoadingPending = false;
      },
      error: (err) => {
        console.error('Failed to fetch pending accommodations:', err);
        this.errorPending = 'Failed to load pending accommodations. Please try again.';
        this.pendingAccommodations = [];
        this.isLoadingPending = false;
      }
    });
  }

  /**
   * Fetch booked accommodations
   */
  fetchBookedAccommodations(): void {
    this.isLoadingBooked = true;

    this.accommodationService.getAllBookings({ status: 'Confirmed' }).subscribe({
      next: (response: any) => {
        // Handle both array and paginated response
        const bookings = Array.isArray(response) ? response : (response.results || []);

        this.bookedAccommodations = bookings.map((booking: any) => ({
          id: booking.id,
          requestNumber: booking.request_number || `ACC-${booking.id}`,
          requestorName: booking.staff_name || 'N/A',
          staffHouseName: booking.staff_house_name || 'N/A',
          roomName: booking.room_name || 'N/A',
          location: booking.location || 'N/A',
          checkInDate: booking.check_in_date || booking.date,
          checkOutDate: booking.check_out_date || booking.date,
          status: booking.status || 'Confirmed',
          notes: booking.notes
        }));

        this.isLoadingBooked = false;
      },
      error: (err) => {
        console.error('Failed to fetch booked accommodations:', err);
        this.bookedAccommodations = [];
        this.isLoadingBooked = false;
      }
    });
  }

  /**
   * Fetch all staff houses
   */
  fetchStaffHouses(): void {
    this.accommodationService.getAllStaffHouses().subscribe({
      next: (staffHouses) => {
        this.availableStaffHouses = staffHouses;
      },
      error: (err) => {
        console.error('Failed to fetch staff houses:', err);
        this.toastService.error('Failed to load staff houses');
      }
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
      next: (rooms) => {
        // Filter only available rooms
        this.availableRooms = rooms.filter(room => room.status === 'Available');
      },
      error: (err) => {
        console.error('Failed to fetch rooms:', err);
        this.toastService.error('Failed to load rooms');
        this.availableRooms = [];
      }
    });
  }

  /**
   * Select accommodation request for processing
   */
  selectRequest(request: PendingAccommodation): void {
    this.selectedRequest = request;
    this.resetFormFields();

    // Filter staff houses by location if specified
    if (request.location && request.location !== 'N/A') {
      this.accommodationService.getAllStaffHouses(request.location).subscribe({
        next: (staffHouses) => {
          this.availableStaffHouses = staffHouses;
        },
        error: (err) => {
          console.error('Failed to fetch staff houses:', err);
        }
      });
    }
  }

  /**
   * Reset form fields
   */
  resetFormFields(): void {
    this.selectedStaffHouse = null;
    this.selectedRoom = null;
    this.bookingNotes = '';
    this.availableRooms = [];
  }

  /**
   * Assign room to accommodation request
   */
  assignRoom(): void {
    if (!this.selectedRequest || !this.selectedRoom) {
      this.toastService.error('Please select a room to assign');
      return;
    }

    this.isProcessing = true;

    const payload = {
      room: this.selectedRoom,
      staff_house: this.selectedStaffHouse,
      request: this.selectedRequest.id,
      date: this.selectedRequest.checkInDate,
      check_in_date: this.selectedRequest.checkInDate,
      check_out_date: this.selectedRequest.checkOutDate,
      status: 'Confirmed',
      notes: this.bookingNotes
    };

    this.accommodationService.createBooking(payload).subscribe({
      next: (response: any) => {
        this.toastService.success(`Room assigned successfully for ${this.selectedRequest!.requestorName}`);
        this.fetchPendingAccommodations();
        this.fetchBookedAccommodations();
        this.selectedRequest = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to assign room: ' + (err.error?.error || err.message || 'Unknown error'));
        this.isProcessing = false;
      }
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

    if (!confirm(`Reject accommodation request ${this.selectedRequest.request_number} due to no available rooms?`)) {
      return;
    }

    this.isProcessing = true;

    this.accommodationService.rejectRequest(
      this.selectedRequest.id,
      'No rooms available for requested dates and location. Request rejected by Accommodation Admin.'
    ).subscribe({
      next: () => {
        this.toastService.success(`Request ${this.selectedRequest!.request_number} rejected due to no available rooms`);
        this.fetchPendingAccommodations();
        this.selectedRequest = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to reject request: ' + (err.error?.error || err.message || 'Unknown error'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Cancel booking
   */
  cancelBooking(booking: BookedAccommodation): void {
    if (!confirm(`Cancel room booking for ${booking.requestorName}?`)) {
      return;
    }

    this.isProcessing = true;

    this.accommodationService.deleteBooking(booking.id).subscribe({
      next: () => {
        this.toastService.success(`Booking for ${booking.requestorName} cancelled successfully`);
        this.fetchPendingAccommodations();
        this.fetchBookedAccommodations();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to cancel booking: ' + (err.error?.error || err.message || 'Unknown error'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Calculate duration between two dates
   */
  calculateDuration(checkIn: string, checkOut: string): number {
    if (!checkIn || !checkOut) return 0;
    try {
      const start = new Date(checkIn);
      const end = new Date(checkOut);
      const diff = end.getTime() - start.getTime();
      return Math.ceil(diff / (1000 * 60 * 60 * 24));
    } catch {
      return 0;
    }
  }

  /**
   * Switch tab
   */
  switchTab(tab: 'pending' | 'booked'): void {
    this.activeTab = tab;
    if (tab === 'pending' && this.pendingAccommodations.length === 0) {
      this.fetchPendingAccommodations();
    } else if (tab === 'booked' && this.bookedAccommodations.length === 0) {
      this.fetchBookedAccommodations();
    }
  }

  /**
   * View request details
   */
  viewRequest(requestId: number): void {
    this.router.navigate(['/accommodation/view', requestId]);
  }

  /**
   * Navigate back to overview
   */
  goToOverview(): void {
    this.router.navigate(['/admin/accommodation']);
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
    if (statusLower === 'confirmed') return 'badge-success';
    if (statusLower === 'pending') return 'badge-warning';
    return 'badge-secondary';
  }

  /**
   * Get location badge class
   */
  getLocationBadgeClass(location: string): string {
    switch (location) {
      case 'Ashgabat': return 'badge-blue';
      case 'Kiyanly': return 'badge-green';
      case 'Turkmenbashy': return 'badge-amber';
      default: return 'badge-gray';
    }
  }

  /**
   * Retry loading pending accommodations
   */
  retryPending(): void {
    this.fetchPendingAccommodations();
  }
}
