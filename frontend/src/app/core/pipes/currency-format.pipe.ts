import { Pipe, PipeTransform } from '@angular/core';
import { AppSettingsService } from '../services/app-settings.service';
import { CurrencyUtils } from '../utils/currency.utils';

/**
 * Custom currency pipe that uses the application's default currency setting
 * Usage: {{ amount | currencyFormat }}
 * Usage with specific currency: {{ amount | currencyFormat:booking.currency }}
 */
@Pipe({
  name: 'currencyFormat',
  standalone: true,
  pure: false, // Re-evaluate when app settings change
})
export class CurrencyFormatPipe implements PipeTransform {
  constructor(private appSettingsService: AppSettingsService) {}

  transform(
    amount: number | null | undefined,
    currency?: string | null,
    locale: string = 'en-US'
  ): string {
    const currencyCode = currency || this.appSettingsService.getDefaultCurrency() || 'USD';
    return CurrencyUtils.format(amount, currencyCode, locale);
  }
}
