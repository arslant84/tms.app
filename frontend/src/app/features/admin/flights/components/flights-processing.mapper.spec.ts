import {
  emptyLeg,
  formatDateForInput,
  parseItineraryTime,
  legFromSegment,
  splitItineraryByDirection,
  legToSegmentPayload,
  isLegValid,
  getValidationIssues,
  isFormValid,
  getTravelTypeBadgeClass,
  extractErrorMessage,
  ValidationParams,
} from './flights-processing.mapper';

describe('flights-processing.mapper', () => {
  describe('emptyLeg', () => {
    it('returns a leg with all fields blank', () => {
      expect(emptyLeg()).toEqual({
        flightNumber: '',
        departureAirport: '',
        arrivalAirport: '',
        departureDate: '',
        departureTime: '',
        arrivalDate: '',
        arrivalTime: '',
      });
    });
  });

  describe('formatDateForInput', () => {
    it('formats an ISO string as YYYY-MM-DD', () => {
      expect(formatDateForInput('2026-03-12T10:00:00Z')).toBe('2026-03-12');
    });

    it('returns empty string for falsy input', () => {
      expect(formatDateForInput('')).toBe('');
    });

    it('returns empty string for an unparseable date', () => {
      expect(formatDateForInput('not a date')).toBe('');
    });
  });

  describe('parseItineraryTime', () => {
    it('parses an HH:MM time', () => {
      expect(parseItineraryTime('14:30')).toBe('14:30');
    });

    it('zero-pads a single-digit hour', () => {
      expect(parseItineraryTime('4:30')).toBe('04:30');
    });

    it('translates named day-period labels', () => {
      expect(parseItineraryTime('Evening')).toBe('18:00');
      expect(parseItineraryTime('midnight')).toBe('00:00');
    });

    it('returns empty string for missing or unrecognized values', () => {
      expect(parseItineraryTime(undefined)).toBe('');
      expect(parseItineraryTime('gibberish')).toBe('');
    });
  });

  describe('legFromSegment', () => {
    it('maps a segment into a leg with pre-filled dates/times', () => {
      const leg = legFromSegment({
        from_location: 'KUL',
        to_location: 'SIN',
        departure_date: '2026-01-01',
        etd: '08:00',
        eta: 'Evening',
      });
      expect(leg.departureAirport).toBe('KUL');
      expect(leg.arrivalAirport).toBe('SIN');
      expect(leg.departureDate).toBe('2026-01-01');
      expect(leg.departureTime).toBe('08:00');
      expect(leg.arrivalTime).toBe('18:00');
      expect(leg.flightNumber).toBe('');
    });

    it('falls back to camelCase from/to fields', () => {
      const leg = legFromSegment({ from: 'KUL', to: 'SIN', date: '2026-01-01' });
      expect(leg.departureAirport).toBe('KUL');
      expect(leg.arrivalAirport).toBe('SIN');
      expect(leg.departureDate).toBe('2026-01-01');
    });
  });

  describe('splitItineraryByDirection', () => {
    const itinerary = [
      { from: 'KUL', to: 'SIN', date: '2026-01-01' },
      { from: 'SIN', to: 'KUL', date: '2026-01-05' },
    ];

    it('returns everything as outbound when not a round trip', () => {
      const result = splitItineraryByDirection(itinerary, false);
      expect(result.outbound.length).toBe(2);
      expect(result.returning.length).toBe(0);
    });

    it('splits by first-date grouping when a round trip', () => {
      const result = splitItineraryByDirection(itinerary, true);
      expect(result.outbound.length).toBe(1);
      expect(result.outbound[0].date).toBe('2026-01-01');
      expect(result.returning.length).toBe(1);
      expect(result.returning[0].date).toBe('2026-01-05');
    });
  });

  describe('legToSegmentPayload', () => {
    it('builds a payload with combined date+time, defaulting missing time to 00:00', () => {
      const leg = { ...emptyLeg(), departureDate: '2026-01-01', arrivalDate: '2026-01-02' };
      const payload = legToSegmentPayload(leg, 'OUTBOUND', 1);
      expect(payload.departureDateTime).toBe('2026-01-01T00:00');
      expect(payload.arrivalDateTime).toBe('2026-01-02T00:00');
      expect(payload.direction).toBe('OUTBOUND');
      expect(payload.sequence).toBe(1);
    });

    it('leaves date-times empty when no date is set', () => {
      const payload = legToSegmentPayload(emptyLeg(), 'RETURN', 2);
      expect(payload.departureDateTime).toBe('');
      expect(payload.arrivalDateTime).toBe('');
    });
  });

  describe('isLegValid', () => {
    it('requires every field to be filled', () => {
      expect(isLegValid(emptyLeg())).toBe(false);
      const full = {
        flightNumber: 'MH123',
        departureAirport: 'KUL',
        arrivalAirport: 'SIN',
        departureDate: '2026-01-01',
        departureTime: '08:00',
        arrivalDate: '2026-01-01',
        arrivalTime: '10:00',
      };
      expect(isLegValid(full)).toBe(true);
    });
  });

  describe('getValidationIssues / isFormValid', () => {
    const validLeg = {
      flightNumber: 'MH123',
      departureAirport: 'KUL',
      arrivalAirport: 'SIN',
      departureDate: '2026-01-01',
      departureTime: '08:00',
      arrivalDate: '2026-01-01',
      arrivalTime: '10:00',
    };

    const baseParams: ValidationParams = {
      pnr: 'ABC123',
      airline: '',
      isAirlineRequired: false,
      eTicketFile: new File([''], 'ticket.pdf'),
      outboundLegs: [validLeg],
      returnLegs: [],
      isRoundTrip: false,
    };

    it('is valid when all required fields are present', () => {
      expect(getValidationIssues(baseParams)).toEqual([]);
      expect(isFormValid(baseParams)).toBe(true);
    });

    it('flags a missing PNR, e-ticket, and invalid outbound leg', () => {
      const issues = getValidationIssues({
        ...baseParams,
        pnr: '',
        eTicketFile: null,
        outboundLegs: [emptyLeg()],
      });
      expect(issues).toContain('PNR / Booking Reference');
      expect(issues).toContain('E-ticket upload');
      expect(issues).toContain('Outbound leg 1');
      expect(isFormValid({ ...baseParams, pnr: '' })).toBe(false);
    });

    it('requires airline only when isAirlineRequired', () => {
      const issues = getValidationIssues({ ...baseParams, isAirlineRequired: true, airline: '' });
      expect(issues).toContain('Airline');
    });

    it('requires at least one return leg on a round trip', () => {
      const issues = getValidationIssues({ ...baseParams, isRoundTrip: true, returnLegs: [] });
      expect(issues).toContain('At least one return leg');
    });
  });

  describe('getTravelTypeBadgeClass', () => {
    it('maps known travel types to their badge class', () => {
      expect(getTravelTypeBadgeClass('Overseas')).toBe('badge-blue');
      expect(getTravelTypeBadgeClass('Domestic')).toBe('badge-green');
    });

    it('falls back to badge-gray for unknown types', () => {
      expect(getTravelTypeBadgeClass('External Parties')).toBe('badge-gray');
    });
  });

  describe('extractErrorMessage', () => {
    it('extracts a direct string error', () => {
      expect(extractErrorMessage({ error: 'Something broke' })).toBe('Something broke');
    });

    it('extracts { error: { detail } } DRF format', () => {
      expect(extractErrorMessage({ error: { detail: 'Not found' } })).toBe('Not found');
    });

    it('extracts { error: { non_field_errors } }', () => {
      expect(extractErrorMessage({ error: { non_field_errors: ['bad', 'request'] } })).toBe(
        'bad, request'
      );
    });

    it('extracts the first field error when no known key matches', () => {
      expect(extractErrorMessage({ error: { pnr: ['This field is required.'] } })).toBe(
        'pnr: This field is required.'
      );
    });

    it('falls back to err.message, then a generic message', () => {
      expect(extractErrorMessage({ message: 'Network error' })).toBe('Network error');
      expect(extractErrorMessage({})).toBe('An unexpected error occurred. Please try again.');
    });
  });
});
