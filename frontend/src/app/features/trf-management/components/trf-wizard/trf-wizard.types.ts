import type { ApproverSelection } from '../../../../core/services/workflow.service';
import type { SkippedStepsSelection } from '../../../../shared/components/approver-selection/approver-selection.component';
import type { DailyMealSelection } from '../../../../shared/components/meal-provision/meal-provision.component';
import type {
  AccommodationDetails,
  TransportDetails,
} from '../domestic-travel-details/domestic-travel-details.component';
import type {
  AdvanceBankDetails,
  AdvanceAmountItem,
} from '../overseas-travel-details/overseas-travel-details.component';

/**
 * Raw TRF payload as the backend actually sends it. snake_case is the
 * current serializer's real field naming; the camelCase fallbacks
 * throughout this file (data.foo || data.fooBar) defend against an older
 * serializer shape this wizard has always had to tolerate on edit-load -
 * both are kept here rather than picking one, to match that existing
 * defensive pattern instead of silently dropping a code path.
 */
export interface TrfBackendDetail {
  purpose?: string;
  itinerary?: unknown[];
  mealProvision?: { dailyMealSelections?: unknown[] };
  advanceBankDetails?: unknown;
  advanceAmountRequested?: unknown[];
}

export interface TrfBackendResponse {
  id: number;
  trf?: TrfBackendResponse; // some endpoints wrap the row as { trf: {...} }
  status?: string;
  travel_type?: string;
  travelType?: string;
  requestor_name?: string;
  requestorName?: string;
  staff_id?: string;
  staffId?: string;
  department?: string;
  position?: string;
  cost_center?: string;
  costCenter?: string;
  tel_email?: string;
  telEmail?: string;
  email?: string;
  purpose?: string;
  additional_comments?: string;
  additionalComments?: string;
  selected_approvers?: ApproverSelection;
  skipped_steps?: SkippedStepsSelection;
  /**
   * Step orders (ints) that already have an APPROVED WorkflowStepExecution.
   * Drives per-step lock state in the edit-mode "Select Approvers" UI - see
   * TravelRequestSerializer.get_approved_step_orders (backend/trf/serializers.py).
   */
  approved_step_orders?: number[];
  domesticTravelDetails?: TrfBackendDetail;
  overseasTravelDetails?: TrfBackendDetail;
  externalPartiesTravelDetails?: TrfBackendDetail;
  externalPartyRequestorInfo?: {
    externalFullName?: string;
    externalOrganization?: string;
    externalRefToAuthorityLetter?: string;
    externalCostCenter?: string;
  };
  itinerary_segments?: unknown[];
  itinerary?: unknown[];
  daily_meals?: unknown[];
  daily_meal_selections?: unknown[];
  mealSelections?: unknown[];
  passport_details?: unknown;
  passportDetails?: unknown;
  bank_detail?: unknown;
  advance_bank_details?: unknown;
  bankDetails?: unknown;
  advance_amounts?: unknown[];
  advance_amount_items?: unknown[];
  advanceAmounts?: unknown[];
  advance_consent_accepted?: boolean;
  external_full_name?: string;
  externalFullName?: string;
  external_organization?: string;
  externalOrganization?: string;
  external_ref_to_authority_letter?: string;
  externalRefToAuthorityLetter?: string;
  external_cost_center?: string;
  externalCostCenter?: string;
}

/**
 * An itinerary row as createNestedResources() actually reads it - a union
 * of the standard field names (date/from/to/etd/eta/flightNumber), External
 * Parties' own names (departureDate/departureLocation/arrivalLocation/
 * departureTime/arrivalTime/modeOfTransport), and the backend's raw
 * snake_case names (segment_date/from_location/etc.) that
 * transformItineraryData()/transformExternalPartiesItineraryData() read
 * directly off an edit-load response, before it's been normalized to the
 * camelCase names above. All optional since no single row ever has every
 * field at once - which alias is present depends on where the row came
 * from (raw backend vs. already-transformed component data).
 */
export interface NestedItineraryRow {
  date?: string | Date | null;
  segment_date?: string | Date | null;
  departureDate?: string | Date | null;
  arrivalDate?: string | Date | null;
  arrival_date?: string | Date | null;
  from?: string;
  from_location?: string;
  departureLocation?: string;
  to?: string;
  to_location?: string;
  arrivalLocation?: string;
  day?: string;
  day_of_week?: string;
  departureTime?: string;
  etd?: string;
  departure_time?: string;
  arrivalTime?: string;
  eta?: string;
  arrival_time?: string;
  modeOfTransport?: string;
  mode_of_transport?: string;
  flightNumber?: string;
  flight_number?: string;
  remarks?: string;
}

/** Raw meal-selection row as read directly off an edit-load backend
 * response - boolean flags may arrive as an actual boolean, the string
 * "true", or 1, depending on which serializer produced the response. */
export interface RawMealRow {
  date?: string | Date | null;
  meal_date?: string | Date | null;
  breakfast?: boolean | string | number;
  lunch?: boolean | string | number;
  dinner?: boolean | string | number;
  supper?: boolean | string | number;
  refreshment?: boolean | string | number;
}

/** Raw bank-detail row as read directly off an edit-load backend response. */
export interface RawBankDetailRow {
  bank_name?: string;
  bankName?: string;
  account_number?: string;
  accountNumber?: string;
  account_name?: string;
  accountName?: string;
  branch_address?: string;
  branchAddress?: string;
  currency?: string;
}

/** Raw advance-amount row as read directly off an edit-load backend
 * response. */
export interface RawAdvanceAmountRow {
  date_from?: string | null;
  dateFrom?: string | null;
  date_to?: string | null;
  dateTo?: string | null;
  lh?: number;
  ma?: number;
  oa?: number;
  tr?: number;
  oe?: number;
  usd?: number;
  remarks?: string;
}

/** Raw passport-detail row as read directly off an edit-load backend
 * response - may arrive as a single object or (per the backend's own array
 * serialization) the first element of an array. */
export interface RawPassportRow {
  passport_file_url?: string;
  passportFileUrl?: string;
  passport_file?: string;
  full_name?: string;
  fullName?: string;
  passport_number?: string;
  passportNumber?: string;
  nationality?: string;
  date_of_birth?: string | null;
  dateOfBirth?: string | null;
  place_of_birth?: string;
  placeOfBirth?: string;
  passport_issue_date?: string | null;
  passportIssueDate?: string | null;
  passport_expiry_date?: string | null;
  passportExpiryDate?: string | null;
}

/** Return shape of transformPassportDetails() / what's read back out of it
 * in createNestedResources(). */
export interface TransformedPassportDetails {
  fullName: string;
  passportNumber: string;
  nationality: string;
  dateOfBirth: string | null;
  placeOfBirth: string;
  passportIssueDate: string | null;
  passportExpiryDate: string | null;
}

/** Return shape of prepareTrfData()/prepareXData() - what
 * createNestedResources() consumes to build every linked resource. */
export interface PreparedTrfData {
  mainTrf: Record<string, unknown>;
  itinerarySegments: NestedItineraryRow[];
  mealSelections: DailyMealSelection[];
  passportDetails: TransformedPassportDetails | null;
  bankDetails: AdvanceBankDetails | null;
  advanceAmounts: AdvanceAmountItem[];
  accommodation?: AccommodationDetails | null;
  transport?: TransportDetails | null;
}
