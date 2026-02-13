import { Pipe, PipeTransform } from '@angular/core';
import { AppSettingsService } from '../services/app-settings.service';

/**
 * Custom currency pipe that uses the application's default currency setting
 * Usage: {{ amount | currencyFormat }}
 * Usage with specific currency: {{ amount | currencyFormat:booking.currency }}
 */
@Pipe({
  name: 'currencyFormat',
  standalone: true,
  pure: false // Re-evaluate when app settings change
})
export class CurrencyFormatPipe implements PipeTransform {
  constructor(private appSettingsService: AppSettingsService) {}

  transform(
    amount: number | null | undefined,
    currency?: string | null,
    locale: string = 'en-US'
  ): string {
    if (amount === null || amount === undefined || isNaN(amount)) {
      return 'N/A';
    }

    const currencyCode = currency || this.appSettingsService.getDefaultCurrency() || 'USD';

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
}
