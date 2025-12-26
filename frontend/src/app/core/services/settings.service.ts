import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ApplicationSetting {
  id: string;
  setting_key: string;
  setting_value: any; // Raw string value from database
  value?: any; // Typed value (if returned by backend)
  setting_type: 'string' | 'boolean' | 'number' | 'json';
  description?: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface SettingUpdate {
  setting_key: string;
  value: any;
}

export interface BulkUpdateResponse {
  updated: ApplicationSetting[];
  errors: any[];
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private apiUrl = `${environment.apiUrl}/settings`;

  constructor(private http: HttpClient) {}

  /**
   * Get all settings as an array
   * For admin use - returns all settings regardless of public flag
   */
  getAllSettings(): Observable<ApplicationSetting[]> {
    return this.http.get<ApplicationSetting[]>(`${this.apiUrl}/`);
  }

  /**
   * Get only public settings (for unauthenticated/non-admin users)
   */
  getPublicSettings(): Observable<ApplicationSetting[]> {
    return this.http.get<ApplicationSetting[]>(`${this.apiUrl}/`, {
      params: { public: 'true' }
    });
  }

  /**
   * Get a single setting by key
   */
  getSetting(key: string): Observable<ApplicationSetting> {
    return this.http.get<ApplicationSetting>(`${this.apiUrl}/${key}/`);
  }

  /**
   * Create a new setting
   */
  createSetting(setting: {
    setting_key: string;
    value: any;
    setting_type: 'string' | 'boolean' | 'number' | 'json';
    description?: string;
    is_public?: boolean;
  }): Observable<ApplicationSetting> {
    return this.http.post<ApplicationSetting>(`${this.apiUrl}/`, setting);
  }

  /**
   * Update a single setting
   */
  updateSetting(key: string, data: {
    value?: any;
    setting_type?: 'string' | 'boolean' | 'number' | 'json';
    description?: string;
    is_public?: boolean;
  }): Observable<ApplicationSetting> {
    return this.http.patch<ApplicationSetting>(`${this.apiUrl}/${key}/`, data);
  }

  /**
   * Bulk update multiple settings
   */
  bulkUpdateSettings(settings: SettingUpdate[]): Observable<BulkUpdateResponse> {
    return this.http.put<BulkUpdateResponse>(`${this.apiUrl}/bulk_update/`, {
      settings
    });
  }

  /**
   * Delete a setting
   */
  deleteSetting(key: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${key}/`);
  }
}
