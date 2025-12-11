import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { FlightBooking, HotelBooking, BookingStatus, BookingClass } from '../models/booking.model';

@Injectable({
  providedIn: 'root'
})
export class BookingService {
  private mockFlightBookings: FlightBooking[] = [
    {
      id: '1',
      trfId: '1',
      userId: '1',
      airline: 'Delta Airlines',
      flightNumber: 'DL1234',
      departureAirport: 'JFK',
      arrivalAirport: 'LAX',
      departureTime: new Date('2025-06-15T08:00:00'),
      arrivalTime: new Date('2025-06-15T11:30:00'),
      bookingClass: BookingClass.ECONOMY,
      status: BookingStatus.CONFIRMED,
      cost: 450,
      bookingReference: 'DL123456',
      createdAt: new Date('2025-05-20'),
      updatedAt: new Date('2025-05-20')
    }
  ];

  private mockHotelBookings: HotelBooking[] = [
    {
      id: '1',
      trfId: '1',
      userId: '1',
      hotelName: 'Marriott Downtown',
      location: 'New York',
      checkInDate: new Date('2025-06-15'),
      checkOutDate: new Date('2025-06-20'),
      roomType: 'Deluxe King',
      numberOfRooms: 1,
      status: BookingStatus.CONFIRMED,
      cost: 1200,
      bookingReference: 'MAR987654',
      createdAt: new Date('2025-05-20'),
      updatedAt: new Date('2025-05-20')
    }
  ];

  constructor(private http: HttpClient) { }

  // Flight Booking Methods
  
  // Search for available flights
  searchFlights(origin: string, destination: string, departureDate: Date): Observable<any[]> {
    // In a real app, this would make an API call to a flight search service
    // For demo purposes, we'll return mock flight search results
    return of([
      {
        airline: 'Delta Airlines',
        flightNumber: 'DL1234',
        departureAirport: origin,
        arrivalAirport: destination,
        departureTime: new Date(departureDate.setHours(8, 0, 0)),
        arrivalTime: new Date(departureDate.setHours(11, 30, 0)),
        duration: '3h 30m',
        price: 450,
        availableSeats: 12,
        class: BookingClass.ECONOMY
      },
      {
        airline: 'American Airlines',
        flightNumber: 'AA5678',
        departureAirport: origin,
        arrivalAirport: destination,
        departureTime: new Date(departureDate.setHours(10, 0, 0)),
        arrivalTime: new Date(departureDate.setHours(13, 15, 0)),
        duration: '3h 15m',
        price: 520,
        availableSeats: 8,
        class: BookingClass.ECONOMY
      },
      {
        airline: 'United Airlines',
        flightNumber: 'UA9012',
        departureAirport: origin,
        arrivalAirport: destination,
        departureTime: new Date(departureDate.setHours(14, 0, 0)),
        arrivalTime: new Date(departureDate.setHours(17, 20, 0)),
        duration: '3h 20m',
        price: 480,
        availableSeats: 5,
        class: BookingClass.ECONOMY
      }
    ]);
  }

  // Get all flight bookings for a user
  getFlightBookings(userId: string): Observable<FlightBooking[]> {
    // In a real app, this would make an API call
    return of(this.mockFlightBookings.filter(booking => booking.userId === userId));
  }

  // Get flight booking by ID
  getFlightBookingById(id: string): Observable<FlightBooking | undefined> {
    // In a real app, this would make an API call
    const booking = this.mockFlightBookings.find(b => b.id === id);
    return of(booking);
  }

  // Create a new flight booking
  createFlightBooking(booking: Partial<FlightBooking>): Observable<FlightBooking> {
    // In a real app, this would make an API call
    const newBooking: FlightBooking = {
      id: (this.mockFlightBookings.length + 1).toString(),
      trfId: booking.trfId || '',
      userId: booking.userId || '',
      airline: booking.airline || '',
      flightNumber: booking.flightNumber || '',
      departureAirport: booking.departureAirport || '',
      arrivalAirport: booking.arrivalAirport || '',
      departureTime: booking.departureTime || new Date(),
      arrivalTime: booking.arrivalTime || new Date(),
      bookingClass: booking.bookingClass || BookingClass.ECONOMY,
      status: BookingStatus.REQUESTED,
      cost: booking.cost || 0,
      bookingReference: this.generateBookingReference(),
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    this.mockFlightBookings.push(newBooking);
    return of(newBooking);
  }

  // Hotel Booking Methods
  
  // Search for available hotels
  searchHotels(location: string, checkIn: Date, checkOut: Date): Observable<any[]> {
    // In a real app, this would make an API call to a hotel search service
    // For demo purposes, we'll return mock hotel search results
    return of([
      {
        hotelName: 'Marriott Downtown',
        location: location,
        address: '123 Main St',
        checkInDate: checkIn,
        checkOutDate: checkOut,
        roomType: 'Deluxe King',
        price: 240,
        availableRooms: 5,
        amenities: ['Free WiFi', 'Pool', 'Gym', 'Restaurant']
      },
      {
        hotelName: 'Hilton Garden Inn',
        location: location,
        address: '456 Park Ave',
        checkInDate: checkIn,
        checkOutDate: checkOut,
        roomType: 'Queen Suite',
        price: 180,
        availableRooms: 8,
        amenities: ['Free WiFi', 'Breakfast', 'Business Center']
      },
      {
        hotelName: 'Hyatt Regency',
        location: location,
        address: '789 Broadway',
        checkInDate: checkIn,
        checkOutDate: checkOut,
        roomType: 'Executive Suite',
        price: 320,
        availableRooms: 3,
        amenities: ['Free WiFi', 'Pool', 'Spa', 'Restaurant', 'Bar']
      }
    ]);
  }

  // Get all hotel bookings for a user
  getHotelBookings(userId: string): Observable<HotelBooking[]> {
    // In a real app, this would make an API call
    return of(this.mockHotelBookings.filter(booking => booking.userId === userId));
  }

  // Get hotel booking by ID
  getHotelBookingById(id: string): Observable<HotelBooking | undefined> {
    // In a real app, this would make an API call
    const booking = this.mockHotelBookings.find(b => b.id === id);
    return of(booking);
  }

  // Create a new hotel booking
  createHotelBooking(booking: Partial<HotelBooking>): Observable<HotelBooking> {
    // In a real app, this would make an API call
    const newBooking: HotelBooking = {
      id: (this.mockHotelBookings.length + 1).toString(),
      trfId: booking.trfId || '',
      userId: booking.userId || '',
      hotelName: booking.hotelName || '',
      location: booking.location || '',
      checkInDate: booking.checkInDate || new Date(),
      checkOutDate: booking.checkOutDate || new Date(),
      roomType: booking.roomType || '',
      numberOfRooms: booking.numberOfRooms || 1,
      status: BookingStatus.REQUESTED,
      cost: booking.cost || 0,
      bookingReference: this.generateBookingReference(),
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    this.mockHotelBookings.push(newBooking);
    return of(newBooking);
  }

  // Helper method to generate a booking reference
  private generateBookingReference(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < 8; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }
}
