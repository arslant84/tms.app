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

export type TransportType =
  | 'Local'
  | 'Intercity'
  | 'Airport Transfer'
  | 'Charter'
  | 'Other';

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
  transportType: TransportType;
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
}

export interface TransportApprovalSubmissionData {
  additionalComments: string;
}

export interface TransportRequestForm extends TransportRequestData, TransportApprovalSubmissionData {
  id: string;
  request_number?: string;
  status: TransportRequestStatus;
  approvalWorkflow: TransportApprovalStep[];
  approval_steps?: any[]; // Legacy field for backward compatibility
  vehicle_assignments?: any[]; // Vehicle assignments for transport processing
  createdAt?: Date | string;
  submittedAt?: Date | string;
  updatedAt?: Date | string;
  createdBy?: string;
  updatedBy?: string;
  bookingDetails?: TransportBookingDetails;
}

export interface TransportApprovalStep {
  role: string; // e.g., 'Requestor', 'Line Manager', 'Department Focal', 'HOD'
  name: string;
  status: 'Current' | 'Pending' | 'Approved' | 'Rejected' | 'Not Started' | 'Cancelled' | 'Submitted';
  date?: Date | string;
  comments?: string;
}

export interface TransportBookingDetails {
  vehicleType?: string;
  vehicleNumber?: string;
  driverName?: string;
  driverContact?: string;
  pickupTime?: string;
  dropoffTime?: string;
  actualRoute?: string;
  bookingReference?: string;
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

export function toBackendFormat(frontendData: Partial<TransportRequestForm>): any {
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
    transport_details: frontendData.transportDetails?.map(detail => ({
      date: detail.date,
      day: detail.day,
      from: detail.from,
      to: detail.to,
      departure_time: detail.departureTime,
      transport_type: detail.transportType,
      number_of_passengers: detail.numberOfPassengers
    })) || [],

    // Submission data
    additional_comments: frontendData.additionalComments,

    // Booking details (for admin)
    booking_details: frontendData.bookingDetails ? {
      vehicle_type: frontendData.bookingDetails.vehicleType,
      vehicle_number: frontendData.bookingDetails.vehicleNumber,
      driver_name: frontendData.bookingDetails.driverName,
      driver_contact: frontendData.bookingDetails.driverContact,
      pickup_time: frontendData.bookingDetails.pickupTime,
      dropoff_time: frontendData.bookingDetails.dropoffTime,
      actual_route: frontendData.bookingDetails.actualRoute,
      booking_reference: frontendData.bookingDetails.bookingReference,
      additional_notes: frontendData.bookingDetails.additionalNotes
    } : undefined
  };
}

export function toFrontendFormat(backendData: any): TransportRequestForm {
  return {
    id: backendData.id?.toString() || '',
    request_number: backendData.request_number,

    // Requestor info
    requestorName: backendData.requestor_name || backendData.requestor?.get_full_name || '',
    staffId: backendData.staff_id || '',
    department: backendData.department || backendData.requestor?.department || '',
    position: backendData.position || '',

    // Request data
    purpose: backendData.purpose || '',
    tsrReference: backendData.tsr_reference,
    status: backendData.status || 'Draft',

    // Transport details array
    transportDetails: backendData.transport_details?.map((detail: any) => ({
      id: detail.id?.toString(),
      date: detail.date,
      day: detail.day || '',
      from: detail.from || '',
      to: detail.to || '',
      departureTime: detail.departure_time || '',
      transportType: detail.transport_type || 'Local',
      numberOfPassengers: detail.number_of_passengers || 1
    })) || [],

    // Submission data
    additionalComments: backendData.additional_comments || '',

    // Approval workflow
    approvalWorkflow: backendData.approval_workflow?.map((step: any) => ({
      role: step.role || step.step_role || '',
      name: step.name || step.step_name || '',
      status: step.status || 'Pending',
      date: step.date || step.step_date,
      comments: step.comments
    })) || [],
    
    // Legacy approval_steps for backward compatibility
    approval_steps: backendData.approval_steps || backendData.approval_workflow || [],

    // Vehicle assignments
    vehicle_assignments: backendData.vehicle_assignments || [],

    // Booking details
    bookingDetails: backendData.booking_details ? {
      vehicleType: backendData.booking_details.vehicle_type,
      vehicleNumber: backendData.booking_details.vehicle_number,
      driverName: backendData.booking_details.driver_name,
      driverContact: backendData.booking_details.driver_contact,
      pickupTime: backendData.booking_details.pickup_time,
      dropoffTime: backendData.booking_details.dropoff_time,
      actualRoute: backendData.booking_details.actual_route,
      bookingReference: backendData.booking_details.booking_reference,
      additionalNotes: backendData.booking_details.additional_notes
    } : undefined,

    // Timestamps
    createdAt: backendData.created_at,
    submittedAt: backendData.submitted_at,
    updatedAt: backendData.updated_at,
    createdBy: backendData.created_by,
    updatedBy: backendData.updated_by
  };
}
