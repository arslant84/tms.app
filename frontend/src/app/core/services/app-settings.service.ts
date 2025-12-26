import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { SettingsService, ApplicationSetting } from './settings.service';

export interface AppSettings {
  application_name: string;
  maintenance_mode: boolean;
  support_email: string;
  default_currency: string;
  enable_email_notifications: boolean;
  session_timeout_minutes: number;
  max_file_upload_size: number;
}

@Injectable({
  providedIn: 'root'
})
export class AppSettingsService {
  private settingsSubject = new BehaviorSubject<AppSettings>({
    application_name: 'TMS',
    maintenance_mode: false,
    support_email: 'support@example.com',
    default_currency: 'USD',
    enable_email_notifications: true,
    session_timeout_minutes: 480,
    max_file_upload_size: 10485760
  });

  public settings$ = this.settingsSubject.asObservable();

  constructor(private settingsService: SettingsService) {
    this.loadSettings();
  }

  /**
   * Load settings from backend and update the BehaviorSubject
   */
  loadSettings(): void {
    this.settingsService.getAllSettings().subscribe({
      next: (response) => {
        const settingsData = Array.isArray(response) ? response : (response as any).results || [];

        if (Array.isArray(settingsData)) {
          const currentSettings = this.settingsSubject.value;
          const updatedSettings = settingsData.reduce((acc, setting: ApplicationSetting) => {
            if (Object.prototype.hasOwnProperty.call(currentSettings, setting.setting_key)) {
              let typedValue: any;

              if (setting.value !== undefined) {
                typedValue = setting.value;
              } else {
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
          }, {} as AppSettings);

          // Merge with current settings and emit
          this.settingsSubject.next({ ...currentSettings, ...updatedSettings });
          console.log('App settings loaded:', this.settingsSubject.value);
        }
      },
      error: (err) => {
        console.error('Error loading app settings:', err);
      }
    });
  }

  /**
   * Get current settings synchronously
   */
  getSettings(): AppSettings {
    return this.settingsSubject.value;
  }

  /**
   * Get a specific setting value
   */
  getSetting<K extends keyof AppSettings>(key: K): AppSettings[K] {
    return this.settingsSubject.value[key];
  }

  /**
   * Get the default currency
   */
  getDefaultCurrency(): string {
    return this.settingsSubject.value.default_currency || 'USD';
  }

  /**
   * Observable for default currency changes
   */
  get defaultCurrency$(): Observable<string> {
    return new Observable(observer => {
      this.settings$.subscribe(settings => {
        observer.next(settings.default_currency);
      });
    });
  }

  /**
   * Refresh settings from backend
   */
  refresh(): void {
    this.loadSettings();
  }
}
