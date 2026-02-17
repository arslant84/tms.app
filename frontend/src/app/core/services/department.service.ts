import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Department, DepartmentListItem } from '../models/user.model';

export interface DepartmentCreatePayload {
  name: string;
  code?: string;
  description?: string;
  is_active?: boolean;
}

export interface DepartmentUpdatePayload {
  name?: string;
  code?: string;
  description?: string;
  is_active?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class DepartmentService {
  private apiUrl = `${environment.apiUrl}/departments`;

  constructor(private http: HttpClient) {}

  /**
   * Get all departments
   */
  getDepartments(): Observable<Department[]> {
    return this.http.get<Department[]>(this.apiUrl + '/');
  }

  /**
   * Get only active departments (for dropdowns)
   */
  getActiveDepartments(): Observable<DepartmentListItem[]> {
    return this.http.get<DepartmentListItem[]>(`${this.apiUrl}/active/`);
  }

  /**
   * Get a single department by ID
   */
  getDepartment(id: string): Observable<Department> {
    return this.http.get<Department>(`${this.apiUrl}/${id}/`);
  }

  /**
   * Create a new department
   */
  createDepartment(data: DepartmentCreatePayload): Observable<Department> {
    return this.http.post<Department>(this.apiUrl + '/', data);
  }

  /**
   * Update an existing department
   */
  updateDepartment(id: string, data: DepartmentUpdatePayload): Observable<Department> {
    return this.http.patch<Department>(`${this.apiUrl}/${id}/`, data);
  }

  /**
   * Delete a department
   */
  deleteDepartment(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`);
  }

  /**
   * Get department name from a Department object or string
   * Helper function for templates
   */
  getDepartmentName(department: Department | DepartmentListItem | string | null | undefined): string {
    if (!department) {
      return '';
    }
    if (typeof department === 'string') {
      return department;
    }
    return department.name || '';
  }
}
