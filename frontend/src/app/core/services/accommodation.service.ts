import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

// Define interfaces for the accommodation request data
export interface AccommodationRequest {
  id: number;
  requestId: string; // BT reference number
  requester: {
    id: number;
    name: string;
    department: string;
    email: string;
  };
  accommodationType: string; // 'ashgabat' or 'kiyanly'
  accommodationName: string;
  roomNumber: string;
  checkInDate: string;
  checkOutDate: string;
  gender: string;
  reason: string;
  specialRequirements?: string;
  relatedTravelRequest?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  dateSubmitted: string;
  priority: 'low' | 'medium' | 'high';
}

@Injectable({
  providedIn: 'root'
})
export class AccommodationService {
  // Store accommodation requests
  private accommodationRequests: AccommodationRequest[] = [];
  
  // BehaviorSubject to notify subscribers when accommodation requests change
  private accommodationRequestsSubject = new BehaviorSubject<AccommodationRequest[]>([]);
  
  // Current user info (mock data - would come from auth service in real app)
  private currentUser = {
    id: 201,
    name: 'John Smith',
    department: 'Marketing',
    email: 'john.smith@example.com'
  };

  constructor() {
    // Load any existing requests from localStorage
    this.loadFromStorage();
  }

  // Get all accommodation requests as an observable
  getAccommodationRequests(): Observable<AccommodationRequest[]> {
    return this.accommodationRequestsSubject.asObservable();
  }

  // Submit a new accommodation request
  submitAccommodationRequest(formData: any): Observable<{success: boolean, reference: string}> {
    // Generate a BT (Business Trip) Reference Number
    const btReference = `BT-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
    
    // Create new request object
    const newRequest: AccommodationRequest = {
      id: this.getNextId(),
      requestId: btReference,
      requester: this.currentUser,
      accommodationType: formData.accommodationType,
      accommodationName: this.getAccommodationName(formData.accommodationType, formData.selectedAccommodation),
      roomNumber: formData.selectedRoom.replace('room', ''),
      checkInDate: formData.checkInDate,
      checkOutDate: formData.checkOutDate,
      gender: formData.gender,
      reason: formData.reason,
      specialRequirements: formData.specialRequirements || '',
      relatedTravelRequest: formData.relatedTravelRequest || '',
      status: 'pending',
      dateSubmitted: new Date().toISOString(),
      priority: 'medium' // Default priority
    };
    
    // Add to the requests array
    this.accommodationRequests.push(newRequest);
    
    // Update the BehaviorSubject
    this.accommodationRequestsSubject.next([...this.accommodationRequests]);
    
    // Save to localStorage
    this.saveToStorage();
    
    // Return success response (simulating API call with delay)
    return of({success: true, reference: btReference}).pipe(delay(1500));
  }

  // Update the status of an accommodation request
  updateRequestStatus(id: number, status: 'pending' | 'in_progress' | 'completed' | 'cancelled'): Observable<boolean> {
    const index = this.accommodationRequests.findIndex(req => req.id === id);
    
    if (index !== -1) {
      this.accommodationRequests[index].status = status;
      this.accommodationRequestsSubject.next([...this.accommodationRequests]);
      this.saveToStorage();
      return of(true).pipe(delay(500));
    }
    
    return of(false);
  }

  // Get a single accommodation request by ID
  getAccommodationRequestById(id: number): Observable<AccommodationRequest | undefined> {
    const request = this.accommodationRequests.find(req => req.id === id);
    return of(request);
  }

  // Helper methods
  private getNextId(): number {
    return this.accommodationRequests.length > 0 
      ? Math.max(...this.accommodationRequests.map(req => req.id)) + 1 
      : 1;
  }

  private getAccommodationName(type: string, id: string): string {
    const accommodations = type === 'ashgabat' 
      ? [
          { id: '41', name: 'Staff House 41' },
          { id: '42', name: 'Staff House 42' }
        ] 
      : [
          { id: '1', name: 'Camp 1' },
          { id: '2', name: 'Camp 2' }
        ];
    
    const accommodation = accommodations.find(a => a.id === id);
    return accommodation ? accommodation.name : '';
  }

  // Storage methods
  private saveToStorage(): void {
    localStorage.setItem('accommodation_requests', JSON.stringify(this.accommodationRequests));
  }

  private loadFromStorage(): void {
    const storedRequests = localStorage.getItem('accommodation_requests');
    if (storedRequests) {
      this.accommodationRequests = JSON.parse(storedRequests);
      this.accommodationRequestsSubject.next([...this.accommodationRequests]);
    }
  }
}
