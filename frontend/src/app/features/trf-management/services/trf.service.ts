import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { DomesticTravelRequestForm, OverseasTravelRequestForm, TravelRequestForm } from '../models/trf.model';
import { environment } from '../../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class TrfService {
  private apiUrl = `${environment.apiUrl}/trf`;
  private overseasApiUrl = `${environment.apiUrl}/overseas-trf`;

  constructor(private http: HttpClient) { }

  // Get all TRFs (legacy method)
  getAllTrfs(params?: any): Observable<any> {
    let queryParams = '';
    if (params) {
      // Convert adminView boolean to admin_view string parameter
      if (params.adminView === true) {
        params.admin_view = 'true';
        delete params.adminView;
      }

      const queryString = Object.keys(params)
        .filter(key => params[key] !== null && params[key] !== undefined && params[key] !== '')
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
        .join('&');
      queryParams = queryString ? `?${queryString}` : '';
    }

    return this.http.get<any>(`${environment.apiUrl}/trf/travel-requests/${queryParams}`)
      .pipe(
        catchError(this.handleError)
      );
  }
  
  // Get all domestic TRFs
  getAllDomesticTrfs(): Observable<DomesticTravelRequestForm[]> {
    return this.http.get<DomesticTravelRequestForm[]>(`${this.apiUrl}/`)
      .pipe(
        catchError(this.handleError)
      );
  }
  
  // Get all overseas TRFs
  getAllOverseasTrfs(): Observable<OverseasTravelRequestForm[]> {
    return this.http.get<OverseasTravelRequestForm[]>(`${this.overseasApiUrl}/`)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Get TRF by ID and type
  getTrfById(id: number, isOverseas: boolean = false, adminView: boolean = false): Observable<TravelRequestForm> {
    const params = adminView ? '?admin_view=true' : '';
    return this.http.get<TravelRequestForm>(`${environment.apiUrl}/trf/travel-requests/${id}/${params}`)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Create new domestic TRF
  createDomesticTrf(trf: DomesticTravelRequestForm): Observable<DomesticTravelRequestForm> {
    return this.http.post<DomesticTravelRequestForm>(`${this.apiUrl}/`, trf)
      .pipe(
        catchError(this.handleError)
      );
  }
  
  // Create new overseas TRF
  createOverseasTrf(trf: OverseasTravelRequestForm): Observable<OverseasTravelRequestForm> {
    return this.http.post<OverseasTravelRequestForm>(`${this.overseasApiUrl}/`, trf)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Update TRF
  updateTrf(id: number, trf: TravelRequestForm, isOverseas: boolean = false): Observable<TravelRequestForm> {
    return this.http.put<TravelRequestForm>(`${environment.apiUrl}/trf/travel-requests/${id}/`, trf)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Delete TRF
  deleteTrf(id: number, isOverseas: boolean = false): Observable<any> {
    return this.http.delete(`${environment.apiUrl}/trf/travel-requests/${id}/`)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Submit TRF for approval
  submitTrf(
    id: number,
    isOverseas: boolean = false,
    selectedApprovers?: { [stepOrder: number]: number },
    skippedSteps?: { [stepOrder: number]: string | null }
  ): Observable<TravelRequestForm> {
    const payload: any = {};
    if (selectedApprovers && Object.keys(selectedApprovers).length > 0) {
      payload.selected_approvers = selectedApprovers;
    }
    if (skippedSteps && Object.keys(skippedSteps).length > 0) {
      payload.skipped_steps = skippedSteps;
    }
    return this.http.post<TravelRequestForm>(`${environment.apiUrl}/trf/travel-requests/${id}/submit/`, payload)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Cancel TRF
  cancelTrf(id: number, isOverseas: boolean = false): Observable<TravelRequestForm> {
    return this.http.post<TravelRequestForm>(`${environment.apiUrl}/trf/travel-requests/${id}/cancel/`, {})
      .pipe(
        catchError(this.handleError)
      );
  }

  // Check TSR accommodation availability
  checkAccommodationAvailability(id: number): Observable<any> {
    return this.http.get<any>(`${environment.apiUrl}/trf/travel-requests/${id}/check-accommodation-availability/`)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Export TRF to PDF
  exportTrfToPdf(id: number, isOverseas: boolean = false): Observable<Blob> {
    // Note: Don't set Accept header to avoid DRF content negotiation issues
    // responseType: 'blob' handles binary content properly
    return this.http.get(`${environment.apiUrl}/trf/travel-requests/${id}/export-pdf/`, {
      responseType: 'blob'
    }).pipe(
      catchError(this.handleError)
    );
  }

  // =============== NEW METHODS FOR WIZARD INTEGRATION ===============

  // Create main Travel Request (supports selected_approvers for direct submission)
  createTravelRequest(data: any, selectedApprovers?: { [stepOrder: number]: number }): Observable<any> {
    const payload = { ...data };
    if (selectedApprovers && Object.keys(selectedApprovers).length > 0) {
      payload.selected_approvers = selectedApprovers;
    }
    return this.http.post<any>(`${environment.apiUrl}/trf/travel-requests/`, payload)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Create Itinerary Segment
  createItinerarySegment(data: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/itinerary-segments/`, data)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Create Daily Meal Selection
  createDailyMeal(data: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/daily-meals/`, data)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Create Meal Provision
  createMealProvision(data: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/meal-provisions/`, data)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Create Passport Detail
  createPassportDetail(data: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/passport-details/`, data)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Create Bank Detail
  createBankDetail(data: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/bank-details/`, data)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Create Advance Amount Requested Item
  createAdvanceAmountItem(data: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/advance-amounts/`, data)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Delete nested resources by type
  deleteNestedResources(trfId: number, type: string): Observable<any> {
    const endpoints: { [key: string]: string } = {
      'itinerary': `${environment.apiUrl}/trf/travel-requests/${trfId}/delete-itinerary/`,
      'meals': `${environment.apiUrl}/trf/travel-requests/${trfId}/delete-meals/`,
      'passport': `${environment.apiUrl}/trf/travel-requests/${trfId}/delete-passport/`,
      'bank': `${environment.apiUrl}/trf/travel-requests/${trfId}/delete-bank/`,
      'advance-amounts': `${environment.apiUrl}/trf/travel-requests/${trfId}/delete-advance-amounts/`
    };

    const url = endpoints[type];
    if (!url) {
      return throwError(() => new Error(`Unknown resource type: ${type}`));
    }

    return this.http.delete<any>(url).pipe(
      catchError(this.handleError)
    );
  }

  // Book flight for TRF (Admin action)
  bookFlight(trfId: string, payload: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/travel-requests/${trfId}/admin/book-flight/`, payload)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Reject TRF (Admin action)
  rejectTrf(trfId: string, reason: string): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/travel-requests/${trfId}/action/`, {
      action: 'reject',
      approverRole: 'Flight Admin',
      approverName: 'Flight Administrator',
      comments: reason
    }).pipe(
      catchError(this.handleError)
    );
  }

  // Cancel flight booking
  cancelFlightBooking(flightId: string): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/bookings/flights/${flightId}/cancel/`, {})
      .pipe(
        catchError(this.handleError)
      );
  }

  // =============== PASSPORT FILE UPLOAD METHODS ===============

  /**
   * Upload passport document for a TRF
   * Creates passport detail record if it doesn't exist
   */
  uploadPassportDocument(trfId: number, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('trf', trfId.toString());
    formData.append('passport_file', file);

    return this.http.post<any>(
      `${environment.apiUrl}/trf/passport-details/upload-for-trf/`,
      formData
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Upload passport file to an existing passport detail record
   */
  uploadPassportFile(passportDetailId: number, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('passport_file', file);

    return this.http.post<any>(
      `${environment.apiUrl}/trf/passport-details/${passportDetailId}/upload-passport/`,
      formData
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Delete passport file from a passport detail record
   */
  deletePassportFile(passportDetailId: number): Observable<any> {
    return this.http.delete<any>(
      `${environment.apiUrl}/trf/passport-details/${passportDetailId}/delete-passport-file/`
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get passport details for a TRF
   */
  getPassportDetails(trfId: number): Observable<any> {
    return this.http.get<any>(
      `${environment.apiUrl}/trf/passport-details/?trf=${trfId}`
    ).pipe(
      catchError(this.handleError)
    );
  }

  // Error handling
  private handleError(error: any) {
    console.error('An error occurred:', error);
    return throwError(() => error);
  }
}
