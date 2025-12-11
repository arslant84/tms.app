import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { NotificationService, NotificationPreference, NotificationEventType } from '../../services/notification.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-notification-preferences',
  standalone: true,
  imports: [CommonModule, RouterModule, ReactiveFormsModule],
  templateUrl: './notification-preferences.component.html',
  styleUrls: ['./notification-preferences.component.scss']
})
export class NotificationPreferencesComponent implements OnInit {
  preferencesForm!: FormGroup;
  eventTypes: NotificationEventType[] = [];
  subscriptions: any[] = [];
  isLoading = false;
  isSaving = false;

  constructor(
    private fb: FormBuilder,
    private notificationService: NotificationService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.initForm();
    this.loadPreferences();
    this.loadEventTypes();
    this.loadSubscriptions();
  }

  initForm(): void {
    this.preferencesForm = this.fb.group({
      email_notifications_enabled: [true],
      in_app_notifications_enabled: [true],
      push_notifications_enabled: [false],
      digest_frequency: ['instant', Validators.required],
      quiet_hours_enabled: [false],
      quiet_hours_start: ['22:00'],
      quiet_hours_end: ['08:00']
    });
  }

  loadPreferences(): void {
    this.isLoading = true;
    this.notificationService.getPreferences().subscribe({
      next: (preferences) => {
        this.preferencesForm.patchValue(preferences);
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading preferences:', err);
        this.toastService.error('Failed to load notification preferences');
        this.isLoading = false;
      }
    });
  }

  loadEventTypes(): void {
    this.notificationService.getEventTypes().subscribe({
      next: (eventTypes) => {
        this.eventTypes = eventTypes;
      },
      error: (err) => {
        console.error('Error loading event types:', err);
      }
    });
  }

  loadSubscriptions(): void {
    this.notificationService.getSubscriptions().subscribe({
      next: (subscriptions) => {
        this.subscriptions = subscriptions;
      },
      error: (err) => {
        console.error('Error loading subscriptions:', err);
      }
    });
  }

  onSubmit(): void {
    if (this.preferencesForm.valid) {
      this.isSaving = true;
      const preferences = this.preferencesForm.value;

      this.notificationService.updatePreferences(preferences).subscribe({
        next: (response) => {
          this.toastService.success('Notification preferences updated successfully');
          this.isSaving = false;
        },
        error: (err) => {
          console.error('Error updating preferences:', err);
          this.toastService.error('Failed to update notification preferences');
          this.isSaving = false;
        }
      });
    }
  }

  getSubscriptionValue(eventTypeId: number): any {
    return this.subscriptions.find(sub => sub.event_type === eventTypeId);
  }

  isSubscribed(eventTypeId: number): boolean {
    const subscription = this.getSubscriptionValue(eventTypeId);
    return subscription ? subscription.is_subscribed : false;
  }

  toggleSubscription(eventType: NotificationEventType): void {
    const subscription = this.getSubscriptionValue(eventType.id);
    const newValue = subscription ? !subscription.is_subscribed : true;

    const data = {
      event_type: eventType.id,
      is_subscribed: newValue,
      email_enabled: newValue,
      in_app_enabled: newValue,
      push_enabled: false
    };

    this.notificationService.updateSubscription(eventType.id, data).subscribe({
      next: (response) => {
        this.loadSubscriptions();
        this.toastService.success(
          newValue
            ? `Subscribed to ${eventType.display_name}`
            : `Unsubscribed from ${eventType.display_name}`
        );
      },
      error: (err) => {
        console.error('Error updating subscription:', err);
        this.toastService.error('Failed to update subscription');
      }
    });
  }

  getEventTypesByCategory(category: string): NotificationEventType[] {
    return this.eventTypes.filter(et => et.category === category);
  }

  get uniqueCategories(): string[] {
    return [...new Set(this.eventTypes.map(et => et.category))];
  }

  cancel(): void {
    this.loadPreferences();
  }
}
