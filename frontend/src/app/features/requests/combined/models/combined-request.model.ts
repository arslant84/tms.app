/**
 * Combined Request Models
 *
 * Interfaces and types for the Combined Request module that unifies
 * TSR, Transport, Accommodation, and Visa requests.
 */

// Status types for the overall request and individual modules
export type CombinedRequestStatus =
  | 'Draft'
  | 'Submitted'
  | 'Pending Department Focal'
  | 'Pending Line Manager'
  | 'Pending HOD'
  | 'Pending Travel Desk'
  | 'Approved'
  | 'Processing'
  | 'Completed'
  | 'Rejected'
  | 'Cancelled';

export type ModuleStatus =
  | 'not_requested'
  | 'pending'
  | 'approved'
  | 'processing'
  | 'completed'
  | 'rejected';

// Passport details for visa applications
export interface PassportDetails {
  id?: number;
  fullName: string;
  passportNumber: string;
  nationality: string;
  dateOfBirth?: string;
  placeOfBirth?: string;
  issueDate?: string;
  expiryDate?: string;
  passportFile?: File | string;
}

// Advance amount item for international travel
export interface AdvanceAmountItem {
  id?: number;
  dateFrom: string;
  dateTo: string;
  lh?: number;
  ma?: number;
  oa?: number;
  tr?: number;
  oe?: number;
  usd?: number;
  remarks?: string;
}

// Itinerary segment for travel
export interface ItinerarySegment {
  id?: number;
  segmentOrder: number;
  segmentDate?: string;
  dayOfWeek?: string;
  fromLocation: string;
  toLocation: string;
  departureTime?: string;
  arrivalTime?: string;
  modeOfTravel?: string;
  flightNumber?: string;
  flightClass?: string;
  purpose?: string;
  remarks?: string;
}

// Meal selection row (domestic travel)
export interface MealDailySelection {
  date: string | null;
  breakfast: boolean;
  lunch: boolean;
  dinner: boolean;
  supper: boolean;
  refreshment: boolean;
}

// Transport segment
export interface TransportSegment {
  id?: number;
  segmentOrder: number;
  dayOfWeek?: string;
  transportType?: string;
  pickupLocation: string;
  dropoffLocation: string;
  pickupDate?: string;
  pickupTime?: string;
  passengers: number;
  vehicleTypePreference?: string;
  notes?: string;
  // Admin fields (read-only for requestors)
  vehicleNumber?: string;
  driverName?: string;
  driverContact?: string;
  segmentCost?: number;
}

// Document attachment
export interface CombinedRequestDocument {
  id?: number;
  documentType: string;
  module: 'travel' | 'transport' | 'accommodation' | 'visa' | 'general';
  file?: File | string;
  fileName?: string;
  description?: string;
  uploadedBy?: number;
  uploadedByName?: string;
  uploadedAt?: string;
}

// Approval step tracking
export interface ApprovalStep {
  id?: number;
  stepOrder: number;
  stepName: string;
  stepRole?: string;
  module?: string;
  approver?: number;
  approverName?: string;
  status: 'pending' | 'approved' | 'rejected' | 'skipped';
  comments?: string;
  actionedAt?: string;
}

// Main Combined Request interface
export interface CombinedRequest {
  id?: number;
  requestNumber?: string;

  // Requestor Information (shared)
  requestor?: number;
  requestorName: string;
  requestorEmail?: string;
  staffId?: string;
  department?: string;
  position?: string;
  email?: string;
  phone?: string;
  costCenter?: string;

  // Module Inclusion Flags
  includeTravel: boolean;
  includeTransport: boolean;
  includeAccommodation: boolean;
  includeVisa: boolean;

  // Travel/TSR Section
  travelType?: string;
  tripType?: string;
  travelPurpose?: string;
  departureDate?: string;
  returnDate?: string;
  destinationCountry?: string;
  destinationCity?: string;
  travelData?: Record<string, any>;

  // Transport Section
  transportPurpose?: string;
  transportTsrReference?: string;
  transportRequiredFrom?: string;
  transportRequiredTo?: string;
  transportPickupLocation?: string;
  transportDropoffLocation?: string;
  transportData?: Record<string, any>;

