/**
 * Pure itinerary-leg parsing, flight-segment payload building, and
 * booking-form validation used by FlightsProcessingComponent.
 *
 * Split out of flights-processing.component.ts (see
 * docs/CODEBASE_REFACTOR_ROADMAP.md item 5) - a pure move, no logic
 * changed.
 */

export interface ItinerarySegment {
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

export interface FlightLegForm {
  flightNumber: string;
  departureAirport: string;
  arrivalAirport: string;
  departureDate: string;
  departureTime: string;
  arrivalDate: string;
  arrivalTime: string;
}

export interface FlightSegmentPayload {
  direction: 'OUTBOUND' | 'RETURN';
  sequence: number;
  flightNumber: string;
  departureAirport: string;
  arrivalAirport: string;
  departureDateTime: string;
  arrivalDateTime: string;
}

export function emptyLeg(): FlightLegForm {
  return {
    flightNumber: '',
    departureAirport: '',
    arrivalAirport: '',
    departureDate: '',
    departureTime: '',
    arrivalDate: '',
    arrivalTime: '',
  };
}

/** Format a date/date-string for input type="date" (YYYY-MM-DD). */
export function formatDateForInput(date: string | Date): string {
  if (!date) return '';
  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toISOString().split('T')[0];
  } catch {
    return '';
  }
}

/**
 * The TSR itinerary's ETD/ETA is free text (requestors can type "14:30"
 * or "Morning") - a native <input type="time"> silently drops anything
 * that isn't strict HH:MM, which is why it used to render empty even
 * though a value was set. Normalize real times, and translate the
 * common day-period labels to a representative clock time so the field
 * still starts pre-filled; admins can still edit it before confirming.
 */
export function parseItineraryTime(value?: string): string {
  if (!value) {
    return '';
  }
  const timeMatch = value.trim().match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
  if (timeMatch) {
    return `${timeMatch[1].padStart(2, '0')}:${timeMatch[2]}`;
  }
  const periodDefaults: Record<string, string> = {
    morning: '08:00',
    afternoon: '13:00',
    evening: '18:00',
    night: '21:00',
    noon: '12:00',
    midnight: '00:00',
  };
  return periodDefaults[value.trim().toLowerCase()] || '';
}

export function legFromSegment(segment: ItinerarySegment): FlightLegForm {
  const depDate = segment.departure_date || segment.date;
  const arrDate = segment.arrival_date || segment.date;
  return {
    flightNumber: '',
    departureAirport: segment.from_location || segment.from || '',
    arrivalAirport: segment.to_location || segment.to || '',
    departureDate: depDate ? formatDateForInput(depDate) : '',
    departureTime: parseItineraryTime(segment.etd),
    arrivalDate: arrDate ? formatDateForInput(arrDate) : '',
    arrivalTime: parseItineraryTime(segment.eta),
  };
}

/**
 * Splits an itinerary into Outbound/Return legs by grouping consecutive
 * segments that share the itinerary's first travel date (Outbound) vs.
 * every segment after that (Return) - itineraries don't carry an explicit
 * direction flag, so date-grouping is the best available signal.
 * `isRoundTrip` is passed in rather than recomputed here since it depends
 * on the same origin/destination comparison the caller (the component's
 * `isRoundTrip` getter) already makes against `selectedTrf`.
 */
export function splitItineraryByDirection(
  itinerary: ItinerarySegment[],
  isRoundTrip: boolean
): { outbound: ItinerarySegment[]; returning: ItinerarySegment[] } {
  if (!isRoundTrip) {
    return { outbound: itinerary, returning: [] };
  }
  const firstDate = itinerary[0]?.departure_date || itinerary[0]?.date;
  const outbound = itinerary.filter(s => (s.departure_date || s.date) === firstDate);
  const returning = itinerary.filter(s => (s.departure_date || s.date) !== firstDate);
  return { outbound: outbound.length ? outbound : [itinerary[0]], returning };
}

export function legToSegmentPayload(
  leg: FlightLegForm,
  direction: 'OUTBOUND' | 'RETURN',
  sequence: number
): FlightSegmentPayload {
  return {
    direction,
    sequence,
    flightNumber: leg.flightNumber,
    departureAirport: leg.departureAirport,
    arrivalAirport: leg.arrivalAirport,
    departureDateTime: leg.departureDate
      ? `${leg.departureDate}T${leg.departureTime || '00:00'}`
      : '',
    arrivalDateTime: leg.arrivalDate ? `${leg.arrivalDate}T${leg.arrivalTime || '00:00'}` : '',
  };
}

export function isLegValid(leg: FlightLegForm): boolean {
  return !!(
    leg.flightNumber &&
    leg.departureAirport &&
    leg.arrivalAirport &&
    leg.departureDate &&
    leg.departureTime &&
    leg.arrivalDate &&
    leg.arrivalTime
  );
}

export interface ValidationParams {
  pnr: string;
  airline: string;
  isAirlineRequired: boolean;
  eTicketFile: File | null;
  outboundLegs: FlightLegForm[];
  returnLegs: FlightLegForm[];
  isRoundTrip: boolean;
}

/**
 * Human-readable list of what's still missing, shown next to the
 * Confirm button so a disabled button is never a silent mystery.
 */
export function getValidationIssues(params: ValidationParams): string[] {
  const issues: string[] = [];
  if (!params.pnr) {
    issues.push('PNR / Booking Reference');
  }
  if (params.isAirlineRequired && !params.airline) {
    issues.push('Airline');
  }
  if (!params.eTicketFile) {
    issues.push('E-ticket upload');
  }
  params.outboundLegs.forEach((leg, i) => {
    if (!isLegValid(leg)) {
      issues.push(`Outbound leg ${i + 1}`);
    }
  });
  if (params.isRoundTrip && params.returnLegs.length === 0) {
    issues.push('At least one return leg');
  }
  params.returnLegs.forEach((leg, i) => {
    if (!isLegValid(leg)) {
      issues.push(`Return leg ${i + 1}`);
    }
  });
  return issues;
}

export function isFormValid(params: ValidationParams): boolean {
  return getValidationIssues(params).length === 0;
}

export function getTravelTypeBadgeClass(travelType: string): string {
  switch (travelType) {
    case 'Overseas':
      return 'badge-blue';
    case 'Home Leave':
      return 'badge-purple';
    case 'Domestic':
      return 'badge-green';
    default:
      return 'badge-gray';
  }
}

/** Extract a human-readable message from a Django REST Framework HTTP
 * error response, trying its various shapes in order. */
export function extractErrorMessage(err: unknown): string {
  const error = (err as { error?: unknown; message?: string })?.error;
  if (error) {
    if (typeof error === 'string') {
      return error;
    }
    const errObj = error as Record<string, unknown>;
    if (typeof errObj['error'] === 'string') {
      return errObj['error'];
    }
    if (typeof errObj['detail'] === 'string') {
      return errObj['detail'];
    }
    if (typeof errObj['message'] === 'string') {
      return errObj['message'];
    }
    if (Array.isArray(errObj['non_field_errors'])) {
      return (errObj['non_field_errors'] as unknown[]).join(', ');
    }
    const keys = Object.keys(errObj);
    if (keys.length > 0 && Array.isArray(errObj[keys[0]])) {
      return `${keys[0]}: ${(errObj[keys[0]] as unknown[]).join(', ')}`;
    }
  }
  const message = (err as { message?: string })?.message;
  if (message) {
    return message;
  }
  return 'An unexpected error occurred. Please try again.';
}
