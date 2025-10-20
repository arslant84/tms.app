/**
 * Accommodation Module - Comprehensive Type Definitions
 *
 * This model matches the React source (pctsb.syntra) exactly.
 * Created: 2025-10-19
 * Purpose: Provide type-safe interfaces for accommodation requests, bookings, and related entities
 */

// ============================================================================
// ENUMS & TYPES
// ============================================================================

/**
 * Location types matching PETRONAS facilities
 */
export type LocationType = 'Ashgabat' | 'Kiyanly' | 'Turkmenbashy';

/**
 * Guest gender for room assignment
 */
export type GuestGender = 'Male' | 'Female';

/**
 * Booking status lifecycle
 */
export type BookingStatus =
  | 'Draft'           // Initial creation
  | 'Pending'         // Awaiting approval
  | 'Confirmed'       // Approved and room assigned
  | 'Checked-in'      // Guest checked in
  | 'Checked-out'     // Guest checked out
  | 'Cancelled'       // Booking cancelled
  | 'Rejected'        // Request rejected
  | 'Blocked';        // Room blocked for maintenance

/**
 * Room types available
 */
export type RoomType = 'Single' | 'Double' | 'Suite' | 'Tent';

/**
 * Room status
 */
export type RoomStatus = 'Available' | 'Occupied' | 'Maintenance' | 'Reserved';

// ============================================================================
// CORE INTERFACES
// ============================================================================

/**
 * Staff House (Accommodation Facility)
 * Represents a physical building/facility that contains rooms
 */
export interface StaffHouse {
  id: number;
  name: string;
  location: LocationType;
  address?: string;
  description?: string;
  totalRooms?: number;
  availableRooms?: number;
  createdAt: Date | string;
  updatedAt: Date | string;
}

/**
 * Room within a Staff House
 */
export interface Room {
  id: number;
  staffHouseId: number;
  staffHouseName?: string;
  name: string;
  roomType: RoomType;
  capacity: number;
  status: RoomStatus;
  floor?: string;
  amenities?: string[];
  createdAt: Date | string;
  updatedAt: Date | string;
}

/**
 * Daily Booking Record
 * Represents a single day's booking for a room
 */
export interface DailyBooking {
  id: number;
  staffHouseId: number;
  staffHouseName?: string;
  roomId: number;
  roomName?: string;
  staffId?: number;
  staffName?: string;
  date: Date | string;
  trfId?: number;
  status: BookingStatus;
  notes?: string;
  checkInTime?: string;    // HH:MM format
  checkOutTime?: string;   // HH:MM format
  createdAt: Date | string;
  updatedAt: Date | string;
}

/**
 * Travel Details nested within accommodation request
 */
export interface TravelDetails {
  from?: string;
  to?: string;
  purpose?: string;
}

/**
 * Rejection Details
 */
export interface RejectionDetails {
  rejectedBy?: string;
  rejectedAt?: Date | string;
  reason?: string;
}

/**
 * Approval Workflow Step
 */
export interface ApprovalStep {
  step: number;
  role: string;
  approver?: string;
  status: 'Pending' | 'Approved' | 'Rejected';
  comments?: string;
  timestamp?: Date | string;
}

/**
 * Main Accommodation Request Details
 * This is the primary interface matching React's AccommodationRequestDetails
 */
export interface AccommodationRequestDetails {
  // Identification
  id: string | number;
  trfId?: string | number;

  // Requestor Information
  requestorName: string;
  requestorId: string;
  requestorGender: GuestGender;
  department: string;
  position?: string;
  costCenter?: string;
  telEmail?: string;
  email?: string;

  // Location & Room Preferences
  location: LocationType;
  requestedCheckInDate: Date | string;
  requestedCheckOutDate: Date | string;
  requestedRoomType?: RoomType;

  // Booking Status
  status: BookingStatus;

  // Assignment Details (filled after approval)
  assignedRoomId?: number;
  assignedRoomName?: string;
  assignedStaffHouseId?: number;
  assignedStaffHouseName?: string;

