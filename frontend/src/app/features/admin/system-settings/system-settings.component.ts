import { Component, OnInit, DoCheck } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TmsApp_Admin_SystemSettings_RoleManagementComponent } from './role-management/role-management.component';
import { TmsApp_Admin_SystemSettings_WorkflowConfigurationComponent } from './workflow-configuration/workflow-configuration.component';
import { ToastService } from '../../../core/services/toast.service';
import { SettingsService, ApplicationSetting, SettingUpdate } from '../../../core/services/settings.service';

interface SettingsForm {
  application_name: string;
  maintenance_mode: boolean;
  support_email: string;
  default_currency: string;
  timezone: string;
  enable_email_notifications: boolean;
  session_timeout_minutes: number;
  max_file_upload_size: number;
}

@Component({
  selector: 'app-system-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, TmsApp_Admin_SystemSettings_RoleManagementComponent, TmsApp_Admin_SystemSettings_WorkflowConfigurationComponent],
  templateUrl: './system-settings.component.html',
  styleUrls: ['./system-settings.component.scss']
})
export class SystemSettingsComponent implements OnInit, DoCheck {
  isLoading = true;
  isSaving = false;
  hasChanges = false;

  settings: ApplicationSetting[] = [];
  formData: SettingsForm = {
    application_name: '',
    maintenance_mode: false,
    support_email: '',
    default_currency: '',
    timezone: '',
    enable_email_notifications: true,
    session_timeout_minutes: 480,
    max_file_upload_size: 10485760
  };
  originalData: SettingsForm = { ...this.formData };

  constructor(
    private toastService: ToastService,
    private settingsService: SettingsService
  ) {}

  ngOnInit(): void {
    this.loadSettings();
  }

  ngDoCheck(): void {
    this.checkChanges();
  }

  checkChanges(): void {
    this.hasChanges = Object.keys(this.formData).some(key => {
      const typedKey = key as keyof SettingsForm;
      return this.formData[typedKey] !== this.originalData[typedKey];
    });
  }

  loadSettings(): void {
    this.isLoading = true;
    this.settingsService.getAllSettings().subscribe({
      next: (response) => {
        // Handle both paginated and non-paginated responses
        const settingsData = Array.isArray(response) ? response : (response as any).results || [];

        if (Array.isArray(settingsData)) {
          this.settings = settingsData;
          const formDataFromSettings = settingsData.reduce((acc, setting) => {
            if (Object.prototype.hasOwnProperty.call(this.formData, setting.setting_key)) {
              // Use typed 'value' field if available from backend's get_value() method
              // Otherwise fallback to setting_value with type conversion
              let typedValue: any;

              if (setting.value !== undefined) {
                // Backend provides typed value through serializer
                typedValue = setting.value;
              } else {
                // Fallback: manually convert setting_value based on setting_type
                const rawValue = setting.setting_value;

                if (setting.setting_type === 'boolean') {
                  typedValue = rawValue === 'true' || rawValue === true;
                } else if (setting.setting_type === 'number') {
                  typedValue = parseFloat(rawValue);
                } else if (setting.setting_type === 'json') {
                  try {
                    typedValue = typeof rawValue === 'string' ? JSON.parse(rawValue) : rawValue;
                  } catch (e) {
                    console.error('Failed to parse JSON setting:', setting.setting_key, e);
                    typedValue = rawValue;
                  }
                } else {
                  typedValue = rawValue;
                }
              }

              (acc as any)[setting.setting_key] = typedValue;
            }
            return acc;
          }, {} as SettingsForm);

          this.formData = { ...this.formData, ...formDataFromSettings };
          this.originalData = { ...this.formData };
          console.log('Loaded application settings:', this.formData);
        } else {
          console.error('Error: settingsData is not an array', response);
          this.toastService.error('Failed to load application settings: Invalid data format');
        }
        this.isLoading = false;
        this.checkChanges(); // Initial check
      },
      error: (err) => {
        console.error('Error loading settings:', err);
        this.toastService.error('Failed to load application settings');
        this.isLoading = false;
      }
    });
  }

  handleSaveSettings(): void {
    this.isSaving = true;

    const updates: SettingUpdate[] = [];
    Object.keys(this.formData).forEach(key => {
      const fieldKey = key as keyof SettingsForm;
      if (this.formData[fieldKey] !== this.originalData[fieldKey]) {
        const setting = this.settings.find(s => s.setting_key === key);
        if (setting) {
          updates.push({
            setting_key: key,
            value: this.formData[fieldKey],
          });
        }
      }
    });

    if (updates.length === 0) {
      this.toastService.info('No changes to save');
      this.isSaving = false;
      return;
    }

    this.settingsService.bulkUpdateSettings(updates).subscribe({
      next: () => {
        this.toastService.success(`${updates.length} setting${updates.length > 1 ? 's' : ''} updated successfully`);
        this.loadSettings(); // Reload to sync state
      },
      error: (err) => {
        console.error('Error saving settings:', err);
        this.toastService.error('Failed to save application settings');
      },
      complete: () => {
        this.isSaving = false;
      }
    });
  }

  handleReset(): void {
    this.formData = { ...this.originalData };
  }
}
