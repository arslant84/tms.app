/**
 * Combined Request Service
 *
 * Handles API communication for Combined Request operations including
 * CRUD, workflow actions, and file uploads.
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map, catchError, throwError } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import {
  CombinedRequest,
  CombinedRequestFilters,
  toFrontendFormat,
  toBackendFormat
} from '../models/combined-request.model';

@Injectable({
  providedIn: 'root'
})
export class CombinedRequestService {
  private apiUrl = `${environment.apiUrl}/combined/combined-requests`;

  constructor(private http: HttpClient) {}

  /**
   * Get all combined requests with optional filtering
   */
  getAll(filters?: CombinedRequestFilters): Observable<{
    results: CombinedRequest[];
    count: number;
    next: string | null;
    previous: string | null;
  }> {
    let params = new HttpParams();

    if (filters) {
      if (filters.status) params = params.set('status', filters.status);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.page) params = params.set('page', filters.page.toString());
      if (filters.pageSize) params = params.set('page_size', filters.pageSize.toString());
      if (filters.adminView) params = params.set('admin_view', 'true');
      if (filters.includeTravel !== undefined) params = params.set('include_travel', filters.includeTravel.toString());
      if (filters.includeTransport !== undefined) params = params.set('include_transport', filters.includeTransport.toString());
      if (filters.includeAccommodation !== undefined) params = params.set('include_accommodation', filters.includeAccommodation.toString());
      if (filters.includeVisa !== undefined) params = params.set('include_visa', filters.includeVisa.toString());
    }

    return this.http.get<any>(`${this.apiUrl}/`, { params }).pipe(
      map(response => ({
        results: (response.data?.results || response.results || []).map((item: any) => toFrontendFormat(item)),
        count: response.data?.count || response.count || 0,
        next: response.data?.next || response.next,
        previous: response.data?.previous || response.previous
      })),
      catchError(this.handleError)
    );
  }

  /**
   * Get a single combined request by ID
   */
  getById(id: number | string): Observable<CombinedRequest> {
    return this.http.get<any>(`${this.apiUrl}/${id}/`).pipe(
      map(response => toFrontendFormat(response.data || response)),
      catchError(this.handleError)
    );
  }

  /**
   * Create a new combined request
   */
  create(data: Partial<CombinedRequest>): Observable<CombinedRequest> {
    const backendData = toBackendFormat(data);
    return this.http.post<any>(`${this.apiUrl}/`, backendData).pipe(
      map(response => toFrontendFormat(response.data || response)),
      catchError(this.handleError)
    );
  }

  /**
   * Update an existing combined request
   */
  update(id: number | string, data: Partial<CombinedRequest>): Observable<CombinedRequest> {
    const backendData = toBackendFormat(data);
    return this.http.patch<any>(`${this.apiUrl}/${id}/`, backendData).pipe(
      map(response => toFrontendFormat(response.data || response)),
      catchError(this.handleError)
    );
  }

  /**
   * Delete a combined request (only allowed for drafts)
   */
  delete(id: number | string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Submit a combined request for approval
   */
  submit(
    id: number | string,
    selectedApprovers?: { [stepOrder: number]: number },
    skippedSteps?: { [stepOrder: number]: string | null }
  ): Observable<any> {
    const payload: any = {};
    if (selectedApprovers && Object.keys(selectedApprovers).length > 0) {
      payload.selected_approvers = selectedApprovers;
    }
    if (skippedSteps && Object.keys(skippedSteps).length > 0) {
      payload.skipped_steps = skippedSteps;
    }
    return this.http.post<any>(`${this.apiUrl}/${id}/submit/`, payload).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Approve the current workflow step
   */
  approve(id: number | string, comments?: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${id}/approve/`, { comments }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Reject a combined request
   */
  reject(id: number | string, reason: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${id}/reject/`, { reason }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Cancel a combined request
   */
  cancel(id: number | string, reason?: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${id}/cancel/`, { reason }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Save admin processing details for one module and mark it completed.
   * The backend auto-transitions the overall status to Completed when all
   * included modules are done.
   */
  processModule(
    id: number | string,
    module: 'travel' | 'transport' | 'accommodation' | 'visa',
    processingData: Record<string, any>
  ): Observable<CombinedRequest> {
    return this.http.post<any>(`${this.apiUrl}/${id}/process-module/`, {
      module,
      processing_data: processingData
    }).pipe(
      map(response => toFrontendFormat(response.data || response)),
      catchError(this.handleError)
    );
  }

  /**
   * Upload a document for a combined request
   */
  uploadDocument(
    requestId: number | string,
    file: File,
    documentType: string,
    module: string,
    description?: string
  ): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    formData.append('module', module);
    if (description) {
      formData.append('description', description);
    }

    return this.http.post<any>(`${this.apiUrl}/${requestId}/upload-document/`, formData).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Delete a document from a combined request
   */
  deleteDocument(requestId: number | string, documentId: number | string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${requestId}/documents/${documentId}/`).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Export request to PDF
   */
  exportToPdf(id: number | string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${id}/export-pdf/`, {
      responseType: 'blob'
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get available approvers for workflow steps
   */
  getAvailableApprovers(): Observable<any[]> {
    return this.http.get<any>(`${environment.apiUrl}/workflows/approvers/`).pipe(
      map(response => response.data || response),
      catchError(this.handleError)
    );
  }

  /**
   * Error handler
   */
  private handleError(error: any): Observable<never> {
    console.error('CombinedRequestService error:', error);
    if (error.error && typeof error.error === 'object') {
      console.error('Validation errors:', JSON.stringify(error.error, null, 2));
    }
    // Flatten DRF field-level validation errors into a readable message
    let message = error.error?.detail || error.error?.message || error.message || 'An error occurred';
    if (error.error && typeof error.error === 'object' && !error.error.detail && !error.error.message) {
      const fieldErrors = Object.entries(error.error)
        .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
        .join('; ');
      if (fieldErrors) message = fieldErrors;
    }
    return throwError(() => new Error(message));
  }
}
