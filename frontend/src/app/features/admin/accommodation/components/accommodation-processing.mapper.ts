/**
 * Pure calendar-grid and date-formatting helpers used by
 * AccommodationProcessingComponent's booking calendar.
 *
 * Split out of accommodation-processing.component.ts (see
 * docs/CODEBASE_REFACTOR_ROADMAP.md item 4) - a pure move, no logic
 * changed.
 */

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
