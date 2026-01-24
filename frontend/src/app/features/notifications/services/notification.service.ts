import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, interval, Subscription } from 'rxjs';
import { tap, catchError, filter } from 'rxjs/operators';
import { of } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';

// Notification Interfaces
export interface UserNotification {
  id: number;
  user: number;
  event_type?: number;
  title: string;
  message: string;
  content_type?: number;
  object_id?: number;
  action_url?: string;
  action_text: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  is_read: boolean;
  read_at?: string;
  sent_via_email: boolean;
  email_sent_at?: string;
  sent_via_push: boolean;
  push_sent_at?: string;
  additional_data?: any;
  expires_at?: string;
  created_at: string;
}

export interface NotificationPreference {
  id?: number;
  user?: number;
  email_notifications_enabled: boolean;
  in_app_notifications_enabled: boolean;
  push_notifications_enabled: boolean;
  digest_frequency: 'instant' | 'hourly' | 'daily' | 'weekly';
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
}

export interface NotificationEventType {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  category: string;
  module: string;
  is_active: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private apiUrl = `${environment.apiUrl}/notifications`;
  private authService = inject(AuthService);
  private pollingSubscription?: Subscription;

  // Observable for unread count (used by header badge)
  private unreadCountSubject = new BehaviorSubject<number>(0);
  public unreadCount$ = this.unreadCountSubject.asObservable();

  // Observable for notifications list
  private notificationsSubject = new BehaviorSubject<UserNotification[]>([]);
  public notifications$ = this.notificationsSubject.asObservable();

  constructor(private http: HttpClient) {
    // SECURITY: Only poll when user is authenticated
    this.authService.currentUser$.pipe(
      filter(user => user !== null)
    ).subscribe(() => {
      this.startPolling();
    });

    // Stop polling when user logs out
    this.authService.currentUser$.pipe(
      filter(user => user === null)
    ).subscribe(() => {
      this.stopPolling();
    });
  }

  // Start polling for notifications (only when authenticated)
  private startPolling(): void {
    if (this.pollingSubscription) {
      return; // Already polling
    }
    this.pollingSubscription = interval(30000).subscribe(() => {
      this.refreshUnreadCount();
    });
  }

  // Stop polling (on logout)
  private stopPolling(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
      this.pollingSubscription = undefined;
      this.unreadCountSubject.next(0);
      this.notificationsSubject.next([]);
    }
  }

  // Get all notifications for current user
  getAllNotifications(filters?: {
    is_read?: boolean;
    priority?: string;
    page?: number;
    page_size?: number;
  }): Observable<any> {
    let params = new HttpParams();

    if (filters) {
      if (filters.is_read !== undefined) params = params.set('is_read', filters.is_read.toString());
      if (filters.priority) params = params.set('priority', filters.priority);
      if (filters.page) params = params.set('page', filters.page.toString());
      if (filters.page_size) params = params.set('page_size', filters.page_size.toString());
    }

    return this.http.get<any>(`${this.apiUrl}/`, { params }).pipe(
      tap((response) => {
        const notifications = Array.isArray(response) ? response : response.results || [];
        this.notificationsSubject.next(notifications);
      }),
      catchError((error) => {
        // Only log server errors to avoid console spam
        if (error.status >= 500) {
          console.error('❌ Server error fetching notifications:', error.status);
        }
        return of({ results: [] });
      })
    );
  }

  // Get unread count
  getUnreadCount(): Observable<{ count: number }> {
    return this.http.get<{ count: number }>(`${this.apiUrl}/unread_count/`).pipe(
      tap((response) => {
        this.unreadCountSubject.next(response.count);
      }),
      catchError((error) => {
        // Silently handle errors to avoid console spam from polling
        // Only log once if there's an actual server error
        if (error.status >= 500) {
          console.error('❌ Server error fetching unread count:', error.status);
        }
        return of({ count: 0 });
      })
    );
  }

  // Refresh unread count (used by polling)
  refreshUnreadCount(): void {
    this.getUnreadCount().subscribe();
  }

  // Get single notification
  getNotificationById(id: number): Observable<UserNotification> {
    return this.http.get<UserNotification>(`${this.apiUrl}/${id}/`);
  }

  // Mark notification as read
  markAsRead(id: number): Observable<UserNotification> {
    return this.http.post<UserNotification>(`${this.apiUrl}/${id}/mark_as_read/`, {}).pipe(
      tap(() => {
        this.refreshUnreadCount();
        this.refreshNotifications();
      })
    );
  }

  // Mark all as read
  markAllAsRead(): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/mark_all_as_read/`, {}).pipe(
      tap(() => {
        this.refreshUnreadCount();
        this.refreshNotifications();
      })
    );
  }

  // Delete notification
  deleteNotification(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`).pipe(
      tap(() => {
        this.refreshUnreadCount();
        this.refreshNotifications();
      })
    );
  }

  // Get user preferences
  getPreferences(): Observable<NotificationPreference> {
    return this.http.get<NotificationPreference>(`${this.apiUrl}/preferences/my_preferences/`);
  }

  // Update user preferences
  updatePreferences(data: Partial<NotificationPreference>): Observable<NotificationPreference> {
    return this.http.put<NotificationPreference>(`${this.apiUrl}/preferences/update_my_preferences/`, data);
  }

  // Get event types
  getEventTypes(): Observable<NotificationEventType[]> {
    return this.http.get<NotificationEventType[]>(`${this.apiUrl}/event-types/`);
  }

  // Get notification templates
  getNotificationTemplates(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/templates/`);
  }

  // Get user subscriptions
  getSubscriptions(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/subscriptions/my_subscriptions/`);
  }

  // Update subscription for an event type
  updateSubscription(eventTypeId: number | string, data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/subscriptions/${eventTypeId}/update_subscription/`, data);
  }

  // Helper method to refresh notifications
  refreshNotifications(): void {
    this.getAllNotifications({ page_size: 20 }).subscribe();
    this.refreshUnreadCount();
  }

  // Initialize service (call this on app init)
  // SECURITY: Only initialize if user is authenticated
  initialize(): void {
    if (this.authService.getCurrentUser()) {
      this.refreshUnreadCount();
      this.refreshNotifications();
    }
  }
}
