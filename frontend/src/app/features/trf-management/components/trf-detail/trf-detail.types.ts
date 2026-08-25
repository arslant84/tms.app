/**
 * Raw/transformed TRF data shapes for TrfDetailComponent's
 * transformTrfData(). snake_case is the current serializer's real field
 * naming; the camelCase fallbacks throughout defend against an older
 * serializer shape this page has always had to tolerate - both are kept
 * here rather than picking one, matching the existing defensive pattern
 * instead of silently dropping a code path.
 */

export interface TrfItineraryRow {
  date?: string;
  segment_date?: string;
  day?: string;
  day_of_week?: string;
  from?: string;
  from_location?: string;
  to?: string;
  to_location?: string;
  etd?: string;
  departure_time?: string;
  eta?: string;
  arrival_time?: string;
  flightNumber?: string;
  flight_number?: string;
  remarks?: string;
}

export interface TrfMealRow {
  meal_date?: string;
  breakfast?: boolean | string | number;
  lunch?: boolean | string | number;
  dinner?: boolean | string | number;
  supper?: boolean | string | number;
  refreshment?: boolean | string | number;
}

export interface TrfPassportRow {
  passport_file_url?: string;
  passportFileUrl?: string;
}

export interface TrfBankDetails {
  account_name?: string;
  accountName?: string;
  bank_name?: string;
  bankName?: string;
  account_number?: string;
  accountNumber?: string;
  currency?: string;
  branch_address?: string;
  branchAddress?: string;
}

export interface TrfAdvanceAmountRow {
  date_from?: string;
  dateFrom?: string;
  date_to?: string;
  dateTo?: string;
  lh?: number;
  ma?: number;
  oa?: number;
  tr?: number;
  oe?: number;
  usd?: number;
  remarks?: string;
}

/** Legacy TrfApprovalStep row (pre-WorkflowEngine fallback timeline). */
export interface TrfApprovalStepRow {
  step_name?: string;
  step_role?: string;
  status?: string;
  step_date?: string;
  comments?: string;
}

export interface TrfDetailRawTravelDetails {
  purpose?: string;
  itinerary?: TrfItineraryRow[];
  mealProvision?: { dailyMealSelections?: TrfMealRow[] };
  advanceBankDetails?: TrfBankDetails;
  advanceAmountRequested?: TrfAdvanceAmountRow[];
}

export interface TrfDetailRawExternalPartyInfo {
  externalFullName?: string;
  externalOrganization?: string;
  externalRefToAuthorityLetter?: string;
  externalCostCenter?: string;
}

export interface TrfDetailRawResponse {
  id: number;
  trf?: TrfDetailRawResponse; // some endpoints wrap the row as { trf: {...} }
  request_number?: string;
  requestNumber?: string;
  travel_type?: string;
  travelType?: string;
  status?: string;
  requestor_name?: string;
  requestorName?: string;
  created_by?: number | null;
  createdBy?: number | null;
  staff_id?: string;
  staffId?: string;
  department?: string;
  position?: string;
  cost_center?: string;
  costCenter?: string;
  tel_email?: string;
  telEmail?: string;
  purpose?: string;
  additional_comments?: string;
  additionalComments?: string;
  estimated_cost?: number | string;
  estimatedCost?: number | string;
  external_full_name?: string;
  external_party_name?: string;
  externalPartyName?: string;
  external_organization?: string;
  external_party_organization?: string;
  externalPartyOrganization?: string;
  external_ref_to_authority_letter?: string;
  externalRefToAuthorityLetter?: string;
  external_cost_center?: string;
  externalCostCenter?: string;
  itinerary_segments?: TrfItineraryRow[];
  itinerary?: TrfItineraryRow[];
  daily_meals?: TrfMealRow[];
  daily_meal_selections?: TrfMealRow[];
  mealSelections?: TrfMealRow[];
  meal_processing_status?: string;
  mealProcessingStatus?: string;
  passport_details?: TrfPassportRow[];
  passportDetails?: TrfPassportRow[];
  advance_bank_details?: TrfBankDetails;
  bankDetails?: TrfBankDetails;
  advance_amount_items?: TrfAdvanceAmountRow[];
  advanceAmounts?: TrfAdvanceAmountRow[];
  advance_consent_accepted?: boolean;
  advanceConsentAccepted?: boolean;
  advance_consent_accepted_at?: string;
  advanceConsentAcceptedAt?: string;
  approval_steps?: TrfApprovalStepRow[];
  approvalSteps?: TrfApprovalStepRow[];
  approvalWorkflow?: TrfApprovalStepRow[];
  created_at?: string;
  createdAt?: string;
  updated_at?: string;
  updatedAt?: string;
  submitted_at?: string;
  submittedAt?: string;
  flight_details?: TrfFlightDetails;
  flightDetails?: TrfFlightDetails;
  domesticTravelDetails?: TrfDetailRawTravelDetails;
  overseasTravelDetails?: TrfDetailRawTravelDetails;
  externalPartiesTravelDetails?: TrfDetailRawTravelDetails;
  externalPartyRequestorInfo?: TrfDetailRawExternalPartyInfo;
}

/** A flight booking segment (one leg), as returned by FlightBookingSegment -
 * matches trf/views.py's book_flight/_save_flight_segments payload shape. */
export interface TrfFlightSegment {
  direction: 'OUTBOUND' | 'RETURN' | string;
  sequence?: number;
  flightNumber?: string;
  departureAirport?: string;
  arrivalAirport?: string;
  departureDateTime?: string;
  arrivalDateTime?: string;
}

export interface TrfFlightDetails {
  flightNumber?: string;
  flight_number?: string;
  airline?: string;
  bookingReference?: string;
  booking_reference?: string;
  departureLocation?: string;
  departure_location?: string;
  arrivalLocation?: string;
  arrival_location?: string;
  departureDate?: string;
  departure_date?: string;
  departureTime?: string;
  departure_time?: string;
  arrivalDate?: string;
  arrival_date?: string;
  arrivalTime?: string;
  arrival_time?: string;
  status?: string;
  processedBy?: string;
  processedDate?: string;
  remarks?: string;
  eTicketUrl?: string;
  segments?: TrfFlightSegment[];
}

/** Per-travel-type fields transformTrfData assembles before building the
 * final TrfViewData - kept separate so each travel type's extraction is
 * its own small function instead of one large branchy method. */
export interface TravelTypeFields {
  itinerary: TrfItineraryRow[];
  mealSelections: TrfMealRow[];
  bankDetails: TrfBankDetails | null;
  advanceAmounts: TrfAdvanceAmountRow[];
  purpose: string;
}

export interface TrfViewData {
  id: number;
  requestNumber: string;
  travelType: string;
  status: string;
  requestorName: string;
  createdBy: number | null;
  staffId: string;
  department: string;
  position: string;
  costCenter: string;
  telEmail: string;
  purpose: string;
  additionalComments: string;
  estimatedCost: number | string;
  externalPartyName: string;
  externalPartyOrganization: string;
  externalRefToAuthorityLetter: string;
  externalCostCenter: string;
  itinerary: TrfItineraryRow[];
  mealSelections: TrfMealRow[];
  mealProcessingStatus: string;
  passportDetails: TrfPassportRow[];
  bankDetails: TrfBankDetails | null;
  advanceAmounts: TrfAdvanceAmountRow[];
  advanceConsentAccepted: boolean;
  advanceConsentAcceptedAt: string;
  approvalSteps: TrfApprovalStepRow[];
  createdAt: string;
  updatedAt: string;
  submittedAt: string;
  flightDetails: TrfFlightDetails | null;
}
