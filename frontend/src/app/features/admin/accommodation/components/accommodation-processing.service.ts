import { inject, Injectable } from '@angular/core';
import { firstValueFrom, map, type Observable } from 'rxjs';
import {
  AccommodationService,
  type AccommodationBooking,
  type AccommodationRoom,
  type AccommodationStaffHouse,
} from '../../../accommodation/services/accommodation.service';
import {
  mapBookedAccommodation,
  mapBookingData,
  mapPendingAccommodation,
  type BookedAccommodation,
  type BookingData,
  type PendingAccommodation,
  type RawAccommodationRequest,
} from './accommodation-processing.mapper';

/**
 * Data/orchestration layer for AccommodationProcessingComponent's
 * requests-list loading, room assignment, no-rooms rejection, and
 * booking cancellation - Phase 2 of the component's size refactor (see
 * docs/CODEBASE_REFACTOR_ROADMAP.md item 4). Talks to AccommodationService
 * directly, so - like TrfSubmissionService - this is a real injectable
 * service, not a plain module; the component still owns toasts,
 * confirmation dialogs, `isProcessing`/`selectedRequest` state, and
 * navigation, which are UI orchestration, not data operations.
 */
@Injectable({ providedIn: 'root' })
export class AccommodationProcessingService {
  private accommodationService = inject(AccommodationService);

  /** Fetch every accommodation request (admin view) and split it into the
   * Pending ('Approved') and Booked ('Accommodation Assigned') tab lists. */
  loadRequests(): Observable<{
    pending: PendingAccommodation[];
    booked: BookedAccommodation[];
  }> {
    return this.accommodationService.getAllRequests({ adminView: true, page_size: 1000 }).pipe(
      map((response: RawAccommodationRequest[] | { results: RawAccommodationRequest[] }) => {
        const requests: RawAccommodationRequest[] = Array.isArray(response)
          ? response
          : response.results;

        return {
          pending: requests.filter(req => req.status === 'Approved').map(mapPendingAccommodation),
          booked: requests
            .filter(req => req.status === 'Accommodation Assigned')
            .map(mapBookedAccommodation),
        };
      })
    );
  }

  fetchStaffHouses(): Observable<AccommodationStaffHouse[]> {
    return this.accommodationService.getAllStaffHouses();
  }

  fetchRooms(staffHouseId?: number): Observable<AccommodationRoom[]> {
    return this.accommodationService.getAllRooms(staffHouseId);
  }

  /** Fetch bookings and map them into the calendar's own row shape. For
   * now fetches all bookings - in production you'd filter by month. */
  fetchBookings(): Observable<BookingData[]> {
    // Cast to a union with the defensive paginated shape, same reasoning
    // as fetchRelatedBookings below - AccommodationService.getAllBookings()'s
    // declared return type is a bare array, but the pre-extraction inline
    // code guarded against a paginated `{results}` response at runtime too.
    const bookings$ = this.accommodationService.getAllBookings({}) as Observable<
      AccommodationBooking[] | { results?: AccommodationBooking[] }
    >;
    return bookings$.pipe(
      map(bookings => {
        const bookingsList: AccommodationBooking[] = Array.isArray(bookings)
          ? bookings
          : bookings.results || [];
        return bookingsList.map(mapBookingData);
      })
    );
  }

  assignRoom(
    requestId: number,
    assignmentData: {
      staff_house: number;
      room: number;
      start_date: string;
      end_date: string;
      notes?: string;
      assigned_room_info: string;
    }
  ): Observable<{ message?: string }> {
    return this.accommodationService.assignAccommodation(requestId, assignmentData);
  }

  rejectNoRoomsAvailable(requestId: number): Observable<unknown> {
    return this.accommodationService.rejectRequest(
      requestId,
      'No rooms available for requested dates and location. Request rejected by Accommodation Admin.'
    );
  }

  /**
   * Fetch confirmed bookings and filter to the ones matching this
   * accommodation's underlying TRF - the lookup half of "Cancel
   * Booking"'s first phase. Kept separate from deleteBookings() so the
   * component can show a distinct error toast ("...for cancellation") if
   * this specific step fails, exactly matching the original inline flow.
   *
   * Matched by the underlying TRF id (both AccommodationRequest and
   * AccommodationBooking carry a `trf` FK to the same TravelRequest) -
   * previously compared against booking.id (the AccommodationRequest's
   * own id, a different id space), which never matched, so no booking
   * record was ever actually deleted - the room stayed reserved even
   * after "Cancel Booking" reported success (see this session's live QA
   * fix). Kept exactly as fixed - do not revert this comparison.
   */
  async fetchRelatedBookings(booking: BookedAccommodation): Promise<AccommodationBooking[]> {
    // Cast to a union with the defensive paginated shape - see
    // fetchBookings()'s doc comment above for why.
    const bookings = (await firstValueFrom(
      this.accommodationService.getAllBookings({ status: 'Confirmed' })
    )) as AccommodationBooking[] | { results?: AccommodationBooking[] };
    const bookingsList: AccommodationBooking[] = Array.isArray(bookings)
      ? bookings
      : bookings.results || [];
    return bookingsList.filter(b => booking.trf != null && b.trf === booking.trf);
  }

  /** Delete each of the given booking records - second half of "Cancel
   * Booking"'s first phase. A failure here shows a different error toast
   * than fetchRelatedBookings' failure (see that method's doc comment). */
  async deleteBookings(bookings: AccommodationBooking[]): Promise<void> {
    await Promise.all(
      bookings.map(b => firstValueFrom(this.accommodationService.deleteBooking(b.id)))
    );
  }

  /**
   * Second phase of "Cancel Booking": flip the AccommodationRequest's
   * status back to 'Approved' once its bookings are deleted. The
   * original inline flow swallowed a failure here silently (no error
   * toast, just stopping the processing spinner) - a pre-existing quirk,
   * preserved as-is rather than "fixed" during this extraction.
   */
  restoreApprovedStatus(booking: BookedAccommodation): Promise<unknown> {
    return firstValueFrom(
      this.accommodationService.updateRequest(booking.id, { status: 'Approved' })
    );
  }
}
