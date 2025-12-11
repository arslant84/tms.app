import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface TmsApp_Notifications_NotificationTemplate {
  id: string;
  name: string;
  description?: string | null;
  subject: string;
  body: string;
  event_type?: string | null;
  event_type_name?: string;
  event_type_module?: string;
  notification_type: string;
  recipient_type: string;
  variables_available?: string[];
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TmsApp_Notifications_NotificationEventType {
  id: string;
  name: string;
  description?: string;
  category: string;
  module: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TmsApp_Notifications_NotificationTemplateFormValues {
  name: string;
  description?: string | null;
  subject: string;
  body: string;
  event_type?: string | null;
  notification_type: string;
  recipient_type: string;
  variables_available?: string[];
  is_active?: boolean;
}

/**
 * TmsApp_Core_Services_NotificationsService
 * Purpose
 * - Manage notification templates and event types.
 * Endpoints
 * - GET /api/notifications/templates/ - List all templates
 * - GET /api/notifications/templates/{id}/ - Get single template
 * - POST /api/notifications/templates/ - Create template
 * - PUT /api/notifications/templates/{id}/ - Update template
 * - DELETE /api/notifications/templates/{id}/ - Delete template
 * - GET /api/notifications/event-types/ - List all event types
 * Example
 * - notificationsService.getTemplates().subscribe(...)
 */
@Injectable({ providedIn: 'root' })
export class TmsApp_Core_Services_NotificationsService {
  private templatesUrl = `${environment.apiUrl}/notifications/templates`;
  private eventTypesUrl = `${environment.apiUrl}/notifications/event-types`;

  constructor(private http: HttpClient) {}

  /** Get all notification templates */
  getTemplates(): Observable<TmsApp_Notifications_NotificationTemplate[]> {
    return this.http.get<TmsApp_Notifications_NotificationTemplate[]>(this.templatesUrl);
  }

  /** Get single notification template by ID */
  getTemplate(id: string): Observable<TmsApp_Notifications_NotificationTemplate> {
    return this.http.get<TmsApp_Notifications_NotificationTemplate>(`${this.templatesUrl}/${id}/`);
  }

  /** Get all notification event types */
  getEventTypes(): Observable<TmsApp_Notifications_NotificationEventType[]> {
    return this.http.get<TmsApp_Notifications_NotificationEventType[]>(this.eventTypesUrl);
  }

  /** Create new notification template */
  createTemplate(data: TmsApp_Notifications_NotificationTemplateFormValues): Observable<TmsApp_Notifications_NotificationTemplate> {
    return this.http.post<TmsApp_Notifications_NotificationTemplate>(this.templatesUrl, data);
  }

  /** Update notification template */
  updateTemplate(templateId: string, data: TmsApp_Notifications_NotificationTemplateFormValues): Observable<TmsApp_Notifications_NotificationTemplate> {
    return this.http.put<TmsApp_Notifications_NotificationTemplate>(`${this.templatesUrl}/${templateId}/`, data);
  }

  /** Delete notification template */
  deleteTemplate(templateId: string): Observable<void> {
    return this.http.delete<void>(`${this.templatesUrl}/${templateId}/`);
  }
}
