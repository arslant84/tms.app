import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { DomesticTravelRequestForm } from '../models/trf.model';
import { environment } from '../../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class TrfService {
  private apiUrl = `${environment.apiUrl}/api/trf`;

  constructor(private http: HttpClient) { }

  // Get all TRFs
  getAllTrfs(): Observable<DomesticTravelRequestForm[]> {
    return this.http.get<DomesticTravelRequestForm[]>(`${this.apiUrl}/`)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Get TRF by ID
  getTrfById(id: number): Observable<DomesticTravelRequestForm> {
    return this.http.get<DomesticTravelRequestForm>(`${this.apiUrl}/${id}`)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Create new TRF
  createTrf(trf: DomesticTravelRequestForm): Observable<DomesticTravelRequestForm> {
    return this.http.post<DomesticTravelRequestForm>(`${this.apiUrl}/`, trf)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Update TRF
  updateTrf(id: number, trf: DomesticTravelRequestForm): Observable<DomesticTravelRequestForm> {
    return this.http.put<DomesticTravelRequestForm>(`${this.apiUrl}/${id}/`, trf)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Delete TRF
  deleteTrf(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}/`)
      .pipe(
        catchError(this.handleError)
      );
  }

  // Submit TRF for approval
  submitTrf(id: number): Observable<DomesticTravelRequestForm> {
    return this.http.post<DomesticTravelRequestForm>(`${this.apiUrl}/${id}/submit/`, {})
      .pipe(
        catchError(this.handleError)
      );
  }

  // Export TRF to PDF
  exportTrfToPdf(id: number): Observable<Blob> {
    const headers = new HttpHeaders({
      'Accept': 'application/pdf'
    });
    
    return this.http.get(`${this.apiUrl}/${id}/export-pdf/`, {
      headers: headers,
      responseType: 'blob'
    }).pipe(
      catchError(this.handleError)
    );
  }

  // Error handling
  private handleError(error: any) {
    console.error('An error occurred:', error);
    return throwError(() => error);
  }
}
