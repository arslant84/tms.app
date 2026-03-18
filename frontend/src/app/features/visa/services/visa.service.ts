import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';

export interface VisaApplicationDetail extends VisaApplication {
  applicant_name?: string;
  user_email?: string;
  approval_workflow?: VisaApprovalStep[];
  documents?: VisaDocument[];
}

export interface VisaApplication {
  id: number;
  request_number?: string;
  user: number | null;
  requestor_name: string;
  email?: string;
  staff_id?: string;
  department?: string;
  position?: string;
  contact_telephone?: string;
  home_address?: string;

  // Travel Details
  destination: string;
  travel_purpose: string;
  trip_start_date?: string;
  trip_end_date?: string;
  approximately_arrival_date?: string;
  duration_of_stay?: string;
  itinerary_details?: string;

  // Visa Information
  visa_type: string;
  visa_entry_type?: string;
  request_type: string;
  work_visit_category?: string;

  // Passport Details
  passport_number?: string;
  passport_expiry_date?: string;
  passport_place_of_issuance?: string;
  passport_date_of_issuance?: string;
  passport_file?: string;
  passport_file_url?: string;

  // Personal Demographics
  date_of_birth?: string;
  place_of_birth?: string;
  citizenship?: string;
  marital_status?: string;
  family_information?: string;
  education_details?: string;

  // Employment Information
  current_employer_name?: string;
  current_employer_address?: string;

  // Cost & References
  application_fees_borne_by?: string;
  cost_centre_number?: string;
  trf_reference_number?: string;

  // Status & Tracking
  status: string;
  processing_details?: any;
  processing_started_at?: string;
  processing_completed_at?: string;
  submitted_date: string;
  last_updated_date: string;
  created_at: string;
  updated_at: string;

  // Miscellaneous
  additional_comments?: string;
  supporting_documents_notes?: string;
}

export interface VisaApprovalStep {
  id: number;
  visa: number;
  step_role: string;
  step_name: string;
  status: string;
  step_date: string;
  comments?: string;
  created_at: string;
  updated_at: string;
}

export interface VisaDocument {
  id: number;
  visa: number;
  document_name: string;
  document_path: string;
  document_type?: string;
  uploaded_at: string;
  uploaded_by?: string;
}

export interface VisaFilters {
  status?: string;
  visa_type?: string;
  destination?: string;
  search?: string;
  page?: number;
  page_size?: number;
  adminView?: boolean;  // Set to true when viewing from Visa Admin module
}

@Injectable({
  providedIn: 'root'
})
export class VisaService {

  private apiUrl = `${environment.apiUrl}/visa/applications/`;
  private approvalStepsUrl = `${environment.apiUrl}/visa/approval-steps/`;
  private documentsUrl = `${environment.apiUrl}/visa/documents/`;

  constructor(private http: HttpClient) { }