  // Accommodation Section
  accommodationGender?: string;
  accommodationCheckin?: string;
  accommodationCheckout?: string;
  accommodationLocation?: string;
  accommodationRoomType?: string;
  accommodationFlightArrivalTime?: string;
  accommodationFlightDepartureTime?: string;
  accommodationSpecialRequests?: string;
  accommodationGuests?: number;
  accommodationPreferences?: string;
  accommodationData?: Record<string, any>;

  // Visa Section
  visaDestinationCountry?: string;
  visaType?: string;
  passportNumber?: string;
  passportExpiry?: string;
  visaData?: Record<string, any>;
  // Visa Section A: Particulars
  visa_date_of_birth?: string;
  visa_place_of_birth?: string;
  visa_citizenship?: string;
  visa_contact_telephone?: string;
  visa_marital_status?: string;
  visa_home_address?: string;
  visa_family_information?: string;
  visa_education_details?: string;
  visa_passport_number?: string;
  visa_passport_expiry_date?: string;
  visa_passport_place_of_issuance?: string;
  visa_passport_date_of_issuance?: string;
  visa_current_employer_name?: string;
  visa_current_employer_address?: string;
  // Visa Section B: Type of Request
  visa_request_type?: string;
  visa_approximately_arrival_date?: string;
  visa_duration_of_stay?: string;
  visa_entry_type?: string;
  visa_work_visit_category?: string;
  visa_application_fees_borne_by?: string;
  visa_cost_centre_number?: string;
  // Visa Section C: Travel Details
  visa_trf_reference_number?: string;
  visa_trip_start_date?: string;
  visa_trip_end_date?: string;
  visa_travel_purpose?: string;
  visa_itinerary_details?: string;
  // Visa Additional
  visa_additional_comments?: string;
  visa_supporting_documents_notes?: string;

  // Status Tracking
  status: CombinedRequestStatus;
  travelStatus: ModuleStatus;
  transportStatus: ModuleStatus;
  accommodationStatus: ModuleStatus;
  visaStatus: ModuleStatus;

  // Meal provision (domestic travel only)
  mealDailySelections?: MealDailySelection[];

  // Travel type-specific — Bank Details (international & home_leave)
  advanceBankAccountName?: string;
  advanceBankName?: string;
  advanceBankAccountNumber?: string;
  advanceBankCurrency?: string;
  advanceBankBranchRemarks?: string;
  // Travel type-specific — Advance Amount Items (international only)
  advanceAmountItems?: AdvanceAmountItem[];
  // Travel type-specific — External Party Info
  externalFullName?: string;
  externalOrganization?: string;
  externalRefToAuthorityLetter?: string;
  externalCostCenter?: string;

  // Additional
  additionalComments?: string;
  additionalData?: Record<string, any>;

  // Nested data
  passports?: PassportDetails[];
  itinerarySegments?: ItinerarySegment[];
  transportSegments?: TransportSegment[];
  documents?: CombinedRequestDocument[];
  approvalSteps?: ApprovalStep[];

  // Workflow support
  selectedApprovers?: { [stepOrder: number]: number };
  skippedSteps?: { [stepOrder: number]: string | null };

  // Timestamps
  submittedAt?: string;
  createdAt?: string;
  updatedAt?: string;
}

// Form data structure for the wizard
export interface CombinedRequestFormData {
  // Step 1: Module Selection
  includeTravel: boolean;
  includeTransport: boolean;
  includeAccommodation: boolean;
  includeVisa: boolean;

  // Step 2: Basic Information
  requestorName: string;
  staffId: string;
  department: string;
  position: string;
  email: string;
  phone: string;
  costCenter: string;

  // Step 3: Travel Details (if includeTravel)
  travelType: string;
  tripType: string;
  travelPurpose: string;
  departureDate: string;
  returnDate: string;
  destinationCountry: string;
  destinationCity: string;
  itinerarySegments: ItinerarySegment[];

  // Step 4: Transport Details (if includeTransport)
  transportSegments: TransportSegment[];

  // Step 5: Accommodation Details (if includeAccommodation)
  accommodationCheckin: string;
  accommodationCheckout: string;
  accommodationLocation: string;
  accommodationGuests: number;
  accommodationPreferences: string;

  // Step 6: Visa Details (if includeVisa)
  visaDestinationCountry: string;
  visaType: string;
  passports: PassportDetails[];

  // Step 7: Review & Submit
  additionalComments: string;
  selectedApprovers: { [stepOrder: number]: number };
  skippedSteps: { [stepOrder: number]: string | null };
}

