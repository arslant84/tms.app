import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  WorkflowStepNotificationConfig,
  EVENT_TYPE_OPTIONS,
  RecipientType,
} from '../../../../core/models/workflow.models';
import { NotificationTemplate } from '../../../../core/models/notification.models';
import { NotificationService } from '../../../notifications/services/notification.service';
import {
  TmsApp_Core_Services_RolesService,
  TmsApp_Roles_RoleWithPermissions,
} from '../../../../core/services/roles.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';

@Component({
  selector: 'app-step-notification-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './step-notification-config.component.html',
  styleUrls: ['./step-notification-config.component.scss'],
})
export class StepNotificationConfigComponent implements OnInit {
  @Input() stepNumber: number = 1;
  @Input() stepName: string = '';
  @Input() notificationConfigs: WorkflowStepNotificationConfig[] = [];
  @Output() notificationConfigsChange = new EventEmitter<WorkflowStepNotificationConfig[]>();

  availableTemplates: NotificationTemplate[] = [];
  availableRoles: TmsApp_Roles_RoleWithPermissions[] = [];
  eventTypeOptions = EVENT_TYPE_OPTIONS;
  recipientTypeOptions: { value: RecipientType; label: string; category?: string }[] = [];

  isExpanded: boolean = false;
  isAddingNew: boolean = false;
  currentConfig: WorkflowStepNotificationConfig | null = null;
  editingIndex: number = -1;

  // Form model
  form: Partial<WorkflowStepNotificationConfig> = this.getEmptyForm();

