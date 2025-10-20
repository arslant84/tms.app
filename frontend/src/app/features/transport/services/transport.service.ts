import { Injectable } from '@angular/core';
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';
import {
  TransportRequestForm,
  toFrontendFormat
} from '../models/transport.model';

@Injectable({
  providedIn: 'root'
})
export class TransportService {
  private apiUrl = `${environment.apiUrl}/transport/requests`;

  constructor(private http: HttpClient) {}

  // Get all transport requests with optional filters
  getAllRequests(filters?: {
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Observable<any> {
    let params = new HttpParams();

    if (filters) {
      if (filters.status) params = params.set('status', filters.status);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.page) params = params.set('page', filters.page.toString());
      if (filters.page_size) params = params.set('page_size', filters.page_size.toString());
    }

    return this.http.get<any>(this.apiUrl + '/', { params });
  }

  // Get single transport request by ID
  getRequestById(id: number): Observable<TransportRequestForm> {
    return this.http.get<any>(`${this.apiUrl}/${id}/`).pipe(
      map(response => toFrontendFormat(response))
    );
  }

  // Create new transport request
  createRequest(data: any): Observable<TransportRequestForm> {
    return this.http.post<any>(this.apiUrl + '/', data).pipe(
      map(response => toFrontendFormat(response))
    );
  }

  // Update existing transport request
  updateRequest(id: number, data: any): Observable<TransportRequestForm> {
    return this.http.put<any>(`${this.apiUrl}/${id}/`, data).pipe(
      map(response => toFrontendFormat(response))
    );
  }

  // Delete transport request
  deleteRequest(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`);
  }

  // Submit transport request (change status from Draft to Pending)
  submitRequest(id: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/submit/`, {});
  }

  // Cancel transport request
  cancelRequest(id: number, reason?: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/cancel/`, { reason });
  }

  // Approve transport request
  approveRequest(id: number, comments?: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/approve/`, { comments });
  }

  // Reject transport request
  rejectRequest(id: number, reason: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/reject/`, { reason });
  }

  // Complete transport request
  completeRequest(id: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/complete/`, {});
  }

  // Assign vehicle to transport request
  assignVehicle(id: number, data: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/assign_vehicle/`, data);
  }
}
