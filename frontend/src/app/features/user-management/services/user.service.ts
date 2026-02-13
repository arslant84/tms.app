import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface Role {
  id: string;  // UUID
  name: string;
  description?: string;
  permissions?: Permission[];
  created_at: string;
  updated_at: string;
}

export interface Permission {
  id: string;  // UUID
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  role?: Role;
  department: string;
  is_admin: boolean;
  is_active: boolean;
  staff_id?: string;
  phone?: string;
  profile_photo?: string;
  gender?: string;
  last_login_at?: string;
  status?: string;
}

export interface UserCreate {
  email: string;
  name: string;
  password: string;
  password_confirm: string;
  role?: string;  // UUID
  department?: string;
  is_admin?: boolean;
  is_active?: boolean;
  staff_id?: string;
  phone?: string;
  gender?: string;
}

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private apiUrl = `${environment.apiUrl}`;

  constructor(private http: HttpClient) {}

  // User CRUD operations
  getAllUsers(filters?: {
    search?: string;
    role?: string;  // UUID
    department?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Observable<any> {
    let params = new HttpParams();

    if (filters) {
      if (filters.search) params = params.set('search', filters.search);
      if (filters.role) params = params.set('role', filters.role);
      if (filters.department) params = params.set('department', filters.department);
      if (filters.is_active !== undefined) params = params.set('is_active', filters.is_active.toString());
      if (filters.page) params = params.set('page', filters.page.toString());
      if (filters.page_size) params = params.set('page_size', filters.page_size.toString());
    }

    return this.http.get<any>(`${this.apiUrl}/users/`, { params });
  }

  getUserById(id: number): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/users/${id}/`);
  }

  createUser(data: UserCreate): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/users/`, data);
  }

  updateUser(id: number, data: Partial<User>): Observable<User> {
    return this.http.patch<User>(`${this.apiUrl}/users/${id}/`, data);
  }

  deleteUser(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/users/${id}/`);
  }

  changePassword(data: { old_password: string; new_password: string }): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/users/change-password/`, data);
  }

  // Role operations
  getAllRoles(): Observable<any> {
    // Disable pagination for roles by requesting a large page size
    const params = new HttpParams().set('page_size', '1000');
    return this.http.get<any>(`${this.apiUrl}/roles/`, { params });
  }

  getRoleById(id: string): Observable<Role> {
    return this.http.get<Role>(`${this.apiUrl}/roles/${id}/`);
  }

  createRole(data: Partial<Role>): Observable<Role> {
    return this.http.post<Role>(`${this.apiUrl}/roles/`, data);
  }

  updateRole(id: string, data: Partial<Role>): Observable<Role> {
    return this.http.put<Role>(`${this.apiUrl}/roles/${id}/`, data);
  }

  deleteRole(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/roles/${id}/`);
  }

  // Permission operations
  getAllPermissions(): Observable<Permission[]> {
    return this.http.get<Permission[]>(`${this.apiUrl}/permissions/`);
  }
}
