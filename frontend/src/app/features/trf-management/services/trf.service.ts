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
  private apiUrl = `${environment.apiUrl}/api/trf`;
  private overseasApiUrl = `${environment.apiUrl}/api/overseas-trf`;

  constructor(private http: HttpClient) { }

  // Get all TRFs (legacy method)
  getAllTrfs(params?: any): Observable<any> {
    let queryParams = '';
    if (params) {
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
  getTrfById(id: number, isOverseas: boolean = false): Observable<TravelRequestForm> {
    return this.http.get<TravelRequestForm>(`${environment.apiUrl}/trf/travel-requests/${id}/`)
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
    const url = isOverseas ? this.overseasApiUrl : this.apiUrl;
    return this.http.put<TravelRequestForm>(`${url}/${id}/`, trf)
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
  submitTrf(id: number, isOverseas: boolean = false): Observable<TravelRequestForm> {
    const url = isOverseas ? this.overseasApiUrl : this.apiUrl;
    return this.http.post<TravelRequestForm>(`${url}/${id}/submit/`, {})
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

  // Export TRF to PDF
  exportTrfToPdf(id: number, isOverseas: boolean = false): Observable<Blob> {
    const headers = new HttpHeaders({
      'Accept': 'application/pdf'
    });

    const url = isOverseas ? this.overseasApiUrl : this.apiUrl;
    return this.http.get(`${url}/${id}/export-pdf/`, {
      headers: headers,
      responseType: 'blob'
    }).pipe(
      catchError(this.handleError)
    );
  }

  // =============== NEW METHODS FOR WIZARD INTEGRATION ===============

  // Create main Travel Request
  createTravelRequest(data: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/travel-requests/`, data)
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

  // Create Accommodation Detail
  createAccommodation(data: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/accommodation-details/`, data)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Create Company Transport Detail
  createTransport(data: any): Observable<any> {
    return this.http.post<any>(`${environment.apiUrl}/trf/transport-details/`, data)
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

  // Error handling
  private handleError(error: any) {
    console.error('An error occurred:', error);
    return throwError(() => error);
  }
}
