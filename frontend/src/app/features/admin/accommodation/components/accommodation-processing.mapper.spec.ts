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
} from './accommodation-processing.mapper';

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
});
