import {
  deriveTripTypeFromItinerary,
  extractPassportFileInfo,
  formatDateForAPI,
  parseTimeOfDayMinutes,
  transformAdvanceAmounts,
  transformBankDetails,
  transformExternalPartiesItineraryData,
  transformItineraryData,
  transformMealSelectionsData,
  transformPassportDetails,
} from './trf-data-mapper';

describe('trf-data-mapper', () => {
  describe('formatDateForAPI', () => {
    it('formats a Date object as YYYY-MM-DD', () => {
      expect(formatDateForAPI(new Date(2026, 0, 5))).toBe('2026-01-05');
    });

    it('formats an ISO string', () => {
      expect(formatDateForAPI('2026-03-12T10:00:00Z')).toBe('2026-03-12');
    });

    it('returns empty string for falsy input', () => {
      expect(formatDateForAPI(null)).toBe('');
      expect(formatDateForAPI(undefined)).toBe('');
      expect(formatDateForAPI('')).toBe('');
    });

    it('returns empty string for an invalid date', () => {
      expect(formatDateForAPI('not a date')).toBe('');
    });
  });

  describe('parseTimeOfDayMinutes', () => {
    it('parses an HH:MM time', () => {
      expect(parseTimeOfDayMinutes('14:30')).toBe(14 * 60 + 30);
    });

    it('falls back to a named period', () => {
      expect(parseTimeOfDayMinutes('Evening')).toBe(18 * 60);
      expect(parseTimeOfDayMinutes('midnight')).toBe(0);
    });

    it('defaults to noon for missing or unrecognized values', () => {
      expect(parseTimeOfDayMinutes(undefined)).toBe(12 * 60);
      expect(parseTimeOfDayMinutes('gibberish')).toBe(12 * 60);
    });
  });

  describe('deriveTripTypeFromItinerary', () => {
    it('returns One Way for fewer than 2 segments', () => {
      expect(deriveTripTypeFromItinerary([], 'from', 'to', 'date')).toBe('One Way');
      expect(
        deriveTripTypeFromItinerary(
          [{ from: 'A', to: 'B', date: '2026-01-01' }],
          'from',
          'to',
          'date'
        )
      ).toBe('One Way');
    });

    it('returns Round Trip when the last leg returns to the first leg origin', () => {
      const itinerary = [
        { from: 'KUL', to: 'SIN', date: '2026-01-01', etd: '08:00' },
        { from: 'SIN', to: 'KUL', date: '2026-01-05', etd: '18:00' },
      ];
      expect(deriveTripTypeFromItinerary(itinerary, 'from', 'to', 'date')).toBe('Round Trip');
    });

    it('returns One Way for a genuine multi-city trip', () => {
      const itinerary = [
        { from: 'KUL', to: 'SIN', date: '2026-01-01' },
        { from: 'SIN', to: 'BKK', date: '2026-01-05' },
      ];
      expect(deriveTripTypeFromItinerary(itinerary, 'from', 'to', 'date')).toBe('One Way');
    });

    it('sorts out-of-array-order segments by date before deriving trip type', () => {
      // Second leg appears first in the array but is dated later - the
      // derivation must sort by date, not trust array order (see the
      // function's own comment about the since-fixed race condition).
      const itinerary = [
        { from: 'SIN', to: 'KUL', date: '2026-01-05' },
        { from: 'KUL', to: 'SIN', date: '2026-01-01' },
      ];
      expect(deriveTripTypeFromItinerary(itinerary, 'from', 'to', 'date')).toBe('Round Trip');
    });
  });

  describe('transformItineraryData', () => {
    it('prefers snake_case backend fields over camelCase aliases', () => {
      const result = transformItineraryData([
        {
          segment_date: '2026-01-01',
          date: '2099-01-01',
          from_location: 'KUL',
          from: 'wrong',
          to_location: 'SIN',
          flight_number: 'MH123',
        },
      ]);
      expect(result[0]).toEqual(
        jasmine.objectContaining({
          date: '2026-01-01',
          from: 'KUL',
          to: 'SIN',
          flightNumber: 'MH123',
        })
      );
    });

    it('falls back to camelCase fields when snake_case is absent', () => {
      const result = transformItineraryData([
        { date: '2026-02-02', from: 'KUL', to: 'SIN', flightNumber: 'AK456' },
      ]);
      expect(result[0]).toEqual(
        jasmine.objectContaining({
          date: '2026-02-02',
          from: 'KUL',
          to: 'SIN',
          flightNumber: 'AK456',
        })
      );
    });
  });

  describe('transformExternalPartiesItineraryData', () => {
    it('maps backend fields to External Parties field names', () => {
      const result = transformExternalPartiesItineraryData([
        {
          segment_date: '2026-01-01',
          from_location: 'KUL',
          to_location: 'SIN',
          mode_of_transport: 'Flight',
        },
      ]);
      expect(result[0]).toEqual(
        jasmine.objectContaining({
          departureDate: '2026-01-01',
          departureLocation: 'KUL',
          arrivalLocation: 'SIN',
          modeOfTransport: 'Flight',
        })
      );
    });
  });

  describe('transformMealSelectionsData', () => {
    it('coerces boolean-like values from string/number to real booleans', () => {
      const result = transformMealSelectionsData([
        {
          meal_date: '2026-01-01',
          breakfast: 'true',
          lunch: 1,
          dinner: false,
          supper: 0,
          refreshment: true,
        },
      ]);
      expect(result[0]).toEqual({
        date: '2026-01-01',
        breakfast: true,
        lunch: true,
        dinner: false,
        supper: false,
        refreshment: true,
      });
    });
  });

  describe('transformBankDetails', () => {
    it('returns blank defaults for missing/empty input', () => {
      expect(transformBankDetails(null)).toEqual({
        bankName: '',
        accountNumber: '',
        accountName: '',
        branchAddress: '',
        currency: 'USD',
      });
      expect(transformBankDetails({})).toEqual({
        bankName: '',
        accountNumber: '',
        accountName: '',
        branchAddress: '',
        currency: 'USD',
      });
    });

    it('prefers snake_case over camelCase', () => {
      const result = transformBankDetails({ bank_name: 'First National Bank', bankName: 'wrong' });
      expect(result.bankName).toBe('First National Bank');
    });
  });

  describe('transformAdvanceAmounts', () => {
    it('returns an empty array for missing/empty input', () => {
      expect(transformAdvanceAmounts([])).toEqual([]);
    });

    it('maps every numeric field with a zero default', () => {
      const result = transformAdvanceAmounts([
        { date_from: '2026-01-01', date_to: '2026-01-05', lh: 10 },
      ]);
      expect(result[0]).toEqual({
        dateFrom: '2026-01-01',
        dateTo: '2026-01-05',
        lh: 10,
        ma: 0,
        oa: 0,
        tr: 0,
        oe: 0,
        usd: 0,
        remarks: '',
      });
    });
  });

  describe('extractPassportFileInfo', () => {
    it('returns blank file info for missing input', () => {
      expect(extractPassportFileInfo(null)).toEqual({ file: null, fileName: '', fileUrl: '' });
      expect(extractPassportFileInfo([])).toEqual({ file: null, fileName: '', fileUrl: '' });
    });

    it('extracts the file name from the URL for a single object', () => {
      const result = extractPassportFileInfo({
        passport_file_url: 'https://example.com/passports/john-doe.pdf',
      });
      expect(result.fileUrl).toBe('https://example.com/passports/john-doe.pdf');
      expect(result.fileName).toBe('john-doe.pdf');
    });

    it('takes the first element when given an array', () => {
      const result = extractPassportFileInfo([{ passport_file_url: 'https://example.com/a.pdf' }]);
      expect(result.fileName).toBe('a.pdf');
    });
  });

  describe('transformPassportDetails', () => {
    it('returns blank defaults for missing input', () => {
      expect(transformPassportDetails(null)).toEqual({
        fullName: '',
        passportNumber: '',
        nationality: '',
        dateOfBirth: null,
        placeOfBirth: '',
        passportIssueDate: null,
        passportExpiryDate: null,
      });
    });

    it('reads the first element when given an array', () => {
      const result = transformPassportDetails([
        { full_name: 'Jane Doe', passport_number: 'A1234567', nationality: 'Malaysian' },
      ]);
      expect(result.fullName).toBe('Jane Doe');
      expect(result.passportNumber).toBe('A1234567');
      expect(result.nationality).toBe('Malaysian');
    });

    it('reads a single object directly', () => {
      const result = transformPassportDetails({ fullName: 'John Doe', passportNumber: 'B7654321' });
      expect(result.fullName).toBe('John Doe');
      expect(result.passportNumber).toBe('B7654321');
    });
  });
});
