export interface FlightBooking {
  id: string;
  trfId: string;
  userId: string;
  airline: string;
  flightNumber: string;
  departureAirport: string;
  arrivalAirport: string;
  departureTime: Date;
  arrivalTime: Date;
  bookingClass: BookingClass;
  status: BookingStatus;
  cost: number;
  bookingReference: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface HotelBooking {
  id: string;
  trfId: string;
  userId: string;
  hotelName: string;
  location: string;
  checkInDate: Date;
  checkOutDate: Date;
  roomType: string;
  numberOfRooms: number;
  status: BookingStatus;
  cost: number;
  bookingReference: string;
  createdAt: Date;
  updatedAt: Date;
}

export enum BookingClass {
  ECONOMY = 'ECONOMY',
  PREMIUM_ECONOMY = 'PREMIUM_ECONOMY',
  BUSINESS = 'BUSINESS',
  FIRST = 'FIRST'
}

export enum BookingStatus {
  REQUESTED = 'REQUESTED',
  CONFIRMED = 'CONFIRMED',
  CANCELLED = 'CANCELLED'
}
