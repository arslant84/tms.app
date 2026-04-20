import { CommonModule } from '@angular/common';
import { Component, type DoCheck, type OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AppSettingsService } from '../../../core/services/app-settings.service';
import { SettingsService, type ApplicationSetting, type SettingUpdate } from '../../../core/services/settings.service';
import { ToastService } from '../../../core/services/toast.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { DepartmentManagementComponent } from './department-management/department-management.component';
import { EnhancedWorkflowConfigComponent } from './enhanced-workflow-config/enhanced-workflow-config.component';
import { TmsApp_Admin_SystemSettings_RoleManagementComponent } from './role-management/role-management.component';

interface SettingsForm {
  application_name: string;
  maintenance_mode: boolean;
  support_email: string;
  default_currency: string;
  enable_email_notifications: boolean;
  session_timeout_minutes: number;
  max_file_upload_size: number;
}

@Component({
  selector: 'app-system-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, TmsApp_Admin_SystemSettings_RoleManagementComponent, DepartmentManagementComponent, EnhancedWorkflowConfigComponent, LoadingSpinnerComponent],
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
    enable_email_notifications: true,
    session_timeout_minutes: 480,
    max_file_upload_size: 10485760
  };
  originalData: SettingsForm = { ...this.formData };

  private toastService = inject(ToastService);
  private settingsService = inject(SettingsService);
  private appSettingsService = inject(AppSettingsService);

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
        const settingsData: ApplicationSetting[] = Array.isArray(response)
          ? response
          : ((response as { results?: ApplicationSetting[] }).results ?? []);

        if (Array.isArray(settingsData)) {
          this.settings = settingsData;
          const formDataFromSettings = settingsData.reduce((acc, setting) => {
            if (Object.hasOwn(this.formData, setting.setting_key)) {
              let typedValue: string | boolean | number;

              if (setting.value !== undefined) {
                typedValue = setting.value as string | boolean | number;
              } else {
                const rawValue = setting.setting_value;

                if (setting.setting_type === 'boolean') {
                  typedValue = rawValue === 'true';
                } else if (setting.setting_type === 'number') {
                  typedValue = parseFloat(rawValue as string);
                } else if (setting.setting_type === 'json') {
                  try {
                    typedValue = typeof rawValue === 'string' ? JSON.parse(rawValue) : rawValue;
                  } catch (e) {
                    console.error('Failed to parse JSON setting:', setting.setting_key, e);
                    typedValue = rawValue as string;
                  }
                } else {
                  typedValue = rawValue as string;
                }
              }

              (acc as unknown as Record<string, string | boolean | number>)[setting.setting_key] = typedValue;
            }
            return acc;
          }, {} as SettingsForm);

          this.formData = { ...this.formData, ...formDataFromSettings };
          this.originalData = { ...this.formData };
        } else {
          console.error('Error: settingsData is not an array', response);
          this.toastService.error('Failed to load application settings: Invalid data format');
        }
        this.isLoading = false;
        this.checkChanges();
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
        this.loadSettings();
        this.appSettingsService.refresh();
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
