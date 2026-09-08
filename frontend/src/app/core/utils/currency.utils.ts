/**
 * Centralized currency formatting utility.
 * Callers resolve the currency code themselves (e.g. via the injected
 * AppSettingsService) and pass it in - this stays a plain function with no
 * static singleton to initialize, so there's no risk of it silently running
 * before its dependency is wired up.
 */
export class CurrencyUtils {
  /**
   * Format an amount as currency.
   * @param amount - The amount to format
   * @param currencyCode - The currency code to format with (e.g. from AppSettingsService.getDefaultCurrency())
   * @param locale - Optional locale (defaults to 'en-US')
   * @returns Formatted currency string
   */
  static format(
    amount: number | null | undefined,
    currencyCode: string,
    locale: string = 'en-US'
  ): string {
    if (amount === null || amount === undefined || isNaN(amount)) {
      return 'N/A';
    }

    try {
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(amount);
    } catch (error) {
      console.error('Error formatting currency:', error);
      return `${currencyCode} ${amount.toFixed(2)}`;
    }
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
        maximumFractionDigits: decimals,
      });
    } catch (error) {
      console.error('Error formatting number:', error);
      return numericAmount.toFixed(decimals);
    }
  }
}
