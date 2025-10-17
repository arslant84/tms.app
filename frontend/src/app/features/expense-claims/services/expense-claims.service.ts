import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';

export interface ExpenseClaim {
  id: number;
  document_number?: string;
  staff_name: string;
  staff_no: string;
  department_code?: string;
  purpose_of_claim: string;
  total_advance_claim_amount: number;
  status: string;
  submitted_at: string;
  created_at: string;
  trf_id?: number;
}

export interface ExpenseClaimItem {
  id?: number;
  claim_id?: number;
  item_date: string;
  claim_or_travel_details: string;
  official_mileage_km?: number;
  transport?: number;
  hotel_accommodation_allowance?: number;
  out_station_allowance_meal?: number;
  miscellaneous_allowance_10_percent?: number;
  other_expenses?: number;
}

export interface ExpenseClaimFXRate {
  id?: number;
  claim_id?: number;
  fx_date: string;
  type_of_currency: string;
  selling_rate_tt_od: number;
}

export interface ClaimsApprovalStep {
  id?: number;
  claim_id?: number;
  step_role: string;
  step_name: string;
  status: string;
  step_date?: string;
  comments?: string;
}

export interface ExpenseClaimDetail extends ExpenseClaim {
  document_type?: string;
  claim_for_month_of?: string;
  gred?: string;
  staff_type?: string;
  executive_status?: string;
  dept_cost_center_code?: string;
  location?: string;
  tel_ext?: string;
  start_time_from_home?: string;
  time_of_arrival_at_home?: string;
  bank_name?: string;
  account_number?: string;
  is_medical_claim?: boolean;
  applicable_medical_type?: string;
  is_for_family?: boolean;
  family_member_spouse?: boolean;
  family_member_children?: boolean;
  family_member_other?: boolean;
  less_advance_taken?: number;
  less_corporate_credit_card_payment?: number;
  balance_claim_repayment?: number;
  cheque_receipt_no?: string;
  i_declare?: boolean;
  declaration_date?: string;
  expense_items?: ExpenseClaimItem[];
  fx_rates?: ExpenseClaimFXRate[];
  approval_steps?: ClaimsApprovalStep[];
}

@Injectable({
  providedIn: 'root'
})
export class ExpenseClaimsService {
  private apiUrl = `${environment.apiUrl}/expenses`;

  constructor(private http: HttpClient) {}

  /**
   * Get all expense claims with optional filters
   */
  getAllClaims(params?: any): Observable<any> {
    let httpParams = new HttpParams();

    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
          httpParams = httpParams.set(key, params[key].toString());
        }
      });
    }

    const url = `${this.apiUrl}/claims/`;
    console.log('📡 Expense Claims Service: Calling API URL:', url, 'with params:', httpParams.toString());

    return this.http.get<any>(url, { params: httpParams }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get expense claim by ID
   */
  getClaimById(id: number): Observable<ExpenseClaimDetail> {
    const url = `${this.apiUrl}/claims/${id}/`;
    console.log('📡 Expense Claims Service: Fetching claim:', url);

    return this.http.get<ExpenseClaimDetail>(url).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Create new expense claim
   */
  createClaim(claim: Partial<ExpenseClaimDetail>): Observable<ExpenseClaimDetail> {
    const url = `${this.apiUrl}/claims/`;
    console.log('📡 Expense Claims Service: Creating claim:', url);

    return this.http.post<ExpenseClaimDetail>(url, claim).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Update expense claim
   */
  updateClaim(id: number, claim: Partial<ExpenseClaimDetail>): Observable<ExpenseClaimDetail> {
    const url = `${this.apiUrl}/claims/${id}/`;
    console.log('📡 Expense Claims Service: Updating claim:', url);

    return this.http.put<ExpenseClaimDetail>(url, claim).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Delete expense claim
   */
  deleteClaim(id: number): Observable<any> {
    const url = `${this.apiUrl}/claims/${id}/`;
    console.log('📡 Expense Claims Service: Deleting claim:', url);

    return this.http.delete(url).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Cancel expense claim
   */
  cancelClaim(id: number, comments?: string): Observable<any> {
    const url = `${this.apiUrl}/claims/${id}/cancel/`;
    console.log('📡 Expense Claims Service: Cancelling claim:', url);

    return this.http.post(url, { comments }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Submit expense claim for approval
   */
  submitClaim(id: number): Observable<any> {
    const url = `${this.apiUrl}/claims/${id}/submit/`;
    console.log('📡 Expense Claims Service: Submitting claim:', url);

    return this.http.post(url, {}).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Approve expense claim
   */
  approveClaim(id: number, data: { step_role: string; comments?: string }): Observable<any> {
    const url = `${this.apiUrl}/claims/${id}/approve/`;
    console.log('📡 Expense Claims Service: Approving claim:', url);

    return this.http.post(url, data).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Reject expense claim
   */
  rejectClaim(id: number, data: { step_role: string; comments: string }): Observable<any> {
    const url = `${this.apiUrl}/claims/${id}/reject/`;
    console.log('📡 Expense Claims Service: Rejecting claim:', url);

    return this.http.post(url, data).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Mark expense claim as paid
   */
  markAsPaid(id: number, data: any): Observable<any> {
    const url = `${this.apiUrl}/claims/${id}/mark-paid/`;
    console.log('📡 Expense Claims Service: Marking claim as paid:', url);

    return this.http.post(url, data).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get expense items for a claim
   */
  getExpenseItems(claimId: number): Observable<ExpenseClaimItem[]> {
    const url = `${this.apiUrl}/expense-items/`;
    const params = new HttpParams().set('claim', claimId.toString());

    return this.http.get<ExpenseClaimItem[]>(url, { params }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get approval steps for a claim
   */
  getApprovalSteps(claimId: number): Observable<ClaimsApprovalStep[]> {
    const url = `${this.apiUrl}/approval-steps/`;
    const params = new HttpParams().set('claim', claimId.toString());

    return this.http.get<ClaimsApprovalStep[]>(url, { params }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Error handling
   */
  private handleError(error: any): Observable<never> {
    console.error('Expense Claims Service Error:', error);
    throw error;
  }
}
