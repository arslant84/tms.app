import {
  calculateDaysInMonth,
  getVisibleDays,
  canSlidePrevious,
  canSlideNext,
  computeSlidePreviousOffset,
  computeSlideNextOffset,
  formatDateForInput,
  formatDateForDisplay,
  formatDateForAPI,
  formatDateForComparison,
  calculateDays,
  calculateDuration,
  getDayName,
  isWeekend,
  getLocationBadgeClass,
  extractDates,
  mapPendingAccommodation,
  mapBookedAccommodation,
  mapBookingData,
  isRoomAvailableForDates,
  getDateBookingInfo,
  validateAssignmentDates,
  type BookingData,
  type RawAccommodationRequest,
} from './accommodation-processing.mapper';
import type { AccommodationBooking } from '../../../accommodation/services/accommodation.service';

describe('accommodation-processing.mapper', () => {
  describe('calculateDaysInMonth', () => {
    it('returns one Date per day in the month', () => {
      const days = calculateDaysInMonth(2026, 1); // February 2026 (0-indexed month)
      expect(days.length).toBe(28);
      expect(days[0].getDate()).toBe(1);
      expect(days[27].getDate()).toBe(28);
    });

    it('handles a 31-day month', () => {
      const days = calculateDaysInMonth(2026, 0); // January
      expect(days.length).toBe(31);
    });
  });

  describe('getVisibleDays', () => {
    it('slices the days array at the given offset/window', () => {
      const days = calculateDaysInMonth(2026, 0);
      const visible = getVisibleDays(days, 4, 16);
      expect(visible.length).toBe(16);
      expect(visible[0].getDate()).toBe(5);
    });
  });

  describe('canSlidePrevious / canSlideNext', () => {
    it('canSlidePrevious is false at offset 0, true otherwise', () => {
      expect(canSlidePrevious(0)).toBe(false);
      expect(canSlidePrevious(16)).toBe(true);
    });

    it('canSlideNext is true while offset + window < totalDays', () => {
      expect(canSlideNext(0, 16, 31)).toBe(true);
      expect(canSlideNext(16, 16, 31)).toBe(false);
    });
  });

  describe('computeSlidePreviousOffset / computeSlideNextOffset', () => {
    it('never goes below 0', () => {
      expect(computeSlidePreviousOffset(10, 16)).toBe(0);
      expect(computeSlidePreviousOffset(20, 16)).toBe(4);
    });

    it('never exceeds totalDays - daysToShow', () => {
      expect(computeSlideNextOffset(0, 16, 31)).toBe(15);
      expect(computeSlideNextOffset(20, 16, 31)).toBe(15);
    });
  });

  describe('formatDateForInput', () => {
    it('formats as YYYY-MM-DD with zero-padding', () => {
      expect(formatDateForInput(new Date(2026, 0, 5))).toBe('2026-01-05');
    });
  });

  describe('formatDateForDisplay', () => {
    it('formats a Date object as a short readable date', () => {
      expect(formatDateForDisplay(new Date(2026, 0, 5))).toBe('Jan 5, 2026');
    });

    it('accepts an ISO string', () => {
      expect(formatDateForDisplay('2026-01-05T00:00:00Z')).toContain('2026');
    });

    it('returns "Invalid Date" for unparseable input', () => {
      expect(formatDateForDisplay('not a date')).toBe('Invalid Date');
    });
  });

  describe('formatDateForAPI / formatDateForComparison', () => {
    it('both format as the ISO date portion', () => {
      const date = new Date('2026-03-12T10:00:00Z');
      expect(formatDateForAPI(date)).toBe('2026-03-12');
      expect(formatDateForComparison(date)).toBe('2026-03-12');
    });
  });

  describe('calculateDays', () => {
    it('returns 0 when either date is missing', () => {
      expect(calculateDays('', '2026-01-05')).toBe(0);
      expect(calculateDays('2026-01-05', '')).toBe(0);
    });

    it('returns the number of nights between two dates', () => {
      expect(calculateDays('2026-01-01', '2026-01-05')).toBe(4);
    });
  });

  describe('calculateDuration', () => {
    it('returns 0 when either date is missing', () => {
      expect(calculateDuration('', '2026-01-05')).toBe(0);
    });

    it('returns the number of nights between two dates', () => {
      expect(calculateDuration('2026-01-01', '2026-01-05')).toBe(4);
    });
  });

  describe('getDayName', () => {
    it('returns the short weekday name', () => {
      // 2026-01-05 is a Monday
      expect(getDayName(new Date(2026, 0, 5))).toBe('Mon');
    });
  });

  describe('isWeekend', () => {
    it('identifies Saturday and Sunday as weekend', () => {
      expect(isWeekend(new Date(2026, 0, 3))).toBe(true); // Saturday
      expect(isWeekend(new Date(2026, 0, 4))).toBe(true); // Sunday
      expect(isWeekend(new Date(2026, 0, 5))).toBe(false); // Monday
    });
  });

  describe('getLocationBadgeClass', () => {
    it('maps known locations to their badge class', () => {
      expect(getLocationBadgeClass('Ashgabat')).toBe('badge-blue');
      expect(getLocationBadgeClass('Kiyanly')).toBe('badge-green');
      expect(getLocationBadgeClass('Turkmenbashy')).toBe('badge-amber');
    });

    it('falls back to badge-gray for unknown locations', () => {
      expect(getLocationBadgeClass('Somewhere Else')).toBe('badge-gray');
    });
  });

  describe('extractDates', () => {
    it('returns N/A for both dates when nothing is present', () => {
      expect(extractDates({ id: 1 })).toEqual({ checkInDate: 'N/A', checkOutDate: 'N/A' });
    });

    it('prefers additional_data.accommodations[0] over other shapes', () => {
      const req: RawAccommodationRequest = {
        id: 1,
        check_in_date: '2026-01-01',
        additional_data: {
          check_in_date: '2026-02-01',
          accommodations: [{ check_in_date: '2026-03-01' }],
        },
      };
      expect(extractDates(req).checkInDate).toBe('2026-03-01');
    });

    it('falls back through the shape chain when earlier ones are absent', () => {
      const req: RawAccommodationRequest = {
        id: 1,
        requested_check_in_date: '2026-04-01',
      };
      expect(extractDates(req).checkInDate).toBe('2026-04-01');
    });
  });

  describe('mapPendingAccommodation', () => {
    it('maps a raw request into the Pending tab row shape', () => {
      const req: RawAccommodationRequest = {
        id: 5,
        request_number: 'ACC-5',
        requestor_name: 'Jane Doe',
        department: 'IT',
        staff_id: 'S001',
        status: 'Approved',
        trf: 42,
        tsr_departure_date: '2026-01-01',
        tsr_return_date: '2026-01-05',
        additional_data: {
          location: 'Ashgabat',
          check_in_date: '2026-01-01',
          check_out_date: '2026-01-05',
          room_type: 'Single',
        },
      };
      const result = mapPendingAccommodation(req);
      expect(result.id).toBe(5);
      expect(result.requestorName).toBe('Jane Doe');
      expect(result.location).toBe('Ashgabat');
      expect(result.duration).toBe(4);
      expect(result.trfId).toBe(42);
    });

    it('falls back to defaults for missing fields', () => {
      const result = mapPendingAccommodation({ id: 7 });
      expect(result.request_number).toBe('ACC-7');
      expect(result.requestorName).toBe('N/A');
      expect(result.roomType).toBe('Any');
      expect(result.trfId).toBeUndefined();
    });
  });

  describe('mapBookedAccommodation', () => {
    it('maps a raw request into the Booked tab row shape', () => {
      const req: RawAccommodationRequest = {
        id: 8,
        trf: 10,
        request_number: 'ACC-8',
        requestor_name: 'John Smith',
        status: 'Accommodation Assigned',
        additional_comments: 'VIP guest',
      };
      const result = mapBookedAccommodation(req);
      expect(result.trf).toBe(10);
      expect(result.requestNumber).toBe('ACC-8');
      expect(result.staffHouseName).toBe('Not assigned');
      expect(result.notes).toBe('VIP guest');
    });

    it('defaults trf to null when absent', () => {
      expect(mapBookedAccommodation({ id: 9 }).trf).toBeNull();
    });
  });

  describe('mapBookingData', () => {
    it('maps a raw AccommodationBooking into the calendar row shape', () => {
      const booking = {
        id: 1,
        staff_house: 2,
        room: 3,
        date: '2026-01-01',
        status: 'Confirmed',
        staff_name: 'Jane Doe',
        trf: 42,
        notes: 'note',
      } as AccommodationBooking;
      expect(mapBookingData(booking)).toEqual({
        id: 1,
        staff_house_id: 2,
        room_id: 3,
        date: '2026-01-01',
        status: 'Confirmed',
        guest_name: 'Jane Doe',
        trf_id: 42,
        notes: 'note',
      });
    });
  });

  describe('isRoomAvailableForDates', () => {
    const bookings: BookingData[] = [
      { id: 1, staff_house_id: 1, room_id: 5, date: '2026-01-02', status: 'Confirmed' },
      { id: 2, staff_house_id: 1, room_id: 5, date: '2026-01-03', status: 'Cancelled' },
    ];

    it('is always available when either bound is unset', () => {
      expect(isRoomAvailableForDates(5, null, new Date(2026, 0, 5), bookings)).toBe(true);
      expect(isRoomAvailableForDates(5, new Date(2026, 0, 1), null, bookings)).toBe(true);
    });

    it('is unavailable when a non-cancelled booking falls within the range', () => {
      expect(isRoomAvailableForDates(5, new Date(2026, 0, 1), new Date(2026, 0, 3), bookings)).toBe(
        false
      );
    });

    it('ignores cancelled bookings', () => {
      expect(isRoomAvailableForDates(5, new Date(2026, 0, 3), new Date(2026, 0, 3), bookings)).toBe(
        true
      );
    });

    it('is available when no booking matches the room', () => {
      expect(
        isRoomAvailableForDates(99, new Date(2026, 0, 1), new Date(2026, 0, 5), bookings)
      ).toBe(true);
    });
  });

  describe('getDateBookingInfo', () => {
    const bookings: BookingData[] = [
      {
        id: 1,
        staff_house_id: 1,
        room_id: 5,
        date: '2026-01-02',
        status: 'Confirmed',
        guest_name: 'Jane Doe',
      },
    ];

    it('reports occupied with guest name for a matching booking', () => {
      expect(getDateBookingInfo(new Date(2026, 0, 2), 5, bookings)).toEqual({
        isOccupied: true,
        status: 'Confirmed',
        guestName: 'Jane Doe',
      });
    });

    it('reports unoccupied for a date/room with no booking', () => {
      expect(getDateBookingInfo(new Date(2026, 0, 3), 5, bookings)).toEqual({
        isOccupied: false,
        status: null,
        guestName: null,
      });
    });
  });

  describe('validateAssignmentDates', () => {
    it('rejects check-out before check-in', () => {
      const result = validateAssignmentDates(
        new Date(2026, 0, 5),
        new Date(2026, 0, 1),
        false,
        '',
        ''
      );
      expect(result).toContain('Check-out date cannot be before check-in date');
    });

    it('allows same-day checkout', () => {
      const date = new Date(2026, 0, 1);
      expect(validateAssignmentDates(date, date, false, '', '')).toBeNull();
    });

    it('passes without TSR constraints', () => {
      expect(
        validateAssignmentDates(new Date(2026, 0, 1), new Date(2026, 0, 5), false, '', '')
      ).toBeNull();
    });

    it('rejects check-in before the TSR travel window', () => {
      const result = validateAssignmentDates(
        new Date(2025, 11, 25),
        new Date(2026, 0, 5),
        true,
        '2026-01-01',
        '2026-01-10'
      );
      expect(result).toContain('Check-in date must be within TSR travel dates');
    });

    it('rejects check-out after the TSR travel window', () => {
      const result = validateAssignmentDates(
        new Date(2026, 0, 2),
        new Date(2026, 0, 15),
        true,
        '2026-01-01',
        '2026-01-10'
      );
      expect(result).toContain('Check-out date must be within TSR travel dates');
    });

    it('passes when both dates are within the TSR travel window', () => {
      const result = validateAssignmentDates(
        new Date(2026, 0, 2),
        new Date(2026, 0, 5),
        true,
        '2026-01-01',
        '2026-01-10'
      );
      expect(result).toBeNull();
    });
  });
});
