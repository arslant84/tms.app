import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';

// Accommodation Interfaces
export interface AccommodationStaffHouse {
  id: number;
  name: string;
  location: string;
  address?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface AccommodationRoom {
  id: number;
  staff_house: number;
  staff_house_name?: string;
  name: string;
  room_type?: string;
  capacity: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AccommodationRequest {
  id: number;
  request_number?: string;
  requestor_name: string;
  staff_id?: string;
  department?: string;
  position?: string;
  cost_center?: string;
  tel_email?: string;
  email?: string;
  status: string;
  estimated_cost?: number;
  additional_comments?: string;
  submitted_at?: string;
  created_at: string;
  updated_at: string;
  additional_data?: any;
}

export interface AccommodationRequestDetail extends AccommodationRequest {
  bookings?: AccommodationBooking[];
}

export interface AccommodationBooking {
  id: number;
  staff_house: number;
  staff_house_name?: string;
  room: number;
  room_name?: string;
  staff?: number;
  staff_name?: string;
  date: string;
  trf?: number;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class AccommodationService {
  private apiUrl = `${environment.apiUrl}/accommodation`;

  constructor(private http: HttpClient) {}

  // Accommodation Requests
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

    return this.http.get<any>(`${this.apiUrl}/requests/`, { params });
  }

  getRequestById(id: number): Observable<AccommodationRequestDetail> {
    return this.http.get<AccommodationRequestDetail>(`${this.apiUrl}/requests/${id}/`);
  }

  createRequest(data: any): Observable<AccommodationRequestDetail> {
    return this.http.post<AccommodationRequestDetail>(`${this.apiUrl}/requests/`, data);
  }

  updateRequest(id: number, data: any): Observable<AccommodationRequestDetail> {
    return this.http.put<AccommodationRequestDetail>(`${this.apiUrl}/requests/${id}/`, data);
  }

  deleteRequest(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/requests/${id}/`);
  }

  cancelRequest(id: number, reason?: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/requests/${id}/cancel/`, { reason });
  }

  approveRequest(id: number, comments?: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/requests/${id}/approve/`, { comments });
  }

  rejectRequest(id: number, reason: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/requests/${id}/reject/`, { reason });
  }

  // Staff Houses
  getAllStaffHouses(location?: string): Observable<AccommodationStaffHouse[]> {
    let params = new HttpParams();
    if (location) params = params.set('location', location);
    // Add page_size to get all results without pagination
    params = params.set('page_size', '1000');
    return this.http.get<any>(`${this.apiUrl}/staff-houses/`, { params }).pipe(
      map((response: any) => {
        // Handle both paginated and non-paginated responses
        if (response && response.results) {
          return response.results;
        }
        return Array.isArray(response) ? response : [];
      })
    );
  }

  getStaffHouseById(id: number): Observable<AccommodationStaffHouse> {
    return this.http.get<AccommodationStaffHouse>(`${this.apiUrl}/staff-houses/${id}/`);
  }

  createStaffHouse(data: any): Observable<AccommodationStaffHouse> {
    return this.http.post<AccommodationStaffHouse>(`${this.apiUrl}/staff-houses/`, data);
  }

  updateStaffHouse(id: number, data: any): Observable<AccommodationStaffHouse> {
    return this.http.put<AccommodationStaffHouse>(`${this.apiUrl}/staff-houses/${id}/`, data);
  }

  deleteStaffHouse(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/staff-houses/${id}/`);
  }

  // Rooms
  getAllRooms(staffHouseId?: number): Observable<AccommodationRoom[]> {
    let params = new HttpParams();
    if (staffHouseId) params = params.set('staff_house', staffHouseId.toString());
    // Add page_size to get all results without pagination
    params = params.set('page_size', '1000');
    return this.http.get<any>(`${this.apiUrl}/rooms/`, { params }).pipe(
      map((response: any) => {
        // Handle both paginated and non-paginated responses
        if (response && response.results) {
          return response.results;
        }
        return Array.isArray(response) ? response : [];
      })
    );
  }

  getRoomById(id: number): Observable<AccommodationRoom> {
    return this.http.get<AccommodationRoom>(`${this.apiUrl}/rooms/${id}/`);
  }

  createRoom(data: any): Observable<AccommodationRoom> {
    return this.http.post<AccommodationRoom>(`${this.apiUrl}/rooms/`, data);
  }

  updateRoom(id: number, data: any): Observable<AccommodationRoom> {
    return this.http.put<AccommodationRoom>(`${this.apiUrl}/rooms/${id}/`, data);
  }

  deleteRoom(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/rooms/${id}/`);
  }

  // Room availability
  checkRoomAvailability(staffHouseId: number, checkIn: string, checkOut: string): Observable<any> {
    const params = new HttpParams()
      .set('staff_house', staffHouseId.toString())
      .set('check_in', checkIn)
      .set('check_out', checkOut);
    return this.http.get<any>(`${this.apiUrl}/rooms/availability/`, { params });
  }

  // Bookings
  getAllBookings(filters?: {
    staff_house?: number;
    room?: number;
    date?: string;
    status?: string;
  }): Observable<AccommodationBooking[]> {
    let params = new HttpParams();

    if (filters) {
      if (filters.staff_house) params = params.set('staff_house', filters.staff_house.toString());
      if (filters.room) params = params.set('room', filters.room.toString());
      if (filters.date) params = params.set('date', filters.date);
      if (filters.status) params = params.set('status', filters.status);
    }

    return this.http.get<AccommodationBooking[]>(`${this.apiUrl}/bookings/`, { params });
  }

  createBooking(data: any): Observable<AccommodationBooking> {
    return this.http.post<AccommodationBooking>(`${this.apiUrl}/bookings/`, data);
  }

  updateBooking(id: number, data: any): Observable<AccommodationBooking> {
    return this.http.put<AccommodationBooking>(`${this.apiUrl}/bookings/${id}/`, data);
  }

  deleteBooking(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/bookings/${id}/`);
  }

  checkIn(bookingId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/bookings/${bookingId}/checkin/`, {});
  }

  checkOut(bookingId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/bookings/${bookingId}/checkout/`, {});
  }
}
