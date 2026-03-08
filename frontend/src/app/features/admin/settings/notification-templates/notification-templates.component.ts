import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TmsApp_Core_Services_NotificationsService, TmsApp_Notifications_NotificationTemplate, TmsApp_Notifications_NotificationEventType, TmsApp_Notifications_NotificationTemplateFormValues } from '../../../../core/services/notifications.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'tmsapp-admin-systemsettings-notification-templates',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './notification-templates.component.html',
  styleUrls: ['./notification-templates.component.scss']
})
export class TmsApp_Admin_SystemSettings_NotificationTemplatesComponent implements OnInit {
  isLoading = true;
  isSaving = false;
  templates: TmsApp_Notifications_NotificationTemplate[] = [];
  eventTypes: TmsApp_Notifications_NotificationEventType[] = [];

  isModalOpen = false;
  currentTemplate: TmsApp_Notifications_NotificationTemplate | null = null;
  selectedEventType: TmsApp_Notifications_NotificationEventType | null = null;

  form: TmsApp_Notifications_NotificationTemplateFormValues = {
    name: '',
    description: '',
    subject: '',
    body: '',
    event_type: null,
    notification_type: 'email',
    recipient_type: 'approver',
    variables_available: [],
    is_active: true
  };

  constructor(
    private notificationsService: TmsApp_Core_Services_NotificationsService,
    private toast: ToastService,
    private confirmationService: ConfirmationService,
    public dateUtils: DateUtilsService
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading = true;
    Promise.all([
      this.notificationsService.getTemplates().toPromise(),
      this.notificationsService.getEventTypes().toPromise()
    ])
      .then(([templates, eventTypes]) => {
        this.templates = templates || [];
        this.eventTypes = eventTypes || [];
      })
      .catch((error) => {
        console.error('Failed to load data:', error);
        this.toast.error('Failed to load notifications data');
      })
      .finally(() => {
        this.isLoading = false;
      });
  }

  openCreateModal(): void {
    this.currentTemplate = null;
    this.selectedEventType = null;
    this.form = {
      name: '',
      description: '',
      subject: '',
      body: '',
      event_type: null,
      notification_type: 'email',
      recipient_type: 'approver',
      variables_available: [],
      is_active: true
    };
    this.isModalOpen = true;
  }

  async openEditModal(template: TmsApp_Notifications_NotificationTemplate): Promise<void> {
    try {
      // Fetch full template data when editing
      const fullTemplate = await this.notificationsService.getTemplate(template.id).toPromise();
      if (fullTemplate) {
        this.currentTemplate = fullTemplate;
        this.form = {
          name: fullTemplate.name,
          description: fullTemplate.description || '',
          subject: fullTemplate.subject,
          body: fullTemplate.body,
          event_type: fullTemplate.event_type || null,
          notification_type: fullTemplate.notification_type,
          recipient_type: fullTemplate.recipient_type,
          variables_available: fullTemplate.variables_available || [],
          is_active: fullTemplate.is_active
        };

        // Set selected event type for display
        if (fullTemplate.event_type) {
          this.selectedEventType = this.eventTypes.find(et => et.id === fullTemplate.event_type) || null;
        }

        this.isModalOpen = true;
      }
    } catch (error) {
      console.error('Failed to fetch template:', error);
      this.toast.error('Failed to fetch template details for editing');
    }
  }

  closeModal(): void {
    this.isModalOpen = false;
    this.currentTemplate = null;
    this.selectedEventType = null;
  }

  onEventTypeChange(eventTypeId: string): void {
    this.selectedEventType = this.eventTypes.find(et => et.id === eventTypeId) || null;
  }

  submitForm(): void {
    if (!this.isFormValid()) {
      this.toast.error('Please fill in all required fields');
      return;
    }

    this.isSaving = true;
    const op = this.currentTemplate
      ? this.notificationsService.updateTemplate(this.currentTemplate.id, this.form)
      : this.notificationsService.createTemplate(this.form);

    op.subscribe({
      next: () => {
        this.toast.success(this.currentTemplate ? 'Template updated successfully' : 'Template created successfully');
        this.closeModal();
        this.loadData();
      },
      error: (error) => {
        console.error('Failed to save template:', error);
        this.toast.error('Failed to save template');
      },
      complete: () => {
        this.isSaving = false;
      }
    });
  }

  deleteTemplate(template: TmsApp_Notifications_NotificationTemplate): void {
    this.confirmationService.confirmDelete('this template').subscribe(confirmed => {
      if (!confirmed) return;
      this.executeDeleteTemplate(template);
    });
  }

  private executeDeleteTemplate(template: TmsApp_Notifications_NotificationTemplate): void {
    this.notificationsService.deleteTemplate(template.id).subscribe({
      next: () => {
        this.toast.success('Template deleted successfully');
        this.templates = this.templates.filter(t => t.id !== template.id);
      },
      error: (error) => {
        console.error('Failed to delete template:', error);
        this.toast.error('Failed to delete template');
      }
    });
  }

  isFormValid(): boolean {
    return !!(this.form.name && this.form.subject && this.form.body &&
              this.form.notification_type && this.form.event_type);
  }

  getAvailableVariables(): string[] {
    const generalVars = ['userName', 'date', 'requestId'];
    const eventSpecificVars: Record<string, string[]> = {
      'trf': ['requestorName', 'approverName', 'comments', 'entityType'],
      'visa': ['requestorName', 'approverName', 'comments', 'entityType'],
      'claims': ['requestorName', 'approverName', 'comments', 'entityType'],
      'transport': ['requestorName', 'approverName', 'comments', 'entityType'],
      'accommodation': ['requestorName', 'approverName', 'comments', 'entityType'],
    };

    if (this.selectedEventType) {
      const moduleVars = eventSpecificVars[this.selectedEventType.module] || [];
      return [...generalVars, ...moduleVars];
    }

    return generalVars;
  }

}
