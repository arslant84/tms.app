import { AppSettingsService } from '../services/app-settings.service';

/**
 * Centralized currency formatting utility
 * Ensures consistent currency display across the entire application
 */
export class CurrencyUtils {
  private static appSettingsService: AppSettingsService;

  /**
   * Initialize the utility with the AppSettingsService
   * This should be called once during app initialization
   */
  static initialize(appSettingsService: AppSettingsService): void {
    CurrencyUtils.appSettingsService = appSettingsService;
  }

  /**
   * Format currency using the application's default currency
   * @param amount - The amount to format
   * @param locale - Optional locale (defaults to 'en-US')
   * @returns Formatted currency string
   */
  static formatCurrency(
    amount: number | null | undefined,
    locale: string = 'en-US'
  ): string {
    if (amount === null || amount === undefined || isNaN(amount)) {
      return 'N/A';
    }

    const currency = CurrencyUtils.appSettingsService?.getDefaultCurrency() || 'USD';

    try {
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount);
    } catch (error) {
      console.error('Error formatting currency:', error);
      return `${currency} ${amount.toFixed(2)}`;
    }
  }

  /**
   * Format currency with a specific currency code
   * Use this when the currency is stored with the data (e.g., flight bookings)
   * @param amount - The amount to format
   * @param currency - The specific currency code
   * @param locale - Optional locale (defaults to 'en-US')
   * @returns Formatted currency string
   */
  static formatCurrencyWithCode(
    amount: number | null | undefined,
    currency: string | null | undefined,
    locale: string = 'en-US'
  ): string {
    if (amount === null || amount === undefined || isNaN(amount)) {
      return 'N/A';
    }

    const currencyCode = currency || CurrencyUtils.appSettingsService?.getDefaultCurrency() || 'USD';

    try {
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount);
    } catch (error) {
      console.error('Error formatting currency:', error);
      return `${currencyCode} ${amount.toFixed(2)}`;
    }
  }

  /**
   * Get the default currency code from app settings
   * @returns Default currency code
   */
  static getDefaultCurrency(): string {
    return CurrencyUtils.appSettingsService?.getDefaultCurrency() || 'USD';
  }

  /**
   * Format a number with locale-specific formatting (no currency symbol)
   * @param amount - The amount to format
   * @param decimals - Number of decimal places
   * @param locale - Optional locale (defaults to 'en-US')
   * @returns Formatted number string
   */
  static formatNumber(
    amount: number | string | null | undefined,
    decimals: number = 2,
    locale: string = 'en-US'
  ): string {
    if (amount === null || amount === undefined) {
      return 'N/A';
    }

    const numericAmount = typeof amount === 'string' ? parseFloat(amount) : amount;

    if (isNaN(numericAmount)) {
      return 'N/A';
    }

    try {
      return numericAmount.toLocaleString(locale, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      });
    } catch (error) {
      console.error('Error formatting number:', error);
      return numericAmount.toFixed(decimals);
    }
  }
}
