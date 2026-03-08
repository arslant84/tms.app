import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { NotificationService, NotificationPreference, NotificationEventType } from '../../services/notification.service';
import { ToastService } from '../../../../core/services/toast.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

interface Subscription {
  id?: number;
  event_type: string | number;
  event_type_detail?: any;
  receive_email: boolean;
  receive_in_app: boolean;
  receive_push?: boolean;
  is_active: boolean;
}

@Component({
  selector: 'app-notification-preferences',
  standalone: true,
  imports: [CommonModule, RouterModule, ReactiveFormsModule, LoadingSpinnerComponent],
  templateUrl: './notification-preferences.component.html',
  styleUrls: ['./notification-preferences.component.scss']
})
export class NotificationPreferencesComponent implements OnInit {
  preferencesForm!: FormGroup;
  workflowEventTypes: NotificationEventType[] = [];
  subscriptions: Subscription[] = [];
  isLoading = false;
  isSaving = false;

  constructor(
    private fb: FormBuilder,
    private notificationService: NotificationService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.initForm();
    this.loadData();
  }

  initForm(): void {
    this.preferencesForm = this.fb.group({
      email_notifications_enabled: [true],
      in_app_notifications_enabled: [true]
    });
  }

  loadData(): void {
    this.isLoading = true;

    // Load preferences
    this.notificationService.getPreferences().subscribe({
      next: (preferences) => {
        this.preferencesForm.patchValue({
          email_notifications_enabled: preferences.email_notifications_enabled,
          in_app_notifications_enabled: preferences.in_app_notifications_enabled
        });
      },
      error: (err) => {
        console.error('Error loading preferences:', err);
      }
    });

    // Load event types
    this.notificationService.getEventTypes().subscribe({
      next: (eventTypes) => {
        // Filter to only show active workflow-related event types
        this.workflowEventTypes = eventTypes.filter(et => et.is_active);
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading event types:', err);
        this.isLoading = false;
      }
    });

    // Load subscriptions
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
        next: () => {
          this.toastService.success('Notification preferences saved successfully');
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

  getEventTypesByCategory(category: string): NotificationEventType[] {
    return this.workflowEventTypes.filter(et => et.category === category);
  }

  getSubscriptionForEvent(eventTypeId: number | string): Subscription | undefined {
    // Handle both UUID strings and numeric IDs
    return this.subscriptions.find(sub =>
      String(sub.event_type) === String(eventTypeId) ||
      sub.event_type_detail?.id === eventTypeId
    );
  }

  isSubscribedEmail(eventTypeId: number): boolean {
    const subscription = this.getSubscriptionForEvent(eventTypeId);
    // Default to true if no subscription exists (opt-out model)
    return subscription ? subscription.receive_email : true;
  }

  isSubscribedInApp(eventTypeId: number): boolean {
    const subscription = this.getSubscriptionForEvent(eventTypeId);
    // Default to true if no subscription exists (opt-out model)
    return subscription ? subscription.receive_in_app : true;
  }

  toggleEmailSubscription(eventType: NotificationEventType): void {
    const currentValue = this.isSubscribedEmail(eventType.id);
    this.updateSubscription(eventType, !currentValue, this.isSubscribedInApp(eventType.id));
  }

  toggleInAppSubscription(eventType: NotificationEventType): void {
    const currentValue = this.isSubscribedInApp(eventType.id);
    this.updateSubscription(eventType, this.isSubscribedEmail(eventType.id), !currentValue);
  }

  private updateSubscription(eventType: NotificationEventType, receiveEmail: boolean, receiveInApp: boolean): void {
    const data = {
      event_type: eventType.id,
      receive_email: receiveEmail,
      receive_in_app: receiveInApp,
      is_active: true
    };

    this.notificationService.updateSubscription(eventType.id, data).subscribe({
      next: () => {
        // Reload subscriptions to get updated state
        this.notificationService.getSubscriptions().subscribe({
          next: (subscriptions) => {
            this.subscriptions = subscriptions;
          }
        });

        const action = receiveEmail || receiveInApp ? 'Updated' : 'Disabled';
        this.toastService.success(`${action} subscription for ${this.formatEventName(eventType.name)}`);
      },
      error: (err) => {
        console.error('Error updating subscription:', err);
        this.toastService.error('Failed to update subscription');
      }
    });
  }

  formatEventName(name: string): string {
    // Convert WORKFLOW_STARTED to "Workflow Started"
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  }

  cancel(): void {
    this.loadData();
  }
}
