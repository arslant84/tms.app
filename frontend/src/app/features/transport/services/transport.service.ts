import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

// Transport Request Interfaces
export interface TransportRequest {
  id: number;
  requestor?: number;
  trf?: number;
  title: string;
  purpose: string;
  transport_type: string;
  status: string;
  number_of_passengers: number;
  passenger_names?: string;
  vehicle_type?: string;
  special_requirements?: string;
  estimated_cost: number;
  currency: string;
  additional_comments?: string;
  additional_data?: any;
  submitted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TransportRequestDetail extends TransportRequest {
  segments?: TransportSegment[];
  approval_steps?: TransportApprovalStep[];
  vehicle_assignments?: VehicleAssignment[];
}

export interface TransportSegment {
  id?: number;
  transport_request?: number;
  from_location: string;
  to_location: string;
  departure_date: string;
  departure_time: string;
  arrival_date?: string;
  arrival_time?: string;
  distance_km?: number;
  estimated_duration_hours?: number;
  route_description?: string;
  vehicle_number?: string;
  driver_name?: string;
  driver_contact?: string;
  segment_cost: number;
  remarks?: string;
}

export interface TransportApprovalStep {
  id?: number;
  transport_request?: number;
  step_role: string;
  step_name?: string;
  status: string;
  step_date?: string;
  comments?: string;
}

export interface VehicleAssignment {
  id?: number;
  transport_request?: number;
  vehicle_number: string;
  vehicle_type: string;
  vehicle_capacity: number;
  driver_name: string;
  driver_contact: string;
  driver_license?: string;
  assigned_by?: number;
  status: string;
  odometer_start?: number;
  odometer_end?: number;
  fuel_used_liters?: number;
  assignment_date: string;
  completion_date?: string;
}

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
  getRequestById(id: number): Observable<TransportRequestDetail> {
    return this.http.get<TransportRequestDetail>(`${this.apiUrl}/${id}/`);
  }

  // Create new transport request
  createRequest(data: any): Observable<TransportRequestDetail> {
    return this.http.post<TransportRequestDetail>(this.apiUrl + '/', data);
  }

  // Update existing transport request
  updateRequest(id: number, data: any): Observable<TransportRequestDetail> {
    return this.http.put<TransportRequestDetail>(`${this.apiUrl}/${id}/`, data);
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
