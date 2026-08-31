import type { DailyMealSelection } from '../../../../shared/components/meal-provision/meal-provision.component';
import type { PassportUploadDetails } from '../domestic-travel-details/domestic-travel-details.component';
import type {
  AdvanceBankDetails,
  AdvanceAmountItem,
} from '../overseas-travel-details/overseas-travel-details.component';
import type {
  NestedItineraryRow,
  RawMealRow,
  RawBankDetailRow,
  RawAdvanceAmountRow,
  RawPassportRow,
} from './trf-wizard.types';

/**
 * Pure backend<->component data transformation for the TRF wizard. Phase 2
 * of the trf-wizard.component.ts size refactor (see
 * docs/TRF_WIZARD_REFACTOR_ROADMAP.md) - none of these depend on component
 * state, so they're plain exported functions rather than injectable service
 * methods.
 */

/**
 * Convert Date object or ISO string to YYYY-MM-DD format
 */
export function formatDateForAPI(date: string | Date | null | undefined): string {
  if (!date) return '';

  const dateObj = typeof date === 'string' ? new Date(date) : date;

  if (!(dateObj instanceof Date) || Number.isNaN(dateObj.getTime())) {
    return '';
  }

  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, '0');
  const day = String(dateObj.getDate()).padStart(2, '0');

  return `${year}-${month}-${day}`;
}

/**
 * ETD/ETA on an itinerary segment is free text - a real "HH:MM" or a
 * vague day-period label ("Morning", "Evening", etc., see the create
 * form's placeholder). Mirrors flights-processing.component.ts's
 * parseItineraryTime: normalizes what it can, falls back to the middle
 * of the day for anything unparseable so same-day legs still sort in a
 * sensible order instead of colliding.
 */
export function parseTimeOfDayMinutes(value?: string): number {
  if (!value) {
    return 12 * 60;
  }
  const timeMatch = value.trim().match(/^(\d{1,2}):(\d{2})/);
  if (timeMatch) {
    return Number(timeMatch[1]) * 60 + Number(timeMatch[2]);
  }
  const periodMinutes: Record<string, number> = {
    morning: 8 * 60,
    afternoon: 13 * 60,
    evening: 18 * 60,
    night: 21 * 60,
    noon: 12 * 60,
    midnight: 0,
  };
  return periodMinutes[value.trim().toLowerCase()] ?? 12 * 60;
}

/**
 * Trip type ("One Way" vs "Round Trip") is never actually persisted to the
 * backend - the create wizard's own dropdown drives the itinerary editor's
 * add/remove-segment gating locally, but nothing sends or stores that
 * choice server-side (no model field, no serializer field). So on reopen,
 * data.trip_type/data.tripType is always undefined and every TRF silently
 * reset to whatever hardcoded default the caller passed, regardless of
 * what the requestor originally picked.
 *
 * Instead of adding a redundant field that could drift from the real
 * itinerary, derive it the same way flights-processing.component.ts's
 * isRoundTrip getter already does: a round trip's last leg lands back
 * where the first leg started.
 */
export function deriveTripTypeFromItinerary(
  itinerary: Array<Record<string, unknown>>,
  originKey: string,
  destinationKey: string,
  dateKey: string,
  timeKey: string = 'etd'
): 'One Way' | 'Round Trip' {
  if (!itinerary || itinerary.length < 2) {
    return 'One Way';
  }
  // Sort by date (then time-of-day) rather than trusting array order:
  // itinerary segments created before a since-fixed race condition
  // (concurrent, unawaited creation requests) can still be stored with an
  // id order that doesn't match their actual date order - and same-day
  // multi-city legs need the time to disambiguate at all.
  const sorted = [...itinerary]
    .map((segment, index) => ({ segment, index }))
    .sort((a, b) => {
      const dateA = a.segment?.[dateKey] || '';
      const dateB = b.segment?.[dateKey] || '';
      if (dateA !== dateB) {
        return dateA < dateB ? -1 : 1;
      }
      const minutesA = parseTimeOfDayMinutes(a.segment?.[timeKey] as string | undefined);
      const minutesB = parseTimeOfDayMinutes(b.segment?.[timeKey] as string | undefined);
      if (minutesA !== minutesB) {
        return minutesA - minutesB;
      }
      return a.index - b.index;
    })
    .map(({ segment }) => segment);
  const origin = sorted[0]?.[originKey];
  const finalDestination = sorted[sorted.length - 1]?.[destinationKey];
  return origin && finalDestination && origin === finalDestination ? 'Round Trip' : 'One Way';
}

/**
 * Transform itinerary data from backend format to component format
 */
