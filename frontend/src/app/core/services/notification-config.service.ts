import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  WorkflowStepNotificationConfig,
  Role,
  NotificationTemplate,
  WorkflowUser
} from '../models/workflow.models';

export interface NotificationConfigOptions {
  trigger_events: Array<{ value: string; display: string }>;
  recipient_types: Array<{ value: string; display: string }>;
  priorities: Array<{ value: string; display: string }>;
  roles: Role[];
  users: WorkflowUser[];
  templates: NotificationTemplate[];
}

export interface NotificationConfigListResponse {
  count?: number;
  next?: string;
  previous?: string;
  results: WorkflowStepNotificationConfig[];
}

/**
 * Service for managing workflow step notification configurations
 * Provides CRUD operations for notification config in workflow steps
 */
@Injectable({ providedIn: 'root' })
export class NotificationConfigService {
  private baseUrl = `${environment.apiUrl}/workflows/notification-configs`;

  constructor(private http: HttpClient) {}

  /**
   * Get all notification configurations
   * @param params Optional query parameters for filtering
   */
  getConfigs(params?: {
    workflow_step?: string;
    trigger_event?: string;
    entity_type?: string;
    is_active?: boolean;
  }): Observable<NotificationConfigListResponse> {
    let httpParams = new HttpParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          httpParams = httpParams.set(key, String(value));
        }
      });
    }
    return this.http.get<NotificationConfigListResponse>(this.baseUrl, { params: httpParams });
  }

  /**
   * Get a specific notification configuration by ID
   * @param id Configuration ID
   */
  getConfig(id: string): Observable<WorkflowStepNotificationConfig> {
    return this.http.get<WorkflowStepNotificationConfig>(`${this.baseUrl}/${id}/`);
  }

  /**
   * Get all notification configurations for a specific workflow step
   * @param stepId Workflow step ID
   */
  getConfigsByStep(stepId: string): Observable<WorkflowStepNotificationConfig[]> {
    return this.http.get<WorkflowStepNotificationConfig[]>(`${this.baseUrl}/by_step/${stepId}/`);
  }

  /**
   * Create a new notification configuration
   * @param config Notification configuration data
   */
  createConfig(config: WorkflowStepNotificationConfig): Observable<WorkflowStepNotificationConfig> {
    return this.http.post<WorkflowStepNotificationConfig>(this.baseUrl + '/', config);
  }

  /**
   * Update an existing notification configuration
   * @param id Configuration ID
   * @param config Updated configuration data
   */
  updateConfig(id: string, config: Partial<WorkflowStepNotificationConfig>): Observable<WorkflowStepNotificationConfig> {
    return this.http.put<WorkflowStepNotificationConfig>(`${this.baseUrl}/${id}/`, config);
  }

  /**
   * Partially update a notification configuration
   * @param id Configuration ID
   * @param config Partial configuration data
   */
  patchConfig(id: string, config: Partial<WorkflowStepNotificationConfig>): Observable<WorkflowStepNotificationConfig> {
    return this.http.patch<WorkflowStepNotificationConfig>(`${this.baseUrl}/${id}/`, config);
  }

  /**
   * Delete a notification configuration
   * @param id Configuration ID
   */
  deleteConfig(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}/`);
  }

  /**
   * Get dropdown options for notification configuration form
   * Returns trigger events, recipient types, priorities, roles, users, and templates
   */
  getOptions(): Observable<NotificationConfigOptions> {
    return this.http.get<NotificationConfigOptions>(`${this.baseUrl}/options/`);
  }

  /**
   * Preview who will receive notifications based on configuration
   * @param config Notification configuration to preview
   */
  previewRecipients(config: Partial<WorkflowStepNotificationConfig>): Observable<{
    to: WorkflowUser[];
    cc: WorkflowUser[];
    bcc: WorkflowUser[];
  }> {
    return this.http.post<{
      to: WorkflowUser[];
      cc: WorkflowUser[];
      bcc: WorkflowUser[];
    }>(`${this.baseUrl}/preview/`, config);
  }
}
