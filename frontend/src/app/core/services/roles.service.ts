import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface TmsApp_Roles_Permission {
  id: string;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TmsApp_Roles_RoleWithPermissions {
  id: string;
  name: string;
  description?: string | null;
  permissionIds: string[];
  permissions?: TmsApp_Roles_Permission[];
  created_at?: string;
  updated_at?: string;
}

export interface TmsApp_Roles_RoleFormValues {
  name: string;
  description?: string | null;
  permissionIds?: string[];
}

/**
 * TmsApp_Core_Services_RolesService
 * Purpose
 * - Manage roles and permissions data access.
 * Endpoints
 * - GET, POST, PUT at `${apiBase}/admin/settings/roles`
 * - DELETE at `${apiBase}/admin/settings/roles?id=...`
 * Example
 * - rolesService.getRoles().subscribe(...)
 */
@Injectable({ providedIn: 'root' })
export class TmsApp_Core_Services_RolesService {
  private apiBase = environment.apiUrl;
  private rolesUrl = `${this.apiBase}/roles/`;
  private permissionsUrl = `${this.apiBase}/permissions/`;

  constructor(private http: HttpClient) {}

  /** Get all roles with permissions */
  getRoles(): Observable<TmsApp_Roles_RoleWithPermissions[]> {
    return this.http.get<TmsApp_Roles_RoleWithPermissions[]>(this.rolesUrl);
  }

  /** Create role */
  createRole(payload: TmsApp_Roles_RoleFormValues): Observable<TmsApp_Roles_RoleWithPermissions> {
    return this.http.post<TmsApp_Roles_RoleWithPermissions>(this.rolesUrl, payload);
  }

  /** Update role, expects payload plus id */
  updateRole(id: string, payload: TmsApp_Roles_RoleFormValues): Observable<TmsApp_Roles_RoleWithPermissions> {
    return this.http.put<TmsApp_Roles_RoleWithPermissions>(`${this.rolesUrl}${id}/`, payload);
  }

  /** Delete role by id */
  deleteRole(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`${this.rolesUrl}${id}/`);
  }

  /** Get all permissions */
  getPermissions(): Observable<TmsApp_Roles_Permission[]> {
    return this.http.get<TmsApp_Roles_Permission[]>(this.permissionsUrl);
  }
}
