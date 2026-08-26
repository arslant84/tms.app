/**
 * Transport Request Models
 * Matches React source project structure from pctsb.syntra/src/types/transport.ts
 * NO cost fields - exactly as per source
 */

export type TransportRequestStatus =
  | 'Draft'
  | 'Pending Department Focal'
  | 'Pending Line Manager'
  | 'Pending HOD'
  | 'Approved'
  | 'Processing with Transport Admin'
  | 'Completed'
  | 'Rejected'
  | 'Cancelled';

export interface TransportRequestorInformation {
  requestorName: string;
  staffId: string;
  department: string;
  position: string;
}

export interface TransportDetail {
  id?: string;
  date: Date | string | null;
  day: string;
  from: string;
  to: string;
  departureTime: string;
  numberOfPassengers: number;
}

export interface TransportRequestData {
  requestorName?: string;
  staffId?: string;
  department?: string;
  position?: string;

  purpose: string;
  transportDetails: TransportDetail[];
  tsrReference?: string; // Reference to TSR if created from TSR
  /** Id of the TravelRequest this was created from, if embedded in a TSR (null/undefined for ad-hoc requests). */
  trfId?: number;
  /** Request number of the linked TravelRequest, if embedded (e.g. "TSR-..."). */
  trfRequestNumber?: string;
}

export interface TransportApprovalSubmissionData {
  additionalComments: string;
}

export interface TransportRequestForm
  extends TransportRequestData, TransportApprovalSubmissionData {
  id: string;
  request_number?: string;
  status: TransportRequestStatus;
  approvalWorkflow: TransportApprovalStep[];
  approval_steps?: TransportApprovalStep[]; // Legacy field for backward compatibility
  vehicle_assignments?: unknown[]; // Vehicle assignments for transport processing
  selected_approvers?: { [stepOrder: number]: number }; // Selected approvers for workflow steps
  skipped_steps?: { [stepOrder: number]: string | null }; // Skipped workflow steps
  /** Step orders (ints) that already have an APPROVED WorkflowStepExecution - see trf-wizard.types.ts. */
  approved_step_orders?: number[];
  createdAt?: Date | string;
  submittedAt?: Date | string;
  updatedAt?: Date | string;
  createdBy?: string;
  updatedBy?: string;
  /** Id of the User who owns this request (from the detail serializer's
   * nested `requestor` object) - null on list-view rows, which only send
   * requestor_name/department, not the full nested user. */
  requestorId?: number | null;
  bookingDetails?: TransportBookingDetails;
}

export interface TransportApprovalStep {
  role: string; // e.g., 'Requestor', 'Line Manager', 'Department Focal', 'HOD'
  name: string;
  status:
    | 'Current'
    | 'Pending'
    | 'Approved'
    | 'Rejected'
    | 'Not Started'
    | 'Cancelled'
    | 'Submitted';
  date?: Date | string;
  comments?: string;
}

export interface TransportBookingDetails {
  vehicleNumber?: string;
  driverName?: string;
  driverContact?: string;
  pickupTime?: string;
  additionalNotes?: string;
}

export interface TransportRequestSummary {
  id: string;
  requestorName: string;
  department: string;
  purpose: string;
  status: TransportRequestStatus;
  submittedAt?: Date | string;
  tsrReference?: string;
  bookingDetails?: TransportBookingDetails;
}

// Helper functions for backend/frontend conversion

interface TransportBackendApprovalStep {
  role?: string;
  step_role?: string;
  name?: string;
  step_name?: string;
  status?: string;
  date?: string;
  step_date?: string;
  comments?: string;
}

interface TransportBackendTransportDetail {
  id?: string | number;
  date?: string;
  day?: string;
  from?: string;
  to?: string;
  departure_time?: string;
  number_of_passengers?: number;
}

interface TransportBackendData {
  id?: string | number;
  request_number?: string;
  requestor_name?: string;
  requestor?: { id?: number; get_full_name?: string; department?: string | { name?: string } };
  staff_id?: string;
  department?: string | { name?: string };
  position?: string;
  purpose?: string;
  tsr_reference?: string;
  trf?: number;
  trf_request_number?: string;
  status?: string;
  transport_details?: TransportBackendTransportDetail[];
  additional_comments?: string;
  approval_workflow?: TransportBackendApprovalStep[];
  approval_steps?: TransportBackendApprovalStep[];
  vehicle_assignments?: unknown[];
  selected_approvers?: { [stepOrder: number]: number };
  skipped_steps?: { [stepOrder: number]: string | null };
  approved_step_orders?: number[];
  booking_details?: {
    vehicle_number?: string;
    driver_name?: string;
    driver_contact?: string;
    pickup_time?: string;
    additional_notes?: string;
  };
  created_at?: string;
  submitted_at?: string;
  updated_at?: string;
  created_by?: string;
  updated_by?: string;
}

