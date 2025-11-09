import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, forkJoin, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';

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
  details: any;
}

export interface ApprovalAction {
  action: 'approve' | 'reject';
  comments?: string;
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
  providedIn: 'root'
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
      expenses: this.getPendingExpenses()
    }).pipe(
      map(results => {
        return [
          ...results.trfs,
          ...results.accommodations,
          ...results.transports,
          ...results.visas,
          ...results.expenses
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
            expense: 0
          },
          byPriority: {
            high: 0,
            medium: 0,
            low: 0
          },
          overdue: 0
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
   */
  approveRequest(type: string, id: number, comments?: string, stepRole?: string): Observable<any> {
    const url = this.getApprovalUrl(type, id, 'approve');
    // Backend requires step_role field
    const payload: any = { comments: comments || '' };
    if (stepRole) {
      payload.step_role = stepRole;
    } else {
      // Default to current approval step if not provided
      payload.step_role = 'Department Focal';
    }
    return this.http.post(url, payload, { withCredentials: true });
  }

  /**
   * Reject a request
   */
  rejectRequest(type: string, id: number, comments?: string, stepRole?: string): Observable<any> {
    const url = this.getApprovalUrl(type, id, 'reject');
    // Backend requires step_role field
    const payload: any = { comments: comments || '' };
    if (stepRole) {
      payload.step_role = stepRole;
    } else {
      // Default to current approval step if not provided
      payload.step_role = 'Department Focal';
    }
    return this.http.post(url, payload, { withCredentials: true });
  }

  /**
   * Get approval history for a request
   */
  getApprovalHistory(type: string, id: number): Observable<any[]> {
    const url = this.getHistoryUrl(type, id);
    return this.http.get<any[]>(url, { withCredentials: true }).pipe(
      catchError(error => {
        console.error(`Error fetching approval history for ${type} ${id}:`, error);
        return of([]);
      })
    );
  }

  // Private helper methods

  private getPendingTrfs(): Observable<ApprovalRequest[]> {
    return this.http.get<any[]>(`${this.baseUrl}/trf/travel-requests/pending-approvals/`, {
      withCredentials: true
    }).pipe(
      map(trfs => trfs.map(trf => this.transformTrfToApproval(trf))),
      catchError(error => {
        console.error('Error fetching pending TRFs:', error);
        return of([]);
      })
    );
  }

  private getPendingAccommodations(): Observable<ApprovalRequest[]> {
    return this.http.get<any[]>(`${this.baseUrl}/accommodation/requests/pending-approvals/`, {
      withCredentials: true
    }).pipe(
      map(accs => accs.map(acc => this.transformAccommodationToApproval(acc))),
      catchError(error => {
        console.error('Error fetching pending accommodations:', error);
        return of([]);
      })
    );
  }

  private getPendingTransports(): Observable<ApprovalRequest[]> {
    return this.http.get<any[]>(`${this.baseUrl}/transport/requests/pending-approvals/`, {
      withCredentials: true
    }).pipe(
      map(transports => transports.map(transport => this.transformTransportToApproval(transport))),
      catchError(error => {
        console.error('Error fetching pending transports:', error);
        return of([]);
      })
    );
  }

  private getPendingVisas(): Observable<ApprovalRequest[]> {
    return this.http.get<any[]>(`${this.baseUrl}/visa/applications/pending-approvals/`, {
      withCredentials: true
    }).pipe(
      map(visas => visas.map(visa => this.transformVisaToApproval(visa))),
      catchError(error => {
        console.error('Error fetching pending visas:', error);
        return of([]);
      })
    );
  }

  private getPendingExpenses(): Observable<ApprovalRequest[]> {
    return this.http.get<any[]>(`${this.baseUrl}/expenses/claims/pending-approvals/`, {
      withCredentials: true
    }).pipe(
      map(expenses => expenses.map(expense => this.transformExpenseToApproval(expense))),
      catchError(error => {
        console.error('Error fetching pending expenses:', error);
        return of([]);
      })
    );
  }

  // Transform backend data to unified ApprovalRequest format

  private transformTrfToApproval(trf: any): ApprovalRequest {
    // Backend uses 'itinerary_segments', but some responses might use 'itinerary'
    const itinerary = trf.itinerary_segments || trf.itinerary || [];

    const destination = this.extractDestination(itinerary);
    const departureDate = this.extractDepartureDate(itinerary);
    const returnDate = this.extractReturnDate(itinerary);

    return {
      id: trf.id,
      type: 'trf',
      title: `${trf.travel_type || 'Travel'} - ${trf.purpose || 'Travel Request'}`,
      requester: {
        id: trf.requestor_id || trf.requestor?.id,
        name: trf.requestor_name || trf.requestor?.name || 'Unknown',
        department: trf.department || trf.requestor?.department || 'Unknown',
        email: trf.tel_email || trf.requestor?.email || ''
      },
      dateSubmitted: trf.created_at || trf.submission_date,
      deadline: trf.deadline || null,
      priority: this.determinePriority(trf.travel_type, trf.created_at),
      status: trf.status || 'Pending',
      currentApprovalStep: trf.current_approval_step,
      details: {
        travelType: trf.travel_type,
        purpose: trf.purpose,
        destination: destination,
        departureDate: departureDate,
        returnDate: returnDate,
        estimatedCost: trf.total_estimated_cost || 0
      }
    };
  }

  private transformAccommodationToApproval(acc: any): ApprovalRequest {
    return {
      id: acc.id,
      type: 'accommodation',
      title: `Accommodation - ${acc.hotel_name || acc.location || 'Request'}`,
      requester: {
        id: acc.requestor_id || acc.requestor?.id,
        name: acc.requestor_name || acc.requestor?.name || 'Unknown',
        department: acc.department || acc.requestor?.department || 'Unknown',
        email: acc.email || acc.requestor?.email || ''
      },
      dateSubmitted: acc.created_at || acc.submission_date,
      deadline: acc.deadline || null,
      priority: this.determinePriority('accommodation', acc.check_in_date),
      status: acc.status || 'Pending',
      currentApprovalStep: acc.current_approval_step,
      details: {
        hotelName: acc.hotel_name,
        location: acc.location,
        checkInDate: acc.check_in_date,
        checkOutDate: acc.check_out_date,
        roomType: acc.room_type
      }
    };
  }

  private transformTransportToApproval(transport: any): ApprovalRequest {
    return {
      id: transport.id,
      type: 'transport',
      title: `Transport - ${transport.transport_type || 'Request'}`,
      requester: {
        id: transport.requestor_id || transport.requestor?.id,
        name: transport.requestor_name || transport.requestor?.name || 'Unknown',
        department: transport.department || transport.requestor?.department || 'Unknown',
        email: transport.email || transport.requestor?.email || ''
      },
      dateSubmitted: transport.created_at || transport.submission_date,
      deadline: transport.deadline || null,
      priority: this.determinePriority('transport', transport.pickup_date),
      status: transport.status || 'Pending',
      currentApprovalStep: transport.current_approval_step,
      details: {
        transportType: transport.transport_type,
        pickupLocation: transport.pickup_location,
        dropoffLocation: transport.dropoff_location,
        pickupDate: transport.pickup_date,
        pickupTime: transport.pickup_time,
        estimatedCost: transport.estimated_cost || 0
      }
    };
  }

  private transformVisaToApproval(visa: any): ApprovalRequest {
    return {
      id: visa.id,
      type: 'visa',
      title: `Visa - ${visa.destination_country || 'Application'}`,
      requester: {
        id: visa.applicant_id || visa.applicant?.id,
        name: visa.applicant_name || visa.applicant?.name || 'Unknown',
        department: visa.department || visa.applicant?.department || 'Unknown',
        email: visa.email || visa.applicant?.email || ''
      },
      dateSubmitted: visa.created_at || visa.submission_date,
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
        estimatedCost: visa.estimated_cost || 0
      }
    };
  }

  private transformExpenseToApproval(expense: any): ApprovalRequest {
    return {
      id: expense.id,
      type: 'expense',
      title: `Expense Claim - ${expense.expense_type || 'Reimbursement'}`,
      requester: {
        id: expense.claimant_id || expense.claimant?.id,
        name: expense.claimant_name || expense.claimant?.name || 'Unknown',
        department: expense.department || expense.claimant?.department || 'Unknown',
        email: expense.email || expense.claimant?.email || ''
      },
      dateSubmitted: expense.created_at || expense.submission_date,
      deadline: expense.deadline || null,
      priority: this.determinePriority('expense', expense.created_at),
      status: expense.status || 'Pending',
      currentApprovalStep: expense.current_approval_step,
      details: {
        expenseType: expense.expense_type,
        totalAmount: expense.total_amount || 0,
        currency: expense.currency || 'MYR',
        claimDate: expense.claim_date,
        hasReceipts: expense.has_receipts || false
      }
    };
  }

  // Helper methods

  private determinePriority(type: string, dateField?: string): 'low' | 'medium' | 'high' {
    if (!dateField) return 'medium';

    const targetDate = new Date(dateField);
    const today = new Date();
    const daysUntil = Math.ceil((targetDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (daysUntil < 7) return 'high';
    if (daysUntil < 14) return 'medium';
    return 'low';
  }

  private extractDestination(itinerary: any[]): string {
    if (!itinerary || itinerary.length === 0) return 'N/A';
    // Backend uses 'to_location' not 'destination'
    const lastSegment = itinerary[itinerary.length - 1];
    return lastSegment?.to_location || lastSegment?.destination || 'N/A';
  }

  private extractDepartureDate(itinerary: any[]): string {
    if (!itinerary || itinerary.length === 0) return '';
    // Backend uses 'segment_date' not 'departure_date'
    const firstSegment = itinerary[0];
    return firstSegment?.segment_date || firstSegment?.departure_date || firstSegment?.date || '';
  }

  private extractReturnDate(itinerary: any[]): string {
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
      expense: `${this.baseUrl}/expenses/claims/${id}/${action}/`
    };
    return baseUrls[type] || '';
  }

  private getHistoryUrl(type: string, id: number): string {
    const baseUrls: { [key: string]: string } = {
      trf: `${this.baseUrl}/trf/travel-requests/${id}/approval-history/`,
      accommodation: `${this.baseUrl}/accommodation/requests/${id}/approval-history/`,
      transport: `${this.baseUrl}/transport/requests/${id}/approval-history/`,
      visa: `${this.baseUrl}/visa/applications/${id}/approval-history/`,
      expense: `${this.baseUrl}/expenses/claims/${id}/approval-history/`
    };
    return baseUrls[type] || '';
  }
}