export function transformItineraryData(itinerary: NestedItineraryRow[]): NestedItineraryRow[] {
  // High complexity here is field-name fallback chains (backend snake_case
  // vs several legacy camelCase aliases per field), not branchy logic.
  // eslint-disable-next-line complexity
  return itinerary.map(segment => ({
    date: segment.segment_date || segment.date || null,
    day: segment.day_of_week || segment.day || '',
    from: segment.from_location || segment.from || '',
    to: segment.to_location || segment.to || '',
    etd: segment.departure_time || segment.etd || '',
    eta: segment.arrival_time || segment.eta || '',
    flightNumber: segment.flight_number || segment.flightNumber || '',
    remarks: segment.remarks || '',
  }));
}

/**
 * Transform itinerary data specifically for External Parties
 * External Parties component expects different field names
 */
export function transformExternalPartiesItineraryData(
  itinerary: NestedItineraryRow[]
): NestedItineraryRow[] {
  // High complexity here is field-name fallback chains (backend snake_case
  // vs several legacy camelCase aliases per field), not branchy logic.
  // eslint-disable-next-line complexity
  const transformed = itinerary.map(segment => {
    const result = {
      departureDate: segment.segment_date || segment.date || segment.departureDate || null,
      day: segment.day_of_week || segment.day || '',
      departureTime: segment.departure_time || segment.etd || segment.departureTime || '',
      departureLocation: segment.from_location || segment.from || segment.departureLocation || '',
      arrivalDate: segment.arrival_date || segment.date || segment.arrivalDate || null,
      arrivalTime: segment.arrival_time || segment.eta || segment.arrivalTime || '',
      arrivalLocation: segment.to_location || segment.to || segment.arrivalLocation || '',
      modeOfTransport:
        segment.mode_of_transport ||
        segment.modeOfTransport ||
        segment.flight_number ||
        segment.flightNumber ||
        '',
      remarks: segment.remarks || '',
    };
    return result;
  });

  return transformed;
}

/**
 * Transform meal selections data from backend format to component format
 */
export function transformMealSelectionsData(mealSelections: RawMealRow[]): DailyMealSelection[] {
  const transformed = mealSelections.map(meal => {
    const result = {
      date: meal.meal_date || meal.date || '',
      // Explicitly handle boolean values - backend returns true/false
      breakfast: meal.breakfast === true || meal.breakfast === 'true' || meal.breakfast === 1,
      lunch: meal.lunch === true || meal.lunch === 'true' || meal.lunch === 1,
      dinner: meal.dinner === true || meal.dinner === 'true' || meal.dinner === 1,
      supper: meal.supper === true || meal.supper === 'true' || meal.supper === 1,
      refreshment:
        meal.refreshment === true || meal.refreshment === 'true' || meal.refreshment === 1,
    };
    return result;
  });

  return transformed;
}

/**
 * Transform bank details from backend format to component format
 */
export function transformBankDetails(
  bankDetail: RawBankDetailRow | null | undefined
): AdvanceBankDetails {
  if (!bankDetail || Object.keys(bankDetail).length === 0) {
    return {
      bankName: '',
      accountNumber: '',
      accountName: '',
      branchAddress: '',
      currency: 'USD',
    };
  }

  return {
    bankName: bankDetail.bank_name || bankDetail.bankName || '',
    accountNumber: bankDetail.account_number || bankDetail.accountNumber || '',
    accountName: bankDetail.account_name || bankDetail.accountName || '',
    branchAddress: bankDetail.branch_address || bankDetail.branchAddress || '',
    currency: bankDetail.currency || 'USD',
  };
}

/**
 * Transform advance amounts from backend format to component format
 */
export function transformAdvanceAmounts(
  advanceAmounts: RawAdvanceAmountRow[]
): AdvanceAmountItem[] {
  if (!advanceAmounts || advanceAmounts.length === 0) {
    return [];
  }

  return advanceAmounts.map(item => ({
    dateFrom: item.date_from || item.dateFrom || '',
    dateTo: item.date_to || item.dateTo || '',
    lh: item.lh || 0,
    ma: item.ma || 0,
    oa: item.oa || 0,
    tr: item.tr || 0,
    oe: item.oe || 0,
    usd: item.usd || 0,
    remarks: item.remarks || '',
  }));
}

/**
 * Extract passport file info from passport details for upload component
 */
export function extractPassportFileInfo(
  passportDetails: RawPassportRow | RawPassportRow[] | null | undefined
): PassportUploadDetails {
  if (!passportDetails) {
    return { file: null, fileName: '', fileUrl: '' };
  }

  // Handle array format from backend
  const detail = Array.isArray(passportDetails) ? passportDetails[0] : passportDetails;

  if (!detail) {
    return { file: null, fileName: '', fileUrl: '' };
  }

  const fileUrl = detail.passport_file_url || detail.passportFileUrl || detail.passport_file || '';
  const fileName = fileUrl ? fileUrl.split('/').pop() || '' : '';

  return {
    file: null, // File object is not available from backend, only URL
    fileName: fileName,
    fileUrl: fileUrl,
  };
}