  constructor(
    private notificationService: NotificationService,
    private rolesService: TmsApp_Core_Services_RolesService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit(): void {
    this.loadNotificationTemplates();
    this.loadRolesAndBuildRecipientOptions();
  }

  loadNotificationTemplates(): void {
    this.notificationService.getNotificationTemplates().subscribe({
      next: templates => {
        this.availableTemplates = templates;
      },
      error: error => {
        console.error('Error loading notification templates:', error);
      },
    });
  }

  loadRolesAndBuildRecipientOptions(): void {
    this.rolesService.getRoles().subscribe({
      next: roles => {
        this.availableRoles = roles;
        this.buildRecipientTypeOptions();
      },
      error: error => {
        console.error('Error loading roles:', error);
        // Build with generic options only if roles fail to load
        this.buildRecipientTypeOptions();
      },
    });
  }

  buildRecipientTypeOptions(): void {
    // Generic/Workflow-specific recipient types
    const genericOptions: { value: RecipientType; label: string; category: string }[] = [
      { value: 'current_approver', label: 'Current Approver', category: 'Workflow' },
      { value: 'requester', label: 'Requester', category: 'Workflow' },
      { value: 'previous_approvers', label: 'Previous Approvers', category: 'Workflow' },
      { value: 'next_approvers', label: 'Next Approvers', category: 'Workflow' },
      { value: 'all_stakeholders', label: 'All Stakeholders', category: 'Workflow' },
    ];

    // Dynamic role-based recipient types
    const roleOptions: { value: RecipientType; label: string; category: string }[] =
      this.availableRoles.map(role => ({
        value: `role_${role.id}` as RecipientType,
        label: role.name,
        category: 'System Roles',
      }));

    // Custom emails option
    const customOption: { value: RecipientType; label: string; category: string }[] = [
      { value: 'custom_emails', label: 'Custom Email Addresses', category: 'Other' },
    ];

    // Combine all options
    this.recipientTypeOptions = [...genericOptions, ...roleOptions, ...customOption];
  }

  getEmptyForm(): Partial<WorkflowStepNotificationConfig> {
    return {
      event_type: 'assignment',
      notification_template: '',
      recipient_types: ['current_approver'],
      custom_recipients: [],
      is_active: true,
      send_email: true,
      send_system_notification: true,
      priority: 'normal',
    };
  }

  toggleExpanded(): void {
    this.isExpanded = !this.isExpanded;
  }

  startAddNew(): void {
    this.isAddingNew = true;
    this.editingIndex = -1;
    this.form = this.getEmptyForm();
  }

  editConfig(config: WorkflowStepNotificationConfig, index: number): void {
    this.isAddingNew = true;
    this.editingIndex = index;
    this.form = { ...config };
  }

  deleteConfig(index: number): void {
    this.confirmationService
      .confirmDelete('this notification configuration')
      .subscribe(confirmed => {
        if (confirmed) {
          this.notificationConfigs.splice(index, 1);
          this.emitChanges();
        }
      });
  }

  restoreDefaults(): void {
    this.confirmationService
      .confirm({
        title: 'Restore Defaults',
        message:
          'This will replace all current notification configurations with defaults. Continue?',
        confirmText: 'Restore',
        type: 'warning',
      })
      .subscribe(confirmed => {
        if (!confirmed) return;
        this.doRestoreDefaults();
      });
  }

  private doRestoreDefaults(): void {
    type EventType = 'assignment' | 'approval' | 'rejection' | 'reminder' | 'delegation';
    type Priority = 'low' | 'normal' | 'high' | 'urgent';

    // Default notification configs matching backend defaults
    const defaultConfigs: {
      event_type: EventType;
      template_name: string;
      recipient_types: RecipientType[];
      priority: Priority;
    }[] = [
      {
        event_type: 'assignment',
        template_name: 'approval_required',
        recipient_types: ['current_approver'],
        priority: 'high',
      },
      {
        event_type: 'approval',
        template_name: 'workflow_completed',
        recipient_types: ['requester'],
        priority: 'normal',
      },
      {
        event_type: 'rejection',
        template_name: 'workflow_rejected',
        recipient_types: ['requester'],
        priority: 'urgent',
      },
      {
        event_type: 'delegation',
        template_name: 'delegation_confirmed',
        recipient_types: ['current_approver'],
        priority: 'high',
      },
    ];

    // Find template IDs by name
    const newConfigs: WorkflowStepNotificationConfig[] = [];
    for (const defaultConfig of defaultConfigs) {
      const template = this.availableTemplates.find(t => t.name === defaultConfig.template_name);
      if (template) {
        newConfigs.push({
          event_type: defaultConfig.event_type,
          notification_template: template.id,
          recipient_types: defaultConfig.recipient_types,
          custom_recipients: [],
          is_active: true,
          send_email: true,
          send_system_notification: true,
          priority: defaultConfig.priority,
        });
      }
    }

    this.notificationConfigs.length = 0;
    this.notificationConfigs.push(...newConfigs);
    this.emitChanges();
  }

  cancelEdit(): void {
    this.isAddingNew = false;
    this.editingIndex = -1;
    this.form = this.getEmptyForm();
  }

  saveConfig(): void {
    // Validate form
    if (!this.form.notification_template || this.form.recipient_types?.length === 0) {
      this.toastService.warning(
        'Please select a notification template and at least one recipient type.'
      );
      return;
    }

    // Check if custom emails is selected but no emails provided
    if (
      this.form.recipient_types?.includes('custom_emails') &&
      this.form.custom_recipients?.length === 0
    ) {
      this.toastService.warning('Please provide at least one custom email address.');
      return;
    }

    const config: WorkflowStepNotificationConfig = {
      event_type: this.form.event_type!,
      notification_template: this.form.notification_template!,
      recipient_types: this.form.recipient_types!,
      custom_recipients: this.form.custom_recipients || [],
      is_active: this.form.is_active ?? true,
      send_email: this.form.send_email ?? true,
      send_system_notification: this.form.send_system_notification ?? true,
      priority: this.form.priority || 'normal',
    };

    if (this.editingIndex >= 0) {
      // Update existing
      this.notificationConfigs[this.editingIndex] = config;
    } else {
      // Add new
      this.notificationConfigs.push(config);
    }

    this.emitChanges();
    this.cancelEdit();
  }

  toggleRecipientType(type: RecipientType): void {
    if (!this.form.recipient_types) {
      this.form.recipient_types = [];
    }

    const index = this.form.recipient_types.indexOf(type);
    if (index >= 0) {
      this.form.recipient_types.splice(index, 1);
    } else {
      this.form.recipient_types.push(type);
    }
  }

  isRecipientTypeSelected(type: RecipientType): boolean {
    return this.form.recipient_types?.includes(type) || false;
  }

  addCustomEmail(): void {
    const email = prompt('Enter email address:');
    if (email && this.validateEmail(email)) {
      if (!this.form.custom_recipients) {
        this.form.custom_recipients = [];
      }
      this.form.custom_recipients.push(email);
    } else if (email) {
      this.toastService.error('Invalid email address');
    }
  }

  removeCustomEmail(index: number): void {
    this.form.custom_recipients?.splice(index, 1);
  }

  validateEmail(email: string): boolean {
    const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return re.test(email);
  }

  getRecipientsByCategory(
    category: string
  ): { value: RecipientType; label: string; category?: string }[] {
    return this.recipientTypeOptions.filter(option => option.category === category);
  }

  getTemplateName(templateId: string): string {
    const template = this.availableTemplates.find(t => t.id === templateId);
    return template?.name || 'Unknown Template';
  }

  getEventTypeLabel(eventType: string): string {
    const option = EVENT_TYPE_OPTIONS.find(o => o.value === eventType);
    return option?.label || eventType;
  }

  getRecipientTypeLabels(types: RecipientType[]): string {
    return types
      .map(type => {
        const option = this.recipientTypeOptions.find(o => o.value === type);
        return option?.label || type;
      })
      .join(', ');
  }

  getConfigCount(): number {
    return this.notificationConfigs.length;
  }

  private emitChanges(): void {
    this.notificationConfigsChange.emit(this.notificationConfigs);
  }
}