// Filters for list view
export interface CombinedRequestFilters {
  status?: string;
  search?: string;
  includeTravel?: boolean;
  includeTransport?: boolean;
  includeAccommodation?: boolean;
  includeVisa?: boolean;
  page?: number;
  pageSize?: number;
  adminView?: boolean;
}

// API response format conversion helpers
export function toFrontendFormat(backendData: any): CombinedRequest {
  return {
    id: backendData.id,
    requestNumber: backendData.request_number,
    requestor: backendData.requestor,
    requestorName: backendData.requestor_name || '',
    requestorEmail: backendData.requestor_email,
    staffId: backendData.staff_id || '',
    department: backendData.department || '',
    position: backendData.position || '',
    email: backendData.email || '',
    phone: backendData.phone || '',
    costCenter: backendData.cost_center || '',

    includeTravel: backendData.include_travel ?? true,
    includeTransport: backendData.include_transport ?? false,
    includeAccommodation: backendData.include_accommodation ?? false,
    includeVisa: backendData.include_visa ?? false,

    travelType: backendData.travel_type || '',
    tripType: backendData.trip_type || 'Round Trip',
    travelPurpose: backendData.travel_purpose || '',
    departureDate: backendData.departure_date || '',
    returnDate: backendData.return_date || '',
    destinationCountry: backendData.destination_country || '',
    destinationCity: backendData.destination_city || '',
    travelData: backendData.travel_data || {},

    transportPurpose: backendData.transport_purpose || '',
    transportTsrReference: backendData.transport_tsr_reference || '',
    transportRequiredFrom: backendData.transport_required_from,
    transportRequiredTo: backendData.transport_required_to,
    transportPickupLocation: backendData.transport_pickup_location || '',
    transportDropoffLocation: backendData.transport_dropoff_location || '',
    transportData: backendData.transport_data || {},

    accommodationGender: backendData.accommodation_gender || backendData.additional_data?.requestor_gender || '',
    accommodationCheckin: backendData.accommodation_checkin || backendData.additional_data?.requested_check_in_date || '',
    accommodationCheckout: backendData.accommodation_checkout || backendData.additional_data?.requested_check_out_date || '',
    accommodationLocation: backendData.accommodation_location || backendData.additional_data?.location || '',
    accommodationRoomType: backendData.accommodation_room_type || backendData.additional_data?.requested_room_type || '',
    accommodationFlightArrivalTime: backendData.accommodation_flight_arrival_time || backendData.additional_data?.flight_arrival_time || '',
    accommodationFlightDepartureTime: backendData.accommodation_flight_departure_time || backendData.additional_data?.flight_departure_time || '',
    accommodationSpecialRequests: backendData.accommodation_special_requests || backendData.additional_data?.special_requests || '',
    accommodationGuests: backendData.accommodation_guests || 1,
    accommodationPreferences: backendData.accommodation_preferences || '',
    accommodationData: backendData.accommodation_data || {},

    visaDestinationCountry: backendData.visa_destination_country || '',
    visaType: backendData.visa_type || '',
    passportNumber: backendData.passport_number || '',
    passportExpiry: backendData.passport_expiry || '',
    visaData: backendData.visa_data || {},
    visa_date_of_birth: backendData.visa_date_of_birth || '',
    visa_place_of_birth: backendData.visa_place_of_birth || '',
    visa_citizenship: backendData.visa_citizenship || '',
    visa_contact_telephone: backendData.visa_contact_telephone || '',
    visa_marital_status: backendData.visa_marital_status || '',
    visa_home_address: backendData.visa_home_address || '',
    visa_family_information: backendData.visa_family_information || '',
    visa_education_details: backendData.visa_education_details || '',
    visa_passport_number: backendData.visa_passport_number || '',
    visa_passport_expiry_date: backendData.visa_passport_expiry_date || '',
    visa_passport_place_of_issuance: backendData.visa_passport_place_of_issuance || '',
    visa_passport_date_of_issuance: backendData.visa_passport_date_of_issuance || '',
    visa_current_employer_name: backendData.visa_current_employer_name || '',
    visa_current_employer_address: backendData.visa_current_employer_address || '',
    visa_request_type: backendData.visa_request_type || 'VISA',
    visa_approximately_arrival_date: backendData.visa_approximately_arrival_date || '',
    visa_duration_of_stay: backendData.visa_duration_of_stay || '',
    visa_entry_type: backendData.visa_entry_type || '',
    visa_work_visit_category: backendData.visa_work_visit_category || '',
    visa_application_fees_borne_by: backendData.visa_application_fees_borne_by || '',
    visa_cost_centre_number: backendData.visa_cost_centre_number || '',
    visa_trf_reference_number: backendData.visa_trf_reference_number || '',
    visa_trip_start_date: backendData.visa_trip_start_date || '',
    visa_trip_end_date: backendData.visa_trip_end_date || '',
    visa_travel_purpose: backendData.visa_travel_purpose || '',
    visa_itinerary_details: backendData.visa_itinerary_details || '',
    visa_additional_comments: backendData.visa_additional_comments || '',
    visa_supporting_documents_notes: backendData.visa_supporting_documents_notes || '',

    advanceBankAccountName: backendData.advance_bank_account_name || '',
    advanceBankName: backendData.advance_bank_name || '',
    advanceBankAccountNumber: backendData.advance_bank_account_number || '',
    advanceBankCurrency: backendData.advance_bank_currency || 'TMT',
    advanceBankBranchRemarks: backendData.advance_bank_branch_remarks || '',
    externalFullName: backendData.external_full_name || '',
    externalOrganization: backendData.external_organization || '',
    externalRefToAuthorityLetter: backendData.external_ref_to_authority_letter || '',
    externalCostCenter: backendData.external_cost_center || '',

    mealDailySelections: (backendData.travel_data?.meal_selections || []).map((s: any) => ({
      date: s.date || null,
      breakfast: s.breakfast || false,
      lunch: s.lunch || false,
      dinner: s.dinner || false,
      supper: s.supper || false,
      refreshment: s.refreshment || false
    })),

    advanceAmountItems: (backendData.travel_data?.advance_amount_items || backendData.advance_amount_items || []).map((item: any) => ({
      id: item.id,
      dateFrom: item.date_from,
      dateTo: item.date_to,
      lh: item.lh || 0,
      ma: item.ma || 0,
      oa: item.oa || 0,
      tr: item.tr || 0,
      oe: item.oe || 0,
      usd: item.usd || 0,
      remarks: item.remarks || ''
    })) || [],

    status: backendData.status || 'Draft',
    travelStatus: backendData.travel_status || 'not_requested',
    transportStatus: backendData.transport_status || 'not_requested',
    accommodationStatus: backendData.accommodation_status || 'not_requested',
    visaStatus: backendData.visa_status || 'not_requested',

    additionalComments: backendData.additional_comments || '',
    additionalData: backendData.additional_data || {},

    passports: backendData.passports?.map((p: any) => ({
      id: p.id,
      fullName: p.full_name,
      passportNumber: p.passport_number,
      nationality: p.nationality,
      dateOfBirth: p.date_of_birth,
      placeOfBirth: p.place_of_birth,
      issueDate: p.issue_date,
      expiryDate: p.expiry_date,
      passportFile: p.passport_file
    })) || [],

    itinerarySegments: backendData.itinerary_segments?.map((s: any) => ({
      id: s.id,
      segmentOrder: s.segment_order,
      segmentDate: s.segment_date,
      dayOfWeek: s.day_of_week,
      fromLocation: s.from_location,
      toLocation: s.to_location,
      departureTime: s.departure_time,
      arrivalTime: s.arrival_time,
      modeOfTravel: s.mode_of_travel,
      flightNumber: s.flight_number,
      flightClass: s.flight_class,
      purpose: s.purpose,
      remarks: s.remarks
    })) || [],

    transportSegments: backendData.transport_segments?.map((s: any) => ({
      id: s.id,
      segmentOrder: s.segment_order,
      dayOfWeek: s.day_of_week || '',
      transportType: s.transport_type || '',
      pickupLocation: s.pickup_location,
      dropoffLocation: s.dropoff_location,
      pickupDate: s.pickup_date || '',
      pickupTime: s.pickup_time || '',
      passengers: s.passengers,
      vehicleTypePreference: s.vehicle_type_preference || '',
      notes: s.notes || '',
      vehicleNumber: s.vehicle_number,
      driverName: s.driver_name,
      driverContact: s.driver_contact,
      segmentCost: s.segment_cost
    })) || [],

    documents: backendData.documents?.map((d: any) => ({
      id: d.id,
      documentType: d.document_type,
      module: d.module,
      file: d.file,
      fileName: d.file_name,
      description: d.description,
      uploadedBy: d.uploaded_by,
      uploadedByName: d.uploaded_by_name,
      uploadedAt: d.uploaded_at
    })) || [],

    approvalSteps: backendData.approval_steps?.map((a: any) => ({
      id: a.id,
      stepOrder: a.step_order,
      stepName: a.step_name,
      stepRole: a.step_role,
      module: a.module,
      approver: a.approver,
      approverName: a.approver_name,
      status: a.status,
      comments: a.comments,
      actionedAt: a.actioned_at
    })) || [],

    submittedAt: backendData.submitted_at,
    createdAt: backendData.created_at,
    updatedAt: backendData.updated_at
  };
}

