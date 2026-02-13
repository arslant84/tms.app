import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

// Flight Booking Interfaces
export interface FlightBooking {
  id: number;
  trf: number;
  user: number;
  flight_type: 'ONE_WAY' | 'ROUND_TRIP' | 'MULTI_CITY';
  airline: string;
  airline_code?: string;
  flight_number: string;
  departure_airport: string;
  departure_airport_code?: string;
  arrival_airport: string;
  arrival_airport_code?: string;
  departure_time: string;
  arrival_time: string;
  departure_terminal?: string;
  arrival_terminal?: string;
  booking_class: 'ECONOMY' | 'PREMIUM_ECONOMY' | 'BUSINESS' | 'FIRST';
  seat_number?: string;
  status: 'PENDING' | 'REQUESTED' | 'CONFIRMED' | 'TICKETED' | 'CANCELLED' | 'REFUNDED' | 'NO_SHOW';
  booking_reference: string;
  ticket_number?: string;
  cost: number;
  currency: string;
  tax_amount: number;
  baggage_allowance?: string;
  carry_on_allowance?: string;
  meal_preference?: string;
  special_requests?: string;
  booked_by?: number;
  booking_date?: string;
  confirmation_date?: string;
  ticketing_date?: string;
  cancellation_date?: string;
  cancellation_reason?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

// Hotel Booking Interfaces
export interface HotelBooking {
  id: number;
  trf: number;
  user: number;
  hotel_name: string;
  hotel_chain?: string;
  location: string;
  address?: string;
  contact_number?: string;
  email?: string;
  check_in_date: string;
  check_out_date: string;
  check_in_time?: string;
  check_out_time?: string;
  room_type: string;
  number_of_rooms: number;
  number_of_guests: number;
  bed_preference?: string;
  smoking_preference: boolean;
  status: 'PENDING' | 'REQUESTED' | 'CONFIRMED' | 'TICKETED' | 'CANCELLED' | 'REFUNDED' | 'NO_SHOW';
  booking_reference: string;
  cost_per_night?: number;
  total_cost: number;
  currency: string;
  tax_amount: number;
  service_charges: number;
  breakfast_included: boolean;
  wifi_included: boolean;
  parking_included: boolean;
  airport_transfer: boolean;
  special_requests?: string;
  dietary_requirements?: string;
  booked_by?: number;
  booking_date?: string;
  confirmation_date?: string;
  cancellation_date?: string;
  cancellation_reason?: string;
  payment_method?: string;
  is_prepaid: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class BookingsService {
  private apiUrl = `${environment.apiUrl}/bookings`;

  constructor(private http: HttpClient) {}

  // Flight Booking Methods
  getAllFlightBookings(filters?: {
    status?: string;
    trf_id?: number;
    user_id?: number;
    page?: number;
    page_size?: number;
  }): Observable<any> {
    let params = new HttpParams();

    if (filters) {
      if (filters.status) params = params.set('status', filters.status);
      if (filters.trf_id) params = params.set('trf_id', filters.trf_id.toString());
      if (filters.user_id) params = params.set('user_id', filters.user_id.toString());
      if (filters.page) params = params.set('page', filters.page.toString());
      if (filters.page_size) params = params.set('page_size', filters.page_size.toString());
    }

    return this.http.get<any>(`${this.apiUrl}/flights/`, { params });
  }

  getFlightBookingById(id: number): Observable<FlightBooking> {
    return this.http.get<FlightBooking>(`${this.apiUrl}/flights/${id}/`);
  }

  createFlightBooking(data: Partial<FlightBooking>): Observable<FlightBooking> {
    return this.http.post<FlightBooking>(`${this.apiUrl}/flights/`, data);
  }

  updateFlightBooking(id: number, data: Partial<FlightBooking>): Observable<FlightBooking> {
    return this.http.put<FlightBooking>(`${this.apiUrl}/flights/${id}/`, data);
  }

  deleteFlightBooking(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/flights/${id}/`);
  }

  confirmFlightBooking(id: number): Observable<FlightBooking> {
    return this.http.post<FlightBooking>(`${this.apiUrl}/flights/${id}/confirm/`, {});
  }

  issueTicket(id: number, ticketNumber: string): Observable<FlightBooking> {
    return this.http.post<FlightBooking>(`${this.apiUrl}/flights/${id}/issue_ticket/`, {
      ticket_number: ticketNumber
    });
  }

  cancelFlightBooking(id: number, reason?: string): Observable<FlightBooking> {
    return this.http.post<FlightBooking>(`${this.apiUrl}/flights/${id}/cancel/`, {
      reason: reason || ''
    });
  }

  // Hotel Booking Methods
  getAllHotelBookings(filters?: {
    status?: string;
    trf_id?: number;
    user_id?: number;
    page?: number;
    page_size?: number;
  }): Observable<any> {
    let params = new HttpParams();

    if (filters) {
      if (filters.status) params = params.set('status', filters.status);
      if (filters.trf_id) params = params.set('trf_id', filters.trf_id.toString());
      if (filters.user_id) params = params.set('user_id', filters.user_id.toString());
      if (filters.page) params = params.set('page', filters.page.toString());
      if (filters.page_size) params = params.set('page_size', filters.page_size.toString());
    }

    return this.http.get<any>(`${this.apiUrl}/hotels/`, { params });
  }

  getHotelBookingById(id: number): Observable<HotelBooking> {
    return this.http.get<HotelBooking>(`${this.apiUrl}/hotels/${id}/`);
  }

  createHotelBooking(data: Partial<HotelBooking>): Observable<HotelBooking> {
    return this.http.post<HotelBooking>(`${this.apiUrl}/hotels/`, data);
  }

  updateHotelBooking(id: number, data: Partial<HotelBooking>): Observable<HotelBooking> {
    return this.http.put<HotelBooking>(`${this.apiUrl}/hotels/${id}/`, data);
  }

  deleteHotelBooking(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/hotels/${id}/`);
  }

  confirmHotelBooking(id: number): Observable<HotelBooking> {
    return this.http.post<HotelBooking>(`${this.apiUrl}/hotels/${id}/confirm/`, {});
  }

  cancelHotelBooking(id: number, reason?: string): Observable<HotelBooking> {
    return this.http.post<HotelBooking>(`${this.apiUrl}/hotels/${id}/cancel/`, {
      reason: reason || ''
    });
  }

  // Statistics
  getBookingStats(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/stats/`);
  }
}
