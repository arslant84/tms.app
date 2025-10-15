import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { TravelRequestForm, TRFStatus, TravelType, ApprovalStatus } from '../models/trf.model';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class TrfService {
  private apiUrl = `${environment.apiUrl}/trf`;

  private mockTrfs: TravelRequestForm[] = [
    {
      id: '1',
      requesterId: '1',
      requesterName: 'John Doe',
      purpose: 'Client Meeting',
      destination: 'New York',
      departureDate: new Date('2025-06-15'),
      returnDate: new Date('2025-06-20'),
      travelType: TravelType.DOMESTIC,
      accommodationRequired: true,
      estimatedCost: 2500,
      status: TRFStatus.APPROVED,
      approvalChain: [
        {
          approverId: '3',
          approverName: 'Jane Smith',
          status: ApprovalStatus.APPROVED,
          comments: 'Approved as per policy',
          timestamp: new Date('2025-05-20')
        }
      ],
      createdAt: new Date('2025-05-15'),
      updatedAt: new Date('2025-05-20')
    },
    {
      id: '2',
      requesterId: '1',
      requesterName: 'John Doe',
      purpose: 'Conference',
      destination: 'London',
      departureDate: new Date('2025-07-10'),
      returnDate: new Date('2025-07-15'),
      travelType: TravelType.INTERNATIONAL,
      accommodationRequired: true,
      estimatedCost: 5000,
      status: TRFStatus.PENDING_APPROVAL,
      approvalChain: [
        {
          approverId: '3',
          approverName: 'Jane Smith',
          status: ApprovalStatus.PENDING
        }
      ],
      createdAt: new Date('2025-05-25'),
      updatedAt: new Date('2025-05-25')
    }
  ];

  constructor(private http: HttpClient) { }

  // Get all TRFs for the current user with optional filters
  getAllTrfs(filters?: any): Observable<any> {
    let params = new HttpParams();

    if (filters) {
      Object.keys(filters).forEach(key => {
        if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
          params = params.set(key, filters[key].toString());
        }
      });
    }

    return this.http.get<any>(`${this.apiUrl}/`, { params });
  }

  // Get a specific TRF by ID
  getTrfById(id: string): Observable<TravelRequestForm | undefined> {
    // In a real app, this would make an API call
    const trf = this.mockTrfs.find(t => t.id === id);
    return of(trf);
  }

  // Create a new TRF
  createTrf(trf: Partial<TravelRequestForm>): Observable<TravelRequestForm> {
    // In a real app, this would make an API call
    const newTrf: TravelRequestForm = {
      id: (this.mockTrfs.length + 1).toString(),
      requesterId: '1',
      requesterName: 'John Doe',
      purpose: trf.purpose || '',
      destination: trf.destination || '',
      departureDate: trf.departureDate || new Date(),
      returnDate: trf.returnDate || new Date(),
      travelType: trf.travelType || TravelType.DOMESTIC,
      accommodationRequired: trf.accommodationRequired || false,
      estimatedCost: trf.estimatedCost || 0,
      status: TRFStatus.DRAFT,
      approvalChain: [],
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    this.mockTrfs.push(newTrf);
    return of(newTrf);
  }

  // Update an existing TRF
  updateTrf(id: string, trf: Partial<TravelRequestForm>): Observable<TravelRequestForm | undefined> {
    // In a real app, this would make an API call
    const index = this.mockTrfs.findIndex(t => t.id === id);
    if (index === -1) return of(undefined);
    
    const updatedTrf = { ...this.mockTrfs[index], ...trf, updatedAt: new Date() };
    this.mockTrfs[index] = updatedTrf;
    
    return of(updatedTrf);
  }

  // Submit a TRF for approval
  submitTrf(id: string): Observable<TravelRequestForm | undefined> {
    // In a real app, this would make an API call
    const index = this.mockTrfs.findIndex(t => t.id === id);
    if (index === -1) return of(undefined);
    
    const updatedTrf = { 
      ...this.mockTrfs[index], 
      status: TRFStatus.SUBMITTED, 
      updatedAt: new Date(),
      approvalChain: [
        {
          approverId: '3',
          approverName: 'Jane Smith',
          status: ApprovalStatus.PENDING
        }
      ]
    };
    
    this.mockTrfs[index] = updatedTrf;
    return of(updatedTrf);
  }

  // Cancel a TRF
  cancelTrf(id: string): Observable<TravelRequestForm | undefined> {
    // In a real app, this would make an API call
    const index = this.mockTrfs.findIndex(t => t.id === id);
    if (index === -1) return of(undefined);
    
    const updatedTrf = { 
      ...this.mockTrfs[index], 
      status: TRFStatus.CANCELLED, 
      updatedAt: new Date() 
    };
    
    this.mockTrfs[index] = updatedTrf;
    return of(updatedTrf);
  }
}
