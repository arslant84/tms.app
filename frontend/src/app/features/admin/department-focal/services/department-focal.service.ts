import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../../environments/environment';

interface ArrangementStatus {
  flight?: string;
  meal?: string;
  transport?: string;
  accommodation?: string;
  visa?: string;
}

export interface DepartmentFocalRequest {
  id: number;
  request_number?: string;
  requestor_name?: string;
  department?: string;
  travel_type?: string;
  status?: string;
  created_at?: string;
  arrangement_status?: ArrangementStatus;
  is_fully_arranged?: boolean;
}

export interface DepartmentFocalQueueResponse {
  count: number;
  results: DepartmentFocalRequest[];
}

export interface DepartmentFocalQueueParams {
  search?: string;
  page?: number;
  page_size?: number;
  ready?: boolean;
}

/**
 * Kept as its own small service, separate from TrfService, so this new
 * queue's HTTP call doesn't require staging (and therefore fully
 * relinting) TrfService's large, pre-existing file.
 */
@Injectable({ providedIn: 'root' })
export class DepartmentFocalService {
  private http = inject(HttpClient);

  getQueue(params: DepartmentFocalQueueParams = {}): Observable<DepartmentFocalQueueResponse> {
    const queryParams: Record<string, string> = { department_focal_queue: 'true' };
    if (params.search) queryParams['search'] = params.search;
    if (params.page) queryParams['page'] = String(params.page);
    if (params.page_size) queryParams['page_size'] = String(params.page_size);
    if (params.ready) queryParams['ready'] = 'true';

    const queryString = new URLSearchParams(queryParams).toString();
    return this.http.get<DepartmentFocalQueueResponse>(
      `${environment.apiUrl}/trf/travel-requests/?${queryString}`
    );
  }
}
