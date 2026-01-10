import { Injectable, inject } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { SettingsService, ApplicationSetting } from './settings.service';
import { AuthService } from './auth.service';
import { filter } from 'rxjs/operators';

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
  private authService = inject(AuthService);

  constructor(private settingsService: SettingsService) {
    // SECURITY: Load public settings first (no auth required)
    this.loadPublicSettings();

    // Load full settings when user authenticates
    this.authService.currentUser$.pipe(
      filter(user => user !== null)
    ).subscribe(() => {
      this.loadSettings();
    });
  }

  /**
   * Load public settings (no authentication required)
   */
  private loadPublicSettings(): void {
    this.settingsService.getPublicSettings().subscribe({
      next: (response) => {
        this.processSettings(response);
      },
      error: (err) => {
        console.error('Error loading public settings:', err);
      }
    });
  }

  /**
   * Load all settings from backend (requires authentication)
   */
  loadSettings(): void {
    // Only load if authenticated
    if (!this.authService.getCurrentUser()) {
      return;
    }

    this.settingsService.getAllSettings().subscribe({
      next: (response) => {
        this.processSettings(response);
      },
      error: (err) => {
        console.error('Error loading app settings:', err);
      }
    });
  }

  /**
   * Process settings response and update the BehaviorSubject
   */
  private processSettings(response: ApplicationSetting[]): void {
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
