import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, forkJoin, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';
import { extractData } from '../../../core/utils/api-response.handler';

/** Per-module fields shown in the approval detail view/template - a plain
 * interface (not an index signature) so templates can keep using ordinary
 * dot-notation bindings under this project's noPropertyAccessFromIndexSignature
 * tsconfig setting. Every field is optional since only the fields relevant
 * to ApprovalRequest.type are actually populated by each transform*ToApproval
 * method below. */
export interface ApprovalDetails {
  // trf
  travelType?: string;
  purpose?: string;
  destination?: string;
  departureDate?: string;
  returnDate?: string;
  estimatedCost?: number;
  // accommodation
  hotelName?: string;
  location?: string;
  checkInDate?: string;
  checkOutDate?: string;
  roomType?: string;
  // transport
  pickupLocation?: string;
  dropoffLocation?: string;
  pickupDate?: string;
  pickupTime?: string;
  // visa
  destinationCountry?: string;
  visaType?: string;
  travelDate?: string;
  // expense
  expenseType?: string;
  totalAmount?: number;
  currency?: string;
  claimDate?: string;
  hasReceipts?: boolean;
}

export interface ApprovalRequest {
  id: number;
  type: 'trf' | 'accommodation' | 'transport' | 'visa' | 'expense';
  title: string;
  requester: {
    id: number;
    name: string;
    department: string;
    email: string;
  };
  dateSubmitted: string;
  deadline?: string | null;
  priority: 'low' | 'medium' | 'high';
  status: string;
  currentApprovalStep?: string;
  details: ApprovalDetails;
}

export interface ApprovalAction {
  action: 'approve' | 'reject';
  comments?: string;
}

/** A department as the backend may return it: a plain name, or a nested object. */
type BackendDepartmentRef = string | { name?: string } | null | undefined;

/** Backend rows are loosely typed here on purpose - each module's actual
 * response shape lives in its own feature area (see e.g.
 * trf-management/trf-wizard.types.ts's TrfBackendResponse); this service only
 * reads a handful of fields off each, with the same snake_case/camelCase
 * fallback pattern used throughout the app. */
interface BackendPersonRef {
  id?: number;
  name?: string;
  department?: BackendDepartmentRef;
  email?: string;
}

interface BackendItinerarySegment {
  to_location?: string;
  destination?: string;
  segment_date?: string;
  departure_date?: string;
  arrival_date?: string;
  date?: string;
}

interface BackendTrfRow {
  id: number;
  travel_type?: string;
  travelType?: string;
  purpose?: string;
  requestor_id?: number;
  requestor?: BackendPersonRef;
  requestor_name?: string;
  department?: BackendDepartmentRef;
  tel_email?: string;
  created_at?: string;
  submission_date?: string;
  deadline?: string | null;
  status?: string;
  current_approval_step?: string;
  total_estimated_cost?: number;
  itinerary_segments?: BackendItinerarySegment[];
  itinerary?: BackendItinerarySegment[];
  domesticTravelDetails?: { itinerary?: BackendItinerarySegment[] };
  overseasTravelDetails?: { itinerary?: BackendItinerarySegment[] };
  externalPartiesTravelDetails?: { itinerary?: BackendItinerarySegment[] };
}

interface BackendAccommodationRow {
  id: number;
  hotel_name?: string;
  location?: string;
  requestor_id?: number;
  requestor?: BackendPersonRef;
  requestor_name?: string;
  department?: BackendDepartmentRef;
  email?: string;
  created_at?: string;
  submission_date?: string;
  deadline?: string | null;
  status?: string;
  current_approval_step?: string;
  check_in_date?: string;
  check_out_date?: string;
  room_type?: string;
}

interface BackendTransportRow {
  id: number;
  requestor_id?: number;
  requestor?: BackendPersonRef;
  requestor_name?: string;
  department?: BackendDepartmentRef;
  email?: string;
  created_at?: string;
  submission_date?: string;
  deadline?: string | null;
  status?: string;
  current_approval_step?: string;
  pickup_location?: string;
  dropoff_location?: string;
  pickup_date?: string;
  pickup_time?: string;
  estimated_cost?: number;
}

