import { Injectable } from '@angular/core';

/**
 * Shared utility service for date formatting operations
 */
@Injectable({
  providedIn: 'root'
})
export class DateUtilsService {

  /**
   * Formats a date string to a localized date format (e.g., "January 1, 2024")
   * @param dateString The date string to format
   * @param defaultValue The value to return if date is invalid (default: 'N/A')
   * @returns Formatted date string
   */
  formatDate(dateString: string | null | undefined, defaultValue: string = 'N/A'): string {
    if (!dateString) return defaultValue;

    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return defaultValue;

      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return defaultValue;
    }
  }

  /**
   * Formats a date string to a localized date and time format (e.g., "January 1, 2024, 12:00 PM")
   * @param dateString The date string to format
   * @param defaultValue The value to return if date is invalid (default: 'N/A')
   * @returns Formatted date-time string
   */
  formatDateTime(dateString: string | null | undefined, defaultValue: string = 'N/A'): string {
    if (!dateString) return defaultValue;

    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return defaultValue;

      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return defaultValue;
    }
  }

  /**
   * Formats a date string to a short date format (e.g., "01/15/2024")
   * @param dateString The date string to format
   * @param defaultValue The value to return if date is invalid (default: 'N/A')
   * @returns Formatted short date string
   */
  formatShortDate(dateString: string | null | undefined, defaultValue: string = 'N/A'): string {
    if (!dateString) return defaultValue;

    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return defaultValue;

      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    } catch {
      return defaultValue;
    }
  }

  /**
   * Formats a date string to ISO format for inputs (e.g., "2024-01-15")
   * @param dateString The date string to format
   * @returns Formatted ISO date string or empty string if invalid
   */
  formatForInput(dateString: string | null | undefined): string {
    if (!dateString) return '';

    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return '';

      return date.toISOString().split('T')[0];
    } catch {
      return '';
    }
  }

  /**
   * Calculates the difference in days between two dates
   * @param startDate Start date
   * @param endDate End date
   * @returns Number of days between dates, or null if dates are invalid
   */
  getDaysDifference(startDate: string | Date, endDate: string | Date): number | null {
    try {
      const start = new Date(startDate);
      const end = new Date(endDate);

      if (isNaN(start.getTime()) || isNaN(end.getTime())) return null;

      const diffTime = Math.abs(end.getTime() - start.getTime());
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    } catch {
      return null;
    }
  }

  /**
   * Checks if a date is in the past
   * @param dateString The date to check
   * @returns True if date is in the past
   */
  isPastDate(dateString: string | Date): boolean {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return false;

      return date < new Date();
    } catch {
      return false;
    }
  }

  /**
   * Checks if a date is in the future
   * @param dateString The date to check
   * @returns True if date is in the future
   */
  isFutureDate(dateString: string | Date): boolean {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return false;

      return date > new Date();
    } catch {
      return false;
    }
  }

  /**
   * Gets a relative time string (e.g., "2 days ago", "in 3 hours")
   * @param dateString The date to compare
   * @returns Relative time string
   */
  getRelativeTime(dateString: string | Date): string {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'N/A';

      const now = new Date();
      const diffMs = date.getTime() - now.getTime();
      const diffSecs = Math.floor(diffMs / 1000);
      const diffMins = Math.floor(diffSecs / 60);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffDays > 0) return `in ${diffDays} day${diffDays > 1 ? 's' : ''}`;
      if (diffDays < 0) return `${Math.abs(diffDays)} day${Math.abs(diffDays) > 1 ? 's' : ''} ago`;
      if (diffHours > 0) return `in ${diffHours} hour${diffHours > 1 ? 's' : ''}`;
      if (diffHours < 0) return `${Math.abs(diffHours)} hour${Math.abs(diffHours) > 1 ? 's' : ''} ago`;
      if (diffMins > 0) return `in ${diffMins} minute${diffMins > 1 ? 's' : ''}`;
      if (diffMins < 0) return `${Math.abs(diffMins)} minute${Math.abs(diffMins) > 1 ? 's' : ''} ago`;

      return 'just now';
    } catch {
      return 'N/A';
    }
  }
}