export function toBackendFormat(
  frontendData: Partial<TransportRequestForm>
): Record<string, unknown> {
  return {
    // Requestor info
    requestor_name: frontendData.requestorName,
    staff_id: frontendData.staffId,
    department: frontendData.department,
    position: frontendData.position,

    // Request data
    purpose: frontendData.purpose,
    tsr_reference: frontendData.tsrReference,
    status: frontendData.status || 'Draft',

    // Transport details array
    transport_details:
      frontendData.transportDetails?.map(detail => ({
        date: detail.date,
        day: detail.day,
        from: detail.from,
        to: detail.to,
        departure_time: detail.departureTime,
        number_of_passengers: detail.numberOfPassengers,
      })) || [],

    // Submission data
    additional_comments: frontendData.additionalComments,

    // Booking details (for admin)
    booking_details: frontendData.bookingDetails
      ? {
          vehicle_number: frontendData.bookingDetails.vehicleNumber,
          driver_name: frontendData.bookingDetails.driverName,
          driver_contact: frontendData.bookingDetails.driverContact,
          pickup_time: frontendData.bookingDetails.pickupTime,
          additional_notes: frontendData.bookingDetails.additionalNotes,
        }
      : undefined,
  };
}

function extractDepartmentName(department: string | { name?: string } | undefined | null): string {
  if (!department) {
    return '';
  }
  if (typeof department === 'string') {
    return department;
  }
  return department.name || '';
}

function mapTransportDetail(detail: TransportBackendTransportDetail): TransportDetail {
  return {
    id: detail.id?.toString(),
    date: detail.date || null,
    day: detail.day || '',
    from: detail.from || '',
    to: detail.to || '',
    departureTime: detail.departure_time || '',
    numberOfPassengers: detail.number_of_passengers || 1,
  };
}

function mapApprovalStep(step: TransportBackendApprovalStep): TransportApprovalStep {
  return {
    role: step.role || step.step_role || '',
    name: step.name || step.step_name || '',
    status: (step.status || 'Pending') as TransportApprovalStep['status'],
    date: step.date || step.step_date,
    comments: step.comments,
  };
}

function mapRequestorInfo(backendData: TransportBackendData) {
  return {
    requestorName: backendData.requestor_name || backendData.requestor?.get_full_name || '',
    staffId: backendData.staff_id || '',
    department: extractDepartmentName(backendData.department || backendData.requestor?.department),
    position: backendData.position || '',
    requestorId: backendData.requestor?.id ?? null,
  };
}

function mapWorkflowFields(backendData: TransportBackendData) {
  return {
    approvalWorkflow: backendData.approval_workflow?.map(mapApprovalStep) || [],
    approval_steps: (backendData.approval_steps || backendData.approval_workflow || []).map(
      mapApprovalStep
    ),
    selected_approvers: backendData.selected_approvers || {},
    skipped_steps: backendData.skipped_steps || {},
    approved_step_orders: backendData.approved_step_orders || [],
  };
}

function mapBookingDetails(backendData: TransportBackendData): TransportBookingDetails | undefined {
  if (!backendData.booking_details) {
    return undefined;
  }
  return {
    vehicleNumber: backendData.booking_details.vehicle_number,
    driverName: backendData.booking_details.driver_name,
    driverContact: backendData.booking_details.driver_contact,
    pickupTime: backendData.booking_details.pickup_time,
    additionalNotes: backendData.booking_details.additional_notes,
  };
}

export function toFrontendFormat(backendData: TransportBackendData): TransportRequestForm {
  return {
    id: backendData.id?.toString() || '',
    request_number: backendData.request_number,
    ...mapRequestorInfo(backendData),

    // Request data
    purpose: backendData.purpose || '',
    tsrReference: backendData.tsr_reference,
    trfId: backendData.trf || undefined,
    trfRequestNumber: backendData.trf_request_number || undefined,
    status: (backendData.status || 'Draft') as TransportRequestStatus,

    // Transport details array
    transportDetails: backendData.transport_details?.map(mapTransportDetail) || [],

    // Submission data
    additionalComments: backendData.additional_comments || '',

    ...mapWorkflowFields(backendData),

    // Vehicle assignments
    vehicle_assignments: backendData.vehicle_assignments || [],

    // Booking details
    bookingDetails: mapBookingDetails(backendData),

    // Timestamps
    createdAt: backendData.created_at,
    submittedAt: backendData.submitted_at,
    updatedAt: backendData.updated_at,
    createdBy: backendData.created_by,
    updatedBy: backendData.updated_by,
  };
}