  // Visa Applications CRUD
  getAllApplications(filters?: VisaFilters): Observable<any> {
    let params = new HttpParams();
    if (filters) {
      if (filters.status) params = params.set('status', filters.status);
      if (filters.visa_type) params = params.set('visa_type', filters.visa_type);
      if (filters.destination) params = params.set('destination', filters.destination);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.page) params = params.set('page', filters.page.toString());
      if (filters.page_size) params = params.set('page_size', filters.page_size.toString());
      // Add admin_view parameter for admin modules (side navbar)
      if (filters.adminView) params = params.set('admin_view', 'true');
    }
    // Add cache-busting parameter to prevent stale data
    params = params.set('_t', Date.now().toString());
    return this.http.get<any>(this.apiUrl, { params });
  }

  getApplicationById(id: number, adminView: boolean = false): Observable<VisaApplication> {
    let params = new HttpParams();
    if (adminView) {
      params = params.set('admin_view', 'true');
    }
    return this.http.get<VisaApplication>(`${this.apiUrl}${id}/`, { params });
  }

  createApplication(data: Partial<VisaApplication>): Observable<VisaApplication> {
    return this.http.post<VisaApplication>(this.apiUrl, data);
  }

  updateApplication(id: number, data: Partial<VisaApplication>): Observable<VisaApplication> {
    return this.http.patch<VisaApplication>(`${this.apiUrl}${id}/`, data);
  }

  deleteApplication(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}${id}/`);
  }

  // New endpoints matching backend
  getPendingApprovals(): Observable<VisaApplication[]> {
    return this.http.get<VisaApplication[]>(`${this.apiUrl}pending-approvals/`);
  }

  getMyApplications(): Observable<VisaApplication[]> {
    return this.http.get<VisaApplication[]>(`${this.apiUrl}my-applications/`);
  }

  approveAtStep(id: number, stepRole: string, comments: string = ''): Observable<VisaApplicationDetail> {
    return this.http.post<VisaApplicationDetail>(`${this.apiUrl}${id}/approve/`, {
      step_role: stepRole,
      comments: comments
    });
  }

  rejectAtStep(id: number, stepRole: string, comments: string = ''): Observable<VisaApplicationDetail> {
    return this.http.post<VisaApplicationDetail>(`${this.apiUrl}${id}/reject/`, {
      step_role: stepRole,
      comments: comments
    });
  }

  // Submit application for approval with optional approver selection
  submitApplication(
    id: number,
    selectedApprovers?: { [stepOrder: number]: number },
    skippedSteps?: { [stepOrder: number]: string | null }
  ): Observable<VisaApplication> {
    const payload: any = {};
    if (selectedApprovers && Object.keys(selectedApprovers).length > 0) {
      payload.selected_approvers = selectedApprovers;
    }
    if (skippedSteps && Object.keys(skippedSteps).length > 0) {
      payload.skipped_steps = skippedSteps;
    }
    return this.http.post<VisaApplication>(`${this.apiUrl}${id}/submit/`, payload);
  }

  approveApplication(id: number, comments?: string): Observable<VisaApplication> {
    return this.http.patch<VisaApplication>(`${this.apiUrl}${id}/`, {
      status: 'Approved',
      additional_comments: comments
    });
  }

  rejectApplication(id: number, comments?: string): Observable<VisaApplication> {
    return this.http.patch<VisaApplication>(`${this.apiUrl}${id}/`, {
      status: 'Rejected',
      additional_comments: comments
    });
  }

  cancelApplication(id: number): Observable<VisaApplication> {
    return this.http.patch<VisaApplication>(`${this.apiUrl}${id}/`, {
      status: 'Cancelled'
    });
  }

  completeApplication(id: number, data?: { processing_details?: any; additional_comments?: string }): Observable<VisaApplication> {
    return this.http.post<VisaApplication>(`${this.apiUrl}${id}/complete/`, data || {});
  }

  // Approval Steps
  getApprovalSteps(visaId: number): Observable<VisaApprovalStep[]> {
    const params = new HttpParams().set('visa', visaId.toString());
    return this.http.get<VisaApprovalStep[]>(this.approvalStepsUrl, { params });
  }

  createApprovalStep(data: Partial<VisaApprovalStep>): Observable<VisaApprovalStep> {
    return this.http.post<VisaApprovalStep>(this.approvalStepsUrl, data);
  }

  updateApprovalStep(id: number, data: Partial<VisaApprovalStep>): Observable<VisaApprovalStep> {
    return this.http.put<VisaApprovalStep>(`${this.approvalStepsUrl}${id}/`, data);
  }

  // Documents
  getDocuments(visaId: number): Observable<VisaDocument[]> {
    const params = new HttpParams().set('visa', visaId.toString());
    return this.http.get<VisaDocument[]>(this.documentsUrl, { params });
  }

  uploadDocument(data: FormData): Observable<VisaDocument> {
    return this.http.post<VisaDocument>(this.documentsUrl, data);
  }

  deleteDocument(id: number): Observable<void> {
    return this.http.delete<void>(`${this.documentsUrl}${id}/`);
  }

  // Passport File Upload
  uploadPassportFile(applicationId: number, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('passport_file', file);
    return this.http.post<any>(`${this.apiUrl}${applicationId}/upload-passport/`, formData);
  }

  deletePassportFile(applicationId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}${applicationId}/delete-passport-file/`);
  }

  // Export visa application to PDF
  exportToPdf(id: number): Observable<Blob> {
    return this.http.get(`${this.apiUrl}${id}/export-pdf/`, {
      responseType: 'blob'
    }).pipe(
      catchError(error => {
        console.error('PDF export error:', error);
        return throwError(() => error);
      })
    );
  }
}
