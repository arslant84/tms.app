/**
 * Pure calendar-grid, date-formatting, and request/booking-mapping
 * helpers used by AccommodationProcessingComponent.
 *
 * Split out of accommodation-processing.component.ts (see
 * docs/CODEBASE_REFACTOR_ROADMAP.md item 4) - a pure move, no logic
 * changed. The request/booking-shape types and mapping functions below
 * are Phase 2's pure half (data transforms); the API-calling
 * orchestration (assign/reject/cancel) lives in
 * accommodation-processing.service.ts alongside them.
 */

import type { AccommodationBooking } from '../../../accommodation/services/accommodation.service';

export interface PendingAccommodation {
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

export interface BookedAccommodation {
  id: number;
  trf: number | null;
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

export interface BookingData {
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
export interface RawAccommodationAccom {
  location?: string;
  check_in_date?: string;
  checkInDate?: string;
  check_out_date?: string;
  checkOutDate?: string;
  room_type?: string;
  roomType?: string;
  gender?: string;
}

export interface RawAccommodationRequest {
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

/** All calendar days in the given month (0-indexed month, matching Date). */
export function calculateDaysInMonth(year: number, month: number): Date[] {
  const totalDays = new Date(year, month + 1, 0).getDate();
  const days: Date[] = [];
  for (let i = 1; i <= totalDays; i++) {
    days.push(new Date(year, month, i));
  }
  return days;
}

/** Slice of `days` visible at the current slider offset. */
export function getVisibleDays(days: Date[], offset: number, daysToShow: number): Date[] {
  return days.slice(offset, offset + daysToShow);
}

export function canSlidePrevious(offset: number): boolean {
  return offset > 0;
}

export function canSlideNext(offset: number, daysToShow: number, totalDays: number): boolean {
  return offset + daysToShow < totalDays;
}

export function computeSlidePreviousOffset(offset: number, daysToShow: number): number {
  return Math.max(0, offset - daysToShow);
}

export function computeSlideNextOffset(
  offset: number,
  daysToShow: number,
  totalDays: number
): number {
  return Math.min(totalDays - daysToShow, offset + daysToShow);
}

/** Format date for input type="date" (YYYY-MM-DD). */
export function formatDateForInput(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** Format date for display (readable format), e.g. "Jan 5, 2026". */
export function formatDateForDisplay(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(dateObj.getTime())) return 'Invalid Date';
  return dateObj.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

/** ISO date (YYYY-MM-DD) for API payloads and same-day comparison. */
export function formatDateForAPI(date: Date): string {
  return date.toISOString().split('T')[0];
}

/** Alias of formatDateForAPI kept separate to match the pre-split call
 * sites' own naming (booking-availability comparisons vs. API payloads). */
export function formatDateForComparison(date: Date): string {
  return date.toISOString().split('T')[0];
}

/** Number of nights between two YYYY-MM-DD strings, 0 if either is missing. */
export function calculateDays(checkInDate: string, checkOutDate: string): number {
  if (!checkInDate || !checkOutDate) return 0;
  const from = new Date(checkInDate);
  const to = new Date(checkOutDate);
  const diff = to.getTime() - from.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

/** Same computation as calculateDays, wrapped to never throw on bad input. */
export function calculateDuration(checkIn: string, checkOut: string): number {
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

export function getDayName(date: Date): string {
  return date.toLocaleDateString('en-US', { weekday: 'short' });
}

export function isWeekend(date: Date): boolean {
  const day = date.getDay();
  return day === 0 || day === 6;
}

/** First truthy value in `values`, or `fallback` if none - equivalent to
 * chaining `a || b || c || fallback` but pulls the decision points out of
 * the caller so its own cyclomatic complexity doesn't grow with every
 * fallback field added. */
export function firstTruthy(
  fallback: string,
  ...values: Array<string | number | null | undefined>
): string {
  const found = values.find(v => !!v);
  return found !== undefined ? String(found) : fallback;
}

export function getLocationBadgeClass(location: string): string {
  switch (location) {
    case 'Ashgabat':
      return 'badge-blue';
    case 'Kiyanly':
      return 'badge-green';
    case 'Turkmenbashy':
      return 'badge-amber';
    default:
      return 'badge-gray';
  }
}

/** Pull check-in/out dates out of whichever of the several shapes a raw
 * request happens to carry them in (see RawAccommodationRequest's own
 * doc comment) - 'N/A' if none are present. */
export function extractDates(req: RawAccommodationRequest): {
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

/** Map a raw request with status 'Approved' into the Pending Accommodations
 * tab's row shape. */
export function mapPendingAccommodation(req: RawAccommodationRequest): PendingAccommodation {
  const additionalData = req.additional_data || {};
  const firstAccom = (additionalData.accommodations || [])[0] || {};
  const { checkInDate, checkOutDate } = extractDates(req);
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
    duration: calculateDuration(checkInDate, checkOutDate),
    gender: firstTruthy('N/A', firstAccom.gender, additionalData.gender),
    trfId: req.trf || undefined,
    tsrDepartureDate: req.tsr_departure_date || '',
    tsrReturnDate: req.tsr_return_date || '',
  };
}

/** Map a raw request with status 'Accommodation Assigned' into the Booked
 * Accommodations tab's row shape. */
export function mapBookedAccommodation(req: RawAccommodationRequest): BookedAccommodation {
  const additionalData = req.additional_data || {};
  const firstAccom = (additionalData.accommodations || [])[0] || {};
  const { checkInDate, checkOutDate } = extractDates(req);
  return {
    id: req.id,
    trf: req.trf ?? null,
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
}

/** Map a raw AccommodationBooking (backend shape) into the calendar's own
 * BookingData row shape. */
export function mapBookingData(b: AccommodationBooking): BookingData {
  return {
    id: b.id,
    staff_house_id: b.staff_house,
    room_id: b.room,
    date: b.date,
    status: b.status,
    guest_name: b.staff_name,
    trf_id: b.trf,
    notes: b.notes,
  };
}

/** True if `roomId` has no non-cancelled booking on any night between
 * `from`/`to` inclusive (or always true if either bound is unset). */
export function isRoomAvailableForDates(
  roomId: number,
  from: Date | null,
  to: Date | null,
  bookings: BookingData[]
): boolean {
  if (!from || !to) return true;

  const currentDate = new Date(from);
  const endDate = new Date(to);

  while (currentDate <= endDate) {
    const dateStr = formatDateForComparison(currentDate);
    const isBooked = bookings.some(
      b =>
        b.room_id === roomId &&
        formatDateForComparison(new Date(b.date)) === dateStr &&
        b.status !== 'Cancelled'
    );
    if (isBooked) return false;
    currentDate.setDate(currentDate.getDate() + 1);
  }

  return true;
}

/** Booking-info lookup for a single calendar cell (date + room). */
export function getDateBookingInfo(
  date: Date,
  roomId: number,
  bookings: BookingData[]
): { isOccupied: boolean; status: string | null; guestName: string | null } {
  const dateStr = formatDateForComparison(date);
  const booking = bookings.find(
    b =>
      b.room_id === roomId &&
      formatDateForComparison(new Date(b.date)) === dateStr &&
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

/** Validate assignRoom's date inputs: check-out not before check-in, and -
 * when the request is TSR-linked - both dates within the TSR's travel
 * window. Returns a user-facing error message, or null if valid. Pulled
 * out of assignRoom to make this branchy validation independently
 * testable without Angular DI/HttpClient. */
export function validateAssignmentDates(
  checkIn: Date,
  checkOut: Date,
  hasTsrReference: boolean,
  tsrMinDate: string,
  tsrMaxDate: string
): string | null {
  // Allow same-day checkout (checkOut == checkIn is valid)
  if (checkOut < checkIn) {
    return 'Check-out date cannot be before check-in date';
  }

  if (hasTsrReference && tsrMinDate && tsrMaxDate) {
    const tsrMin = new Date(tsrMinDate);
    const tsrMax = new Date(tsrMaxDate);

    if (checkIn < tsrMin || checkIn > tsrMax) {
      return `Check-in date must be within TSR travel dates (${formatDateForDisplay(tsrMin)} - ${formatDateForDisplay(tsrMax)})`;
    }

    if (checkOut < tsrMin || checkOut > tsrMax) {
      return `Check-out date must be within TSR travel dates (${formatDateForDisplay(tsrMin)} - ${formatDateForDisplay(tsrMax)})`;
    }

    if (checkOut > tsrMax) {
      return `Check-out date cannot be after TSR return date (${formatDateForDisplay(tsrMax)})`;
    }
  }

  return null;
}