  // Flight Details
  flightArrivalTime?: string;      // HH:MM format
  flightDepartureTime?: string;    // HH:MM format

  // Additional Information
  specialRequests?: string;
  notes?: string;
  additionalComments?: string;

  // Timestamps
  submittedDate: Date | string;
  lastUpdatedDate: Date | string;
  createdAt?: Date | string;
  updatedAt?: Date | string;

  // Related Data
  dailyBookings?: DailyBooking[];
  rejectionDetails?: RejectionDetails;
  approvalWorkflow?: ApprovalStep[];

  // Estimated Cost
  estimatedCost?: number;

  // Travel Details
  travelDetails?: TravelDetails;
}

// ============================================================================
// BACKEND COMPATIBILITY INTERFACES
// ============================================================================

/**
 * Backend format for Staff House
 */
export interface StaffHouseBackend {
  id: number;
  name: string;
  location: string;
  address?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Backend format for Room
 */
export interface RoomBackend {
  id: number;
  staff_house: number;
  staff_house_name?: string;
  name: string;
  room_type?: string;
  capacity: number;
  status: string;
  created_at: string;
  updated_at: string;
}

/**
 * Backend format for Daily Booking
 */
export interface DailyBookingBackend {
  id: number;
  staff_house: number;
  staff_house_name?: string;
  room: number;
  room_name?: string;
  staff?: number;
  staff_name?: string;
  date: string;
  trf?: number;
  status: string;
  notes?: string;
  check_in_time?: string;
  check_out_time?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Backend format for Accommodation Request
 */
export interface AccommodationRequestBackend {
  id: number;
  requestor_name: string;
  staff_id?: string;
  department?: string;
  position?: string;
  cost_center?: string;
  tel_email?: string;
  email?: string;
  location?: string;
  requested_check_in_date?: string;
  requested_check_out_date?: string;
  requested_room_type?: string;
  status: string;
  assigned_room?: number;
  assigned_room_name?: string;
  assigned_staff_house?: number;
  assigned_staff_house_name?: string;
  flight_arrival_time?: string;
  flight_departure_time?: string;
  special_requests?: string;
  notes?: string;
  additional_comments?: string;
  estimated_cost?: number;
  submitted_at?: string;
  created_at: string;
  updated_at: string;
  bookings?: DailyBookingBackend[];
  trf?: number;
  requestor_gender?: string;
  additional_data?: any;
}

// ============================================================================
// CONVERSION HELPERS
// ============================================================================

/**
 * Convert StaffHouse from backend format to frontend format
 */
export function staffHouseToFrontend(backend: StaffHouseBackend): StaffHouse {
  return {
    id: backend.id,
    name: backend.name,
    location: backend.location as LocationType,
    address: backend.address,
    description: backend.description,
    createdAt: backend.created_at,
    updatedAt: backend.updated_at
  };
}

/**
 * Convert Room from backend format to frontend format
 */
export function roomToFrontend(backend: RoomBackend): Room {
  return {
    id: backend.id,
    staffHouseId: backend.staff_house,
    staffHouseName: backend.staff_house_name,
    name: backend.name,
    roomType: (backend.room_type || 'Single') as RoomType,
    capacity: backend.capacity,
    status: (backend.status || 'Available') as RoomStatus,
    createdAt: backend.created_at,
    updatedAt: backend.updated_at
  };
}

/**
 * Convert DailyBooking from backend format to frontend format
 */
export function dailyBookingToFrontend(backend: DailyBookingBackend): DailyBooking {
  return {
    id: backend.id,
    staffHouseId: backend.staff_house,
    staffHouseName: backend.staff_house_name,
    roomId: backend.room,
    roomName: backend.room_name,
    staffId: backend.staff,
    staffName: backend.staff_name,
    date: backend.date,
    trfId: backend.trf,
    status: (backend.status || 'Pending') as BookingStatus,
    notes: backend.notes,
    checkInTime: backend.check_in_time,
    checkOutTime: backend.check_out_time,
    createdAt: backend.created_at,
    updatedAt: backend.updated_at
  };
}

/**
 * Convert AccommodationRequest from backend format to frontend format
 */
export function accommodationToFrontend(
  backend: AccommodationRequestBackend
): AccommodationRequestDetails {
  // Convert daily bookings if present
  const dailyBookings = backend.bookings?.map(dailyBookingToFrontend) || [];

  // Extract rejection details from additional_data if present
  const rejectionDetails: RejectionDetails | undefined = backend.additional_data?.rejection
    ? {
        rejectedBy: backend.additional_data.rejection.rejected_by,
        rejectedAt: backend.additional_data.rejection.rejected_at,
        reason: backend.additional_data.rejection.reason
      }
    : undefined;

  // Extract approval workflow from additional_data if present
  const approvalWorkflow: ApprovalStep[] | undefined = backend.additional_data?.approval_workflow;

  // Extract date fields from additional_data (primary source) or direct fields (fallback)
  const checkInDate = backend.additional_data?.requested_check_in_date ||
                      backend.requested_check_in_date ||
                      '';
  const checkOutDate = backend.additional_data?.requested_check_out_date ||
                       backend.requested_check_out_date ||
                       '';
  const roomType = backend.additional_data?.requested_room_type ||
                   backend.requested_room_type;
  const gender = backend.additional_data?.requestor_gender ||
                 backend.requestor_gender ||
                 'Male';
  const location = backend.additional_data?.location ||
                   backend.location ||
                   'Ashgabat';
  const flightArrival = backend.additional_data?.flight_arrival_time ||
                        backend.flight_arrival_time ||
                        '';
  const flightDeparture = backend.additional_data?.flight_departure_time ||
                          backend.flight_departure_time ||
                          '';
  const requests = backend.additional_data?.special_requests ||
                   backend.special_requests ||
                   '';

  return {
    id: backend.id,
    trfId: backend.trf,
    requestorName: backend.requestor_name,
    requestorId: backend.staff_id || '',
    requestorGender: gender as GuestGender,
    department: backend.department || '',
    position: backend.position,
    costCenter: backend.cost_center,
    telEmail: backend.tel_email,
    email: backend.email,
    location: location as LocationType,
    requestedCheckInDate: checkInDate,
    requestedCheckOutDate: checkOutDate,
    requestedRoomType: roomType as RoomType,
    status: (backend.status || 'Draft') as BookingStatus,
    assignedRoomId: backend.assigned_room,
    assignedRoomName: backend.assigned_room_name,
    assignedStaffHouseId: backend.assigned_staff_house,
    assignedStaffHouseName: backend.assigned_staff_house_name,
    flightArrivalTime: flightArrival,
    flightDepartureTime: flightDeparture,
    specialRequests: requests,
    notes: backend.notes,
    additionalComments: backend.additional_comments,
    submittedDate: backend.submitted_at || backend.created_at,
    lastUpdatedDate: backend.updated_at,
    createdAt: backend.created_at,
    updatedAt: backend.updated_at,
    dailyBookings,
    rejectionDetails,
    approvalWorkflow,
    estimatedCost: backend.estimated_cost,
    travelDetails: backend.additional_data?.travel_details
  };
}

/**
 * Convert AccommodationRequest from frontend format to backend format
 */
export function accommodationToBackend(
  frontend: AccommodationRequestDetails
): Partial<AccommodationRequestBackend> {
  // Build additional_data object
  const additionalData: any = {};

  if (frontend.rejectionDetails) {
    additionalData.rejection = {
      rejected_by: frontend.rejectionDetails.rejectedBy,
      rejected_at: frontend.rejectionDetails.rejectedAt,
      reason: frontend.rejectionDetails.reason
    };
  }

  if (frontend.approvalWorkflow) {
    additionalData.approval_workflow = frontend.approvalWorkflow;
  }

  if (frontend.travelDetails) {
    additionalData.travel_details = frontend.travelDetails;
  }

  return {
    requestor_name: frontend.requestorName,
    staff_id: frontend.requestorId,
    requestor_gender: frontend.requestorGender,
    department: frontend.department,
    position: frontend.position,
    cost_center: frontend.costCenter,
    tel_email: frontend.telEmail,
    email: frontend.email,
    location: frontend.location,
    requested_check_in_date: typeof frontend.requestedCheckInDate === 'string'
      ? frontend.requestedCheckInDate
      : frontend.requestedCheckInDate?.toISOString().split('T')[0],
    requested_check_out_date: typeof frontend.requestedCheckOutDate === 'string'
      ? frontend.requestedCheckOutDate
      : frontend.requestedCheckOutDate?.toISOString().split('T')[0],
    requested_room_type: frontend.requestedRoomType,
    status: frontend.status,
    assigned_room: frontend.assignedRoomId,
    assigned_staff_house: frontend.assignedStaffHouseId,
    flight_arrival_time: frontend.flightArrivalTime,
    flight_departure_time: frontend.flightDepartureTime,
    special_requests: frontend.specialRequests,
    notes: frontend.notes,
    additional_comments: frontend.additionalComments,
    estimated_cost: frontend.estimatedCost,
    trf: typeof frontend.trfId === 'number' ? frontend.trfId : (frontend.trfId ? parseInt(frontend.trfId as string) : undefined),
    additional_data: Object.keys(additionalData).length > 0 ? additionalData : undefined
  };
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Calculate number of nights between check-in and check-out dates
 */
export function calculateNights(checkIn: Date | string, checkOut: Date | string): number {
  const checkInDate = typeof checkIn === 'string' ? new Date(checkIn) : checkIn;
  const checkOutDate = typeof checkOut === 'string' ? new Date(checkOut) : checkOut;

  if (isNaN(checkInDate.getTime()) || isNaN(checkOutDate.getTime())) {
    return 0;
  }

  const diffTime = checkOutDate.getTime() - checkInDate.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays > 0 ? diffDays : 0;
}

/**
 * Get status badge class based on booking status
 */
export function getStatusBadgeClass(status: BookingStatus): string {
  const statusMap: Record<BookingStatus, string> = {
    'Draft': 'badge-secondary',
    'Pending': 'badge-warning',
    'Confirmed': 'badge-info',
    'Checked-in': 'badge-primary',
    'Checked-out': 'badge-success',
    'Cancelled': 'badge-secondary',
    'Rejected': 'badge-danger',
    'Blocked': 'badge-dark'
  };

  return statusMap[status] || 'badge-secondary';
}

/**
 * Check if accommodation request is editable based on status
 */
export function isEditable(status: BookingStatus): boolean {
  return ['Draft', 'Pending', 'Rejected'].includes(status);
}

/**
 * Check if accommodation request can be cancelled
 */
export function isCancellable(status: BookingStatus): boolean {
  return ['Pending', 'Confirmed'].includes(status);
}

/**
 * Check if accommodation request can be deleted
 */
export function isDeletable(status: BookingStatus): boolean {
  return ['Draft', 'Rejected'].includes(status);
}

/**
 * Generate date range array between two dates
 */
export function generateDateRange(startDate: Date | string, endDate: Date | string): Date[] {
  const start = typeof startDate === 'string' ? new Date(startDate) : startDate;
  const end = typeof endDate === 'string' ? new Date(endDate) : endDate;
  const dates: Date[] = [];

  if (isNaN(start.getTime()) || isNaN(end.getTime()) || start > end) {
    return dates;
  }

  const currentDate = new Date(start);
  while (currentDate <= end) {
    dates.push(new Date(currentDate));
    currentDate.setDate(currentDate.getDate() + 1);
  }

  return dates;
}

/**
 * Format time string (HH:MM) to 12-hour format with AM/PM
 */
export function formatTime12Hour(time: string | undefined): string {
  if (!time || !/^[0-2]\d:[0-5]\d$/.test(time)) return 'N/A';

  const [hours, minutes] = time.split(':').map(Number);
  const period = hours >= 12 ? 'PM' : 'AM';
  const hour12 = hours % 12 || 12;

  return `${hour12}:${minutes.toString().padStart(2, '0')} ${period}`;
}