export function toBackendFormat(frontendData: Partial<CombinedRequest>): any {
  const result: any = {};

  // Basic fields
  if (frontendData.requestorName !== undefined) result.requestor_name = frontendData.requestorName;
  if (frontendData.staffId !== undefined) result.staff_id = frontendData.staffId;
  if (frontendData.department !== undefined) {
    const dept = frontendData.department;
    result.department = typeof dept === 'string'
      ? dept
      : (dept as { name?: string; code?: string } | null)?.name
        || (dept as { name?: string; code?: string } | null)?.code
        || '';
  }
  if (frontendData.position !== undefined) result.position = frontendData.position;
  if (frontendData.email !== undefined) result.email = frontendData.email;
  if (frontendData.phone !== undefined) result.phone = frontendData.phone;
  if (frontendData.costCenter !== undefined) result.cost_center = frontendData.costCenter;

  // Module flags
  if (frontendData.includeTravel !== undefined) result.include_travel = frontendData.includeTravel;
  if (frontendData.includeTransport !== undefined) result.include_transport = frontendData.includeTransport;
  if (frontendData.includeAccommodation !== undefined) result.include_accommodation = frontendData.includeAccommodation;
  if (frontendData.includeVisa !== undefined) result.include_visa = frontendData.includeVisa;

  // Travel fields
  if (frontendData.travelType !== undefined) result.travel_type = frontendData.travelType;
  if (frontendData.tripType !== undefined) result.trip_type = frontendData.tripType;
  if (frontendData.travelPurpose !== undefined) result.travel_purpose = frontendData.travelPurpose;
  if (frontendData.departureDate !== undefined) result.departure_date = frontendData.departureDate || null;
  if (frontendData.returnDate !== undefined) result.return_date = frontendData.returnDate || null;
  if (frontendData.destinationCountry !== undefined) result.destination_country = frontendData.destinationCountry;
  if (frontendData.destinationCity !== undefined) result.destination_city = frontendData.destinationCity;

  // Pack meal selections and advance amount items into travel_data JSON
  const travelDataBase = frontendData.travelData || {};
  const travelDataOut: Record<string, unknown> = { ...travelDataBase };
  if (frontendData.mealDailySelections !== undefined) {
    travelDataOut['meal_selections'] = frontendData.mealDailySelections;
  }
  if (frontendData.advanceAmountItems !== undefined) {
    travelDataOut['advance_amount_items'] = frontendData.advanceAmountItems?.map(item => ({
      date_from: item.dateFrom || null,
      date_to: item.dateTo || null,
      lh: item.lh || 0,
      ma: item.ma || 0,
      oa: item.oa || 0,
      tr: item.tr || 0,
      oe: item.oe || 0,
      usd: item.usd || 0,
      remarks: item.remarks || null
    }));
  }
  result.travel_data = travelDataOut;

  // Transport fields
  if (frontendData.transportPurpose !== undefined) result.transport_purpose = frontendData.transportPurpose;
  if (frontendData.transportTsrReference !== undefined) result.transport_tsr_reference = frontendData.transportTsrReference;
  if (frontendData.transportRequiredFrom !== undefined) result.transport_required_from = frontendData.transportRequiredFrom;
  if (frontendData.transportRequiredTo !== undefined) result.transport_required_to = frontendData.transportRequiredTo;
  if (frontendData.transportPickupLocation !== undefined) result.transport_pickup_location = frontendData.transportPickupLocation;
  if (frontendData.transportDropoffLocation !== undefined) result.transport_dropoff_location = frontendData.transportDropoffLocation;
  if (frontendData.transportData !== undefined) result.transport_data = frontendData.transportData;

  // Accommodation fields
  if (frontendData.accommodationGender !== undefined) result.accommodation_gender = frontendData.accommodationGender;
  if (frontendData.accommodationCheckin !== undefined) result.accommodation_checkin = frontendData.accommodationCheckin || null;
  if (frontendData.accommodationCheckout !== undefined) result.accommodation_checkout = frontendData.accommodationCheckout || null;
  if (frontendData.accommodationLocation !== undefined) result.accommodation_location = frontendData.accommodationLocation;
  if (frontendData.accommodationRoomType !== undefined) result.accommodation_room_type = frontendData.accommodationRoomType;
  if (frontendData.accommodationFlightArrivalTime !== undefined) result.accommodation_flight_arrival_time = frontendData.accommodationFlightArrivalTime;
  if (frontendData.accommodationFlightDepartureTime !== undefined) result.accommodation_flight_departure_time = frontendData.accommodationFlightDepartureTime;
  if (frontendData.accommodationSpecialRequests !== undefined) result.accommodation_special_requests = frontendData.accommodationSpecialRequests;
  if (frontendData.accommodationGuests !== undefined) result.accommodation_guests = frontendData.accommodationGuests;
  if (frontendData.accommodationPreferences !== undefined) result.accommodation_preferences = frontendData.accommodationPreferences;
  if (frontendData.accommodationData !== undefined) result.accommodation_data = frontendData.accommodationData;

  // Visa fields
  if (frontendData.visaDestinationCountry !== undefined) result.visa_destination_country = frontendData.visaDestinationCountry;
  if (frontendData.visaType !== undefined) result.visa_type = frontendData.visaType;
  if (frontendData.passportNumber !== undefined) result.passport_number = frontendData.passportNumber;
  if (frontendData.passportExpiry !== undefined) result.passport_expiry = frontendData.passportExpiry;
  if (frontendData.visaData !== undefined) result.visa_data = frontendData.visaData;
  if (frontendData.visa_date_of_birth !== undefined) result.visa_date_of_birth = frontendData.visa_date_of_birth || null;
  if (frontendData.visa_place_of_birth !== undefined) result.visa_place_of_birth = frontendData.visa_place_of_birth;
  if (frontendData.visa_citizenship !== undefined) result.visa_citizenship = frontendData.visa_citizenship;
  if (frontendData.visa_contact_telephone !== undefined) result.visa_contact_telephone = frontendData.visa_contact_telephone;
  if (frontendData.visa_marital_status !== undefined) result.visa_marital_status = frontendData.visa_marital_status;
  if (frontendData.visa_home_address !== undefined) result.visa_home_address = frontendData.visa_home_address;
  if (frontendData.visa_family_information !== undefined) result.visa_family_information = frontendData.visa_family_information;
  if (frontendData.visa_education_details !== undefined) result.visa_education_details = frontendData.visa_education_details;
  if (frontendData.visa_passport_number !== undefined) result.visa_passport_number = frontendData.visa_passport_number;
  if (frontendData.visa_passport_expiry_date !== undefined) result.visa_passport_expiry_date = frontendData.visa_passport_expiry_date || null;
  if (frontendData.visa_passport_place_of_issuance !== undefined) result.visa_passport_place_of_issuance = frontendData.visa_passport_place_of_issuance;
  if (frontendData.visa_passport_date_of_issuance !== undefined) result.visa_passport_date_of_issuance = frontendData.visa_passport_date_of_issuance || null;
  if (frontendData.visa_current_employer_name !== undefined) result.visa_current_employer_name = frontendData.visa_current_employer_name;
  if (frontendData.visa_current_employer_address !== undefined) result.visa_current_employer_address = frontendData.visa_current_employer_address;
  if (frontendData.visa_request_type !== undefined) result.visa_request_type = frontendData.visa_request_type;
  if (frontendData.visa_approximately_arrival_date !== undefined) result.visa_approximately_arrival_date = frontendData.visa_approximately_arrival_date || null;
  if (frontendData.visa_duration_of_stay !== undefined) result.visa_duration_of_stay = frontendData.visa_duration_of_stay;
  if (frontendData.visa_entry_type !== undefined) result.visa_entry_type = frontendData.visa_entry_type;
  if (frontendData.visa_work_visit_category !== undefined) result.visa_work_visit_category = frontendData.visa_work_visit_category;
  if (frontendData.visa_application_fees_borne_by !== undefined) result.visa_application_fees_borne_by = frontendData.visa_application_fees_borne_by;
  if (frontendData.visa_cost_centre_number !== undefined) result.visa_cost_centre_number = frontendData.visa_cost_centre_number;
  if (frontendData.visa_trf_reference_number !== undefined) result.visa_trf_reference_number = frontendData.visa_trf_reference_number;
  if (frontendData.visa_trip_start_date !== undefined) result.visa_trip_start_date = frontendData.visa_trip_start_date || null;
  if (frontendData.visa_trip_end_date !== undefined) result.visa_trip_end_date = frontendData.visa_trip_end_date || null;
  if (frontendData.visa_travel_purpose !== undefined) result.visa_travel_purpose = frontendData.visa_travel_purpose;
  if (frontendData.visa_itinerary_details !== undefined) result.visa_itinerary_details = frontendData.visa_itinerary_details;
  if (frontendData.visa_additional_comments !== undefined) result.visa_additional_comments = frontendData.visa_additional_comments;
  if (frontendData.visa_supporting_documents_notes !== undefined) result.visa_supporting_documents_notes = frontendData.visa_supporting_documents_notes;

  // Bank / advance / external fields
  if (frontendData.advanceBankAccountName !== undefined) result.advance_bank_account_name = frontendData.advanceBankAccountName;
  if (frontendData.advanceBankName !== undefined) result.advance_bank_name = frontendData.advanceBankName;
  if (frontendData.advanceBankAccountNumber !== undefined) result.advance_bank_account_number = frontendData.advanceBankAccountNumber;
  if (frontendData.advanceBankCurrency !== undefined) result.advance_bank_currency = frontendData.advanceBankCurrency;
  if (frontendData.advanceBankBranchRemarks !== undefined) result.advance_bank_branch_remarks = frontendData.advanceBankBranchRemarks;
  if (frontendData.externalFullName !== undefined) result.external_full_name = frontendData.externalFullName;
  if (frontendData.externalOrganization !== undefined) result.external_organization = frontendData.externalOrganization;
  if (frontendData.externalRefToAuthorityLetter !== undefined) result.external_ref_to_authority_letter = frontendData.externalRefToAuthorityLetter;
  if (frontendData.externalCostCenter !== undefined) result.external_cost_center = frontendData.externalCostCenter;
  // advanceAmountItems are packed into travel_data above — no separate top-level field

  // Additional fields
  if (frontendData.additionalComments !== undefined) result.additional_comments = frontendData.additionalComments;
  if (frontendData.additionalData !== undefined) result.additional_data = frontendData.additionalData;

  // Nested arrays
  if (frontendData.passports) {
    result.passports = frontendData.passports.map(p => ({
      full_name: p.fullName,
      passport_number: p.passportNumber,
      nationality: p.nationality,
      date_of_birth: p.dateOfBirth || null,
      place_of_birth: p.placeOfBirth || null,
      issue_date: p.issueDate || null,
      expiry_date: p.expiryDate || null
    }));
  }

  if (frontendData.itinerarySegments) {
    result.itinerary_segments = frontendData.itinerarySegments.map(s => ({
      segment_order: s.segmentOrder,
      segment_date: s.segmentDate || null,
      day_of_week: s.dayOfWeek || null,
      from_location: s.fromLocation,
      to_location: s.toLocation,
      departure_time: s.departureTime || null,
      arrival_time: s.arrivalTime || null,
      mode_of_travel: s.modeOfTravel || null,
      flight_number: s.flightNumber || null,
      flight_class: s.flightClass || null,
      purpose: s.purpose || null,
      remarks: s.remarks || null
    }));
  }

  if (frontendData.transportSegments) {
    result.transport_segments = frontendData.transportSegments.map(s => ({
      segment_order: s.segmentOrder,
      day_of_week: s.dayOfWeek || null,
      transport_type: s.transportType || null,
      pickup_location: s.pickupLocation,
      dropoff_location: s.dropoffLocation,
      pickup_date: s.pickupDate || null,
      pickup_time: s.pickupTime || null,
      passengers: s.passengers,
      vehicle_type_preference: s.vehicleTypePreference || null,
      notes: s.notes || null
    }));
  }

  return result;
}
