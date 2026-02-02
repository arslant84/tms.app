/**
 * Notification Models and Interfaces
 */

export interface NotificationTemplate {
  id: string;
  name: string;
  description?: string;
  notification_type: 'email' | 'system' | 'both';
  event_type: number;
  event_type_name?: string;
  subject: string;
  body: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface NotificationEventType {
  id: number;
  name: string;
  display_name?: string;
  description?: string;
  category: string;
  module: string;
  is_active: boolean;
  created_at?: string;
}

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
  additional_data?: Record<string, unknown>;
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
