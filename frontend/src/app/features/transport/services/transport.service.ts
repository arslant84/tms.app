import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';
import {
  TransportBackendData,
  TransportRequestForm,
  toFrontendFormat,
} from '../models/transport.model';

// Type aliases for backward compatibility
export type TransportRequest = TransportRequestForm;

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface VehicleAssignment {
  id?: number;
  vehicle_id?: number;
  vehicle_number?: string;
  vehicle_plate?: string;
  vehicle_type?: string;
  vehicle_capacity?: number;
  driver_name?: string;
  driver_contact?: string;
  driver_license?: string;
  assigned_at?: string;
  assignment_date?: string;
  odometer_start?: number;
}

@Injectable({
  providedIn: 'root',
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
    adminView?: boolean; // Set to true when viewing from Transport Admin module
  }): Observable<TransportRequestForm[] | PaginatedResponse<TransportRequestForm>> {
    let params = new HttpParams();

    if (filters) {
      if (filters.status) params = params.set('status', filters.status);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.page) params = params.set('page', filters.page.toString());
      if (filters.page_size) params = params.set('page_size', filters.page_size.toString());
      // Add admin_view parameter for admin modules (side navbar)
      if (filters.adminView) params = params.set('admin_view', 'true');
    }

    return this.http
      .get<TransportBackendData[] | PaginatedResponse<TransportBackendData>>(this.apiUrl + '/', {
        params,
      })
      .pipe(
        map((response): TransportRequestForm[] | PaginatedResponse<TransportRequestForm> => {
          // Handle array response
          if (Array.isArray(response)) {
            return response.map(item => toFrontendFormat(item));
          }
          // Handle paginated response
          return {
            ...response,
            results: response.results.map(item => toFrontendFormat(item)),
          };
        })
      );
  }

  // Get single transport request by ID
  getRequestById(id: number | string): Observable<TransportRequestForm> {
    return this.http
      .get<TransportBackendData>(`${this.apiUrl}/${id}/`)
      .pipe(map(response => toFrontendFormat(response)));
  }

  // Create new transport request. Callers pass an already-backend-shaped
  // (snake_case) payload built via toBackendFormat, not TransportRequestForm.
  createRequest(data: Record<string, unknown>): Observable<TransportRequestForm> {
    return this.http
      .post<TransportBackendData>(this.apiUrl + '/', data)
      .pipe(map(response => toFrontendFormat(response)));
  }

  // Update existing transport request (partial update)
  updateRequest(
    id: number | string,
    data: Partial<TransportRequestForm> | Record<string, unknown>
  ): Observable<TransportRequestForm> {
    return this.http
      .patch<TransportBackendData>(`${this.apiUrl}/${id}/`, data)
      .pipe(map(response => toFrontendFormat(response)));
  }

  // Delete transport request
  deleteRequest(id: number | string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`);
  }

  // Submit transport request (change status from Draft to Pending)
  submitRequest(id: number | string): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/${id}/submit/`, {});
  }

  // Cancel transport request
  cancelRequest(id: number | string, reason?: string): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/${id}/cancel/`, { reason });
  }

  // Approve transport request
  approveRequest(id: number | string, comments?: string): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/${id}/approve/`, { comments });
  }

  // Reject transport request
  rejectRequest(id: number | string, reason: string): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/${id}/reject/`, { reason });
  }

  // Complete transport request
  completeRequest(id: number | string): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/${id}/complete/`, {});
  }

  // Undo a mistaken completion - cancels the vehicle assignment and reverts
  // the request to Processing with Transport Admin so it can be redone.
  undoCompleteRequest(id: number | string): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/${id}/cancel_assignment/`, {});
  }

  // Assign vehicle to transport request
  assignVehicle(id: number | string, data: VehicleAssignment): Observable<unknown> {
    // Create vehicle assignment through the vehicle-assignments endpoint
    const vehicleAssignmentData = {
      transport_request: id,
      ...data,
    };
    return this.http.post(
      `${environment.apiUrl}/transport/vehicle-assignments/`,
      vehicleAssignmentData
    );
  }

  // Export transport request to PDF
  exportToPdf(id: number | string): Observable<Blob> {
    return this.http
      .get(`${this.apiUrl}/${id}/export-pdf/`, {
        responseType: 'blob',
      })
      .pipe(
        catchError(error => {
          console.error('PDF export error:', error);
          return throwError(() => error);
        })
      );
  }
}
