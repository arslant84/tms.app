import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ToastService } from '../../../core/services/toast.service';
import { SettingsService, SettingUpdate } from '../../../core/services/settings.service';

@Component({
  selector: 'app-system-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './system-settings.component.html',
  styleUrls: ['./system-settings.component.scss']
})
export class SystemSettingsComponent implements OnInit {
  loading = false;
  loadingSettings = true;

  // General Settings
  siteName = 'Travel Management System';
  siteDescription = 'Internal travel and expense management platform';
  supportEmail = 'support@tms.com';
  defaultCurrency = 'USD';
  timezone = 'UTC';
  sessionTimeout = 30;
  maxFileUploadSize = 10;

  // Email Settings
  emailEnabled = true;
  smtpHost = 'smtp.gmail.com';
  smtpPort = 587;
  smtpUsername = '';
  smtpPassword = '';
  smtpUseTLS = true;
  defaultFromEmail = 'noreply@tms.com';

  // Notification Settings
  notificationEnabled = true;
  emailNotifications = true;

  // Approval Settings
  autoApprovalThreshold = 1000;
  requireManagerApproval = true;
  requireFinanceApproval = true;

  // System Maintenance
  maintenanceMode = false;
  maintenanceMessage = 'System is under maintenance. Please check back later.';

  activeTab = 'general';

  constructor(
    private toastService: ToastService,
    private settingsService: SettingsService
  ) {}

  ngOnInit(): void {
    this.loadSettings();
  }

  loadSettings(): void {
    this.loadingSettings = true;

    this.settingsService.getSettingsAsObject().subscribe({
      next: (settings) => {
        // General Settings
        this.siteName = settings['app_name'] || this.siteName;
        this.siteDescription = settings['app_description'] || this.siteDescription;
        this.supportEmail = settings['support_email'] || this.supportEmail;
        this.defaultCurrency = settings['default_currency'] || this.defaultCurrency;
        this.timezone = settings['timezone'] || this.timezone;
        this.sessionTimeout = settings['session_timeout'] || this.sessionTimeout;
        this.maxFileUploadSize = settings['max_file_upload_size'] || this.maxFileUploadSize;

        // Email Settings
        this.emailEnabled = settings['email_enabled'] ?? this.emailEnabled;
        this.smtpHost = settings['smtp_host'] || this.smtpHost;
        this.smtpPort = settings['smtp_port'] || this.smtpPort;
        this.smtpUsername = settings['smtp_username'] || this.smtpUsername;
        this.smtpPassword = settings['smtp_password'] || this.smtpPassword;
        this.smtpUseTLS = settings['smtp_use_tls'] ?? this.smtpUseTLS;
        this.defaultFromEmail = settings['default_from_email'] || this.defaultFromEmail;

        // Notification Settings
        this.notificationEnabled = settings['notifications_enabled'] ?? this.notificationEnabled;
        this.emailNotifications = settings['email_notifications_enabled'] ?? this.emailNotifications;

        // Approval Settings
        this.autoApprovalThreshold = settings['auto_approval_threshold'] || this.autoApprovalThreshold;
        this.requireManagerApproval = settings['require_manager_approval'] ?? this.requireManagerApproval;
        this.requireFinanceApproval = settings['require_finance_approval'] ?? this.requireFinanceApproval;

        // System Maintenance
        this.maintenanceMode = settings['maintenance_mode'] ?? this.maintenanceMode;
        this.maintenanceMessage = settings['maintenance_message'] || this.maintenanceMessage;

        this.loadingSettings = false;
      },
      error: (err) => {
        console.error('Failed to load settings:', err);
        this.toastService.error('Failed to load system settings');
        this.loadingSettings = false;
      }
    });
  }

  saveSettings(): void {
    this.loading = true;

    const settingsToUpdate: SettingUpdate[] = [
      // General Settings
      { setting_key: 'app_name', value: this.siteName },
      { setting_key: 'app_description', value: this.siteDescription },
      { setting_key: 'support_email', value: this.supportEmail },
      { setting_key: 'default_currency', value: this.defaultCurrency },
      { setting_key: 'timezone', value: this.timezone },
      { setting_key: 'session_timeout', value: this.sessionTimeout },
      { setting_key: 'max_file_upload_size', value: this.maxFileUploadSize },

      // Email Settings
      { setting_key: 'email_enabled', value: this.emailEnabled },
      { setting_key: 'smtp_host', value: this.smtpHost },
      { setting_key: 'smtp_port', value: this.smtpPort },
      { setting_key: 'smtp_username', value: this.smtpUsername },
      { setting_key: 'smtp_password', value: this.smtpPassword },
      { setting_key: 'smtp_use_tls', value: this.smtpUseTLS },
      { setting_key: 'default_from_email', value: this.defaultFromEmail },

      // Notification Settings
      { setting_key: 'notifications_enabled', value: this.notificationEnabled },
      { setting_key: 'email_notifications_enabled', value: this.emailNotifications },

      // Approval Settings
      { setting_key: 'auto_approval_threshold', value: this.autoApprovalThreshold },
      { setting_key: 'require_manager_approval', value: this.requireManagerApproval },
      { setting_key: 'require_finance_approval', value: this.requireFinanceApproval },

      // System Maintenance
      { setting_key: 'maintenance_mode', value: this.maintenanceMode },
      { setting_key: 'maintenance_message', value: this.maintenanceMessage }
    ];

    this.settingsService.bulkUpdateSettings(settingsToUpdate).subscribe({
      next: (response) => {
        this.loading = false;

        if (response.errors && response.errors.length > 0) {
          console.error('Some settings failed to update:', response.errors);
          this.toastService.error(`Settings saved with ${response.errors.length} error(s)`);
        } else {
          this.toastService.success('System settings saved successfully');
        }
      },
      error: (err) => {
        console.error('Failed to save settings:', err);
        this.toastService.error('Failed to save system settings');
        this.loading = false;
      }
    });
  }

  resetSettings(): void {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
      // Reset to defaults
      this.siteName = 'Travel Management System';
      this.siteDescription = 'Internal travel and expense management platform';
      this.supportEmail = 'support@tms.com';
      this.defaultCurrency = 'USD';
      this.timezone = 'UTC';
      this.sessionTimeout = 30;
      this.maxFileUploadSize = 10;
      this.emailEnabled = true;
      this.smtpHost = 'smtp.gmail.com';
      this.smtpPort = 587;
      this.smtpUseTLS = true;
      this.notificationEnabled = true;
      this.emailNotifications = true;
      this.autoApprovalThreshold = 1000;
      this.requireManagerApproval = true;
      this.requireFinanceApproval = true;
      this.maintenanceMode = false;

      this.toastService.success('Settings reset to defaults');
    }
  }

  setActiveTab(tab: string): void {
    this.activeTab = tab;
  }
}