interface BackendVisaRow {
  id: number;
  destination_country?: string;
  applicant_id?: number;
  applicant?: BackendPersonRef;
  applicant_name?: string;
  department?: BackendDepartmentRef;
  email?: string;
  created_at?: string;
  submission_date?: string;
  deadline?: string | null;
  status?: string;
  current_approval_step?: string;
  visa_type?: string;
  travel_date?: string;
  return_date?: string;
  purpose?: string;
  estimated_cost?: number;
}

interface BackendExpenseRow {
  id: number;
  expense_type?: string;
  claimant_id?: number;
  claimant?: BackendPersonRef;
  claimant_name?: string;
  department?: BackendDepartmentRef;
  email?: string;
  created_at?: string;
  submission_date?: string;
  deadline?: string | null;
  status?: string;
  current_approval_step?: string;
  total_amount?: number;
  currency?: string;
  claim_date?: string;
  has_receipts?: boolean;
}

export interface ApprovalStats {
  total: number;
  byType: {
    trf: number;
    accommodation: number;
    transport: number;
    visa: number;
    expense: number;
  };
  byPriority: {
    high: number;
    medium: number;
    low: number;
  };
  overdue: number;
}

@Injectable({
  providedIn: 'root',
})
export class ApprovalsService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Get all pending approvals across all modules
   */
  getAllPendingApprovals(): Observable<ApprovalRequest[]> {
    return forkJoin({
      trfs: this.getPendingTrfs(),
      accommodations: this.getPendingAccommodations(),
      transports: this.getPendingTransports(),
      visas: this.getPendingVisas(),
      expenses: this.getPendingExpenses(),
    }).pipe(
      map(results => {
        return [
          ...results.trfs,
          ...results.accommodations,
          ...results.transports,
          ...results.visas,
          ...results.expenses,
        ];
      }),
      catchError(error => {
        console.error('Error fetching pending approvals:', error);
        return of([]);
      })
    );
  }

  /**
   * Get pending approvals by type
   */
  getPendingApprovalsByType(type: string): Observable<ApprovalRequest[]> {
    switch (type) {
      case 'trf':
        return this.getPendingTrfs();
      case 'accommodation':
        return this.getPendingAccommodations();
      case 'transport':
        return this.getPendingTransports();
      case 'visa':
        return this.getPendingVisas();
      case 'expense':
        return this.getPendingExpenses();
      default:
        return this.getAllPendingApprovals();
    }
  }

  /**
   * Get approval statistics
   */
  getApprovalStats(): Observable<ApprovalStats> {
    return this.getAllPendingApprovals().pipe(
      map(approvals => {
        const stats: ApprovalStats = {
          total: approvals.length,
          byType: {
            trf: 0,
            accommodation: 0,
            transport: 0,
            visa: 0,
            expense: 0,
          },
          byPriority: {
            high: 0,
            medium: 0,
            low: 0,
          },
          overdue: 0,
        };

        const today = new Date();
        approvals.forEach(approval => {
          // Count by type
          stats.byType[approval.type]++;

          // Count by priority
          stats.byPriority[approval.priority]++;

          // Count overdue
          if (approval.deadline && new Date(approval.deadline) < today) {
            stats.overdue++;
          }
        });

        return stats;
      })
    );
  }

  /**
   * Approve a request
   * @param type - The request type (trf, accommodation, transport, visa, expense)
   * @param id - The request ID
   * @param comments - Optional approval comments
   * @param stepRole - The current workflow step role (required - should come from workflow instance)
   */
  approveRequest(
    type: string,
    id: number,
    comments?: string,
    stepRole?: string
  ): Observable<unknown> {
    const url = this.getApprovalUrl(type, id, 'approve');
    const payload: { comments: string; step_role?: string } = { comments: comments || '' };

    if (stepRole) {
      payload.step_role = stepRole;
    }
    // Note: step_role should be provided by the caller based on the actual workflow step.
    // The backend WorkflowEngine will determine the correct step if not provided.

    return this.http.post(url, payload, { withCredentials: true });
  }

  /**
   * Reject a request
   * @param type - The request type (trf, accommodation, transport, visa, expense)
   * @param id - The request ID
   * @param comments - Optional rejection comments
   * @param stepRole - The current workflow step role (required - should come from workflow instance)
   */
  rejectRequest(
    type: string,
    id: number,
    comments?: string,
    stepRole?: string
  ): Observable<unknown> {
    const url = this.getApprovalUrl(type, id, 'reject');
    const payload: { comments: string; step_role?: string } = { comments: comments || '' };

    if (stepRole) {
      payload.step_role = stepRole;
    }
    // Note: step_role should be provided by the caller based on the actual workflow step.
    // The backend WorkflowEngine will determine the correct step if not provided.

    return this.http.post(url, payload, { withCredentials: true });
  }

  /**
   * Get approval history for a request
   */
  getApprovalHistory(type: string, id: number): Observable<Record<string, unknown>[]> {
    const url = this.getHistoryUrl(type, id);
    return this.http.get<Record<string, unknown>[]>(url, { withCredentials: true }).pipe(
      catchError(error => {
        console.error(`Error fetching approval history for ${type} ${id}:`, error);
        return of([]);
      })
    );
  }

  // Private helper methods

  private getPendingTrfs(): Observable<ApprovalRequest[]> {
    return this.http
      .get<unknown>(`${this.baseUrl}/trf/travel-requests/pending-approvals/`, {
        withCredentials: true,
      })
      .pipe(
        map(response => extractData<BackendTrfRow[]>(response) || []),
        map(trfs => trfs.map(trf => this.transformTrfToApproval(trf))),
        catchError(error => {
          console.error('Error fetching pending TRFs:', error);
          return of([]);
        })
      );
  }

  private getPendingAccommodations(): Observable<ApprovalRequest[]> {
    return this.http
      .get<unknown>(`${this.baseUrl}/accommodation/requests/pending-approvals/`, {
        withCredentials: true,
      })
      .pipe(
        map(response => extractData<BackendAccommodationRow[]>(response) || []),
        map(accs => accs.map(acc => this.transformAccommodationToApproval(acc))),
        catchError(error => {
          console.error('Error fetching pending accommodations:', error);
          return of([]);
        })
      );
  }

  private getPendingTransports(): Observable<ApprovalRequest[]> {
    return this.http
      .get<unknown>(`${this.baseUrl}/transport/requests/pending-approvals/`, {
        withCredentials: true,
      })
      .pipe(
        map(response => extractData<BackendTransportRow[]>(response) || []),
        map(transports =>
          transports.map(transport => this.transformTransportToApproval(transport))
        ),
        catchError(error => {
          console.error('Error fetching pending transports:', error);
          return of([]);
        })
      );
  }

  private getPendingVisas(): Observable<ApprovalRequest[]> {
    return this.http
      .get<unknown>(`${this.baseUrl}/visa/applications/pending-approvals/`, {
        withCredentials: true,
      })
      .pipe(
        map(response => extractData<BackendVisaRow[]>(response) || []),
        map(visas => visas.map(visa => this.transformVisaToApproval(visa))),
        catchError(error => {
          console.error('Error fetching pending visas:', error);
          return of([]);
        })
      );
  }

  private getPendingExpenses(): Observable<ApprovalRequest[]> {
    return this.http
      .get<unknown>(`${this.baseUrl}/expenses/claims/pending-approvals/`, {
        withCredentials: true,
      })
      .pipe(
        map(response => extractData<BackendExpenseRow[]>(response) || []),
        map(expenses => expenses.map(expense => this.transformExpenseToApproval(expense))),
        catchError(error => {
          console.error('Error fetching pending expenses:', error);
          return of([]);
        })
      );
  }

  // Transform backend data to unified ApprovalRequest format

  // High complexity here is field-name fallback chains (backend snake_case
  // vs legacy camelCase aliases per field, same pattern used throughout the
  // TRF wizard - see e.g. trf-edit-loader.service.ts), not branchy logic.
  // eslint-disable-next-line complexity
  private transformTrfToApproval(trf: BackendTrfRow): ApprovalRequest {
    // Extract itinerary from nested structure based on travel type
    let itinerary: BackendItinerarySegment[] = [];
    const travelType = trf.travel_type || trf.travelType;

    if (travelType === 'Domestic') {
      const domesticDetails = trf.domesticTravelDetails || {};
      itinerary = domesticDetails.itinerary || trf.itinerary_segments || trf.itinerary || [];
    } else if (travelType === 'Overseas') {
      const overseasDetails = trf.overseasTravelDetails || {};
      itinerary = overseasDetails.itinerary || trf.itinerary_segments || trf.itinerary || [];
    } else if (travelType === 'External Parties') {
      const externalDetails = trf.externalPartiesTravelDetails || {};
      itinerary = externalDetails.itinerary || trf.itinerary_segments || trf.itinerary || [];
    } else {
      // Fallback for legacy data
      itinerary = trf.itinerary_segments || trf.itinerary || [];
    }

    const destination = this.extractDestination(itinerary);
    const departureDate = this.extractDepartureDate(itinerary);
    const returnDate = this.extractReturnDate(itinerary);

    return {
      id: trf.id,
      type: 'trf',
      title: `${trf.travel_type || 'Travel'} - ${trf.purpose || 'Travel Request'}`,
      requester: {
        id: trf.requestor_id || trf.requestor?.id || 0,
        name: trf.requestor_name || trf.requestor?.name || 'Unknown',
        department: this.extractDepartmentName(trf.department || trf.requestor?.department),
        email: trf.tel_email || trf.requestor?.email || '',
      },
      dateSubmitted: trf.created_at || trf.submission_date || '',
      deadline: trf.deadline || null,
      priority: this.determinePriority(trf.travel_type || 'trf', trf.created_at),
      status: trf.status || 'Pending',
      currentApprovalStep: trf.current_approval_step,
      details: {
        travelType: trf.travel_type,
        purpose: trf.purpose,
        destination: destination,
        departureDate: departureDate,
        returnDate: returnDate,
        estimatedCost: trf.total_estimated_cost || 0,
      },
    };
  }

  private transformAccommodationToApproval(acc: BackendAccommodationRow): ApprovalRequest {
    return {
      id: acc.id,
      type: 'accommodation',
      title: `Accommodation - ${acc.hotel_name || acc.location || 'Request'}`,
      requester: {
        id: acc.requestor_id || acc.requestor?.id || 0,
        name: acc.requestor_name || acc.requestor?.name || 'Unknown',
        department: this.extractDepartmentName(acc.department || acc.requestor?.department),
        email: acc.email || acc.requestor?.email || '',
      },
      dateSubmitted: acc.created_at || acc.submission_date || '',
      deadline: acc.deadline || null,
      priority: this.determinePriority('accommodation', acc.check_in_date),
      status: acc.status || 'Pending',
      currentApprovalStep: acc.current_approval_step,
      details: {
        hotelName: acc.hotel_name,
        location: acc.location,
        checkInDate: acc.check_in_date,
        checkOutDate: acc.check_out_date,
        roomType: acc.room_type,
      },
    };
  }

  private transformTransportToApproval(transport: BackendTransportRow): ApprovalRequest {
    return {
      id: transport.id,
      type: 'transport',
      title: 'Transport Request',
      requester: {
        id: transport.requestor_id || transport.requestor?.id || 0,
        name: transport.requestor_name || transport.requestor?.name || 'Unknown',
        department: this.extractDepartmentName(
          transport.department || transport.requestor?.department
        ),
        email: transport.email || transport.requestor?.email || '',
      },
      dateSubmitted: transport.created_at || transport.submission_date || '',
      deadline: transport.deadline || null,
      priority: this.determinePriority('transport', transport.pickup_date),
      status: transport.status || 'Pending',
      currentApprovalStep: transport.current_approval_step,
      details: {
        pickupLocation: transport.pickup_location,
        dropoffLocation: transport.dropoff_location,
        pickupDate: transport.pickup_date,
        pickupTime: transport.pickup_time,
        estimatedCost: transport.estimated_cost || 0,
      },
    };
  }

  private transformVisaToApproval(visa: BackendVisaRow): ApprovalRequest {
    return {
      id: visa.id,
      type: 'visa',
      title: `Visa - ${visa.destination_country || 'Application'}`,
      requester: {
        id: visa.applicant_id || visa.applicant?.id || 0,
        name: visa.applicant_name || visa.applicant?.name || 'Unknown',
        department: this.extractDepartmentName(visa.department || visa.applicant?.department),
        email: visa.email || visa.applicant?.email || '',
      },
      dateSubmitted: visa.created_at || visa.submission_date || '',
      deadline: visa.deadline || null,
      priority: this.determinePriority('visa', visa.travel_date),
      status: visa.status || 'Pending',
      currentApprovalStep: visa.current_approval_step,
      details: {
        destinationCountry: visa.destination_country,
        visaType: visa.visa_type,
        travelDate: visa.travel_date,
        returnDate: visa.return_date,
        purpose: visa.purpose,
        estimatedCost: visa.estimated_cost || 0,
      },
    };
  }

  // High complexity here is field-name fallback chains, same as
  // transformTrfToApproval above, not branchy logic.
  // eslint-disable-next-line complexity
  private transformExpenseToApproval(expense: BackendExpenseRow): ApprovalRequest {
    return {
      id: expense.id,
      type: 'expense',
      title: `Expense Claim - ${expense.expense_type || 'Reimbursement'}`,
      requester: {
        id: expense.claimant_id || expense.claimant?.id || 0,
        name: expense.claimant_name || expense.claimant?.name || 'Unknown',
        department: this.extractDepartmentName(expense.department || expense.claimant?.department),
        email: expense.email || expense.claimant?.email || '',
      },
      dateSubmitted: expense.created_at || expense.submission_date || '',
      deadline: expense.deadline || null,
      priority: this.determinePriority('expense', expense.created_at),
      status: expense.status || 'Pending',
      currentApprovalStep: expense.current_approval_step,
      details: {
        expenseType: expense.expense_type,
        totalAmount: expense.total_amount || 0,
        currency: expense.currency || 'MYR',
        claimDate: expense.claim_date,
        hasReceipts: expense.has_receipts || false,
      },
    };
  }

  // Helper methods

  private extractDepartmentName(department: BackendDepartmentRef): string {
    if (!department) {
      return 'Unknown';
    }
    if (typeof department === 'string') {
      return department;
    }
    return department.name || 'Unknown';
  }

  private determinePriority(type: string, dateField?: string): 'low' | 'medium' | 'high' {
    if (!dateField) return 'medium';

    const targetDate = new Date(dateField);
    const today = new Date();
    const daysUntil = Math.ceil((targetDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (daysUntil < 7) return 'high';
    if (daysUntil < 14) return 'medium';
    return 'low';
  }

  private extractDestination(itinerary: BackendItinerarySegment[]): string {
    if (!itinerary || itinerary.length === 0) return 'N/A';
    // Backend uses 'to_location' not 'destination'
    const lastSegment = itinerary[itinerary.length - 1];
    return lastSegment?.to_location || lastSegment?.destination || 'N/A';
  }

  private extractDepartureDate(itinerary: BackendItinerarySegment[]): string {
    if (!itinerary || itinerary.length === 0) return '';
    // Backend uses 'segment_date' not 'departure_date'
    const firstSegment = itinerary[0];
    return firstSegment?.segment_date || firstSegment?.departure_date || firstSegment?.date || '';
  }

  private extractReturnDate(itinerary: BackendItinerarySegment[]): string {
    if (!itinerary || itinerary.length === 0) return '';
    // Backend uses 'segment_date' not 'arrival_date'
    const lastSegment = itinerary[itinerary.length - 1];
    return lastSegment?.segment_date || lastSegment?.arrival_date || lastSegment?.date || '';
  }

  private getApprovalUrl(type: string, id: number, action: 'approve' | 'reject'): string {
    const baseUrls: { [key: string]: string } = {
      trf: `${this.baseUrl}/trf/travel-requests/${id}/${action}/`,
      accommodation: `${this.baseUrl}/accommodation/requests/${id}/${action}/`,
      transport: `${this.baseUrl}/transport/requests/${id}/${action}/`,
      visa: `${this.baseUrl}/visa/applications/${id}/${action}/`,
      expense: `${this.baseUrl}/expenses/claims/${id}/${action}/`,
    };
    return baseUrls[type] || '';
  }

  private getHistoryUrl(type: string, id: number): string {
    const baseUrls: { [key: string]: string } = {
      trf: `${this.baseUrl}/trf/travel-requests/${id}/approval-history/`,
      accommodation: `${this.baseUrl}/accommodation/requests/${id}/approval-history/`,
      transport: `${this.baseUrl}/transport/requests/${id}/approval-history/`,
      visa: `${this.baseUrl}/visa/applications/${id}/approval-history/`,
      expense: `${this.baseUrl}/expenses/claims/${id}/approval-history/`,
    };
    return baseUrls[type] || '';
  }
}
