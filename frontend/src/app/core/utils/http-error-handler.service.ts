import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

/**
 * HTTP Error Handler Utility Service
 * Provides centralized error message extraction and formatting
 *
 * Supports multiple backend response formats:
 * - Standardized: { success: false, message: "...", errors: {...} }
 * - DRF default: { error: "...", detail: "..." }
 * - Field errors: { field_name: ["error1", "error2"] }
 *
 * Usage:
 * ```typescript
 * error: (err) => {
 *   const message = this.errorHandler.getErrorMessage(err);
 *   this.toastService.error(message);
 * }
 * ```
 */
@Injectable({
  providedIn: 'root'
})
export class HttpErrorHandlerService {

  /**
   * Extract user-friendly error message from HTTP error response
   * Handles multiple backend error formats:
   * - Standardized: { success: false, message: "...", errors: {...} }
   * - { error: "message" }
   * - { detail: "message" }
   * - { field_name: ["error1", "error2"] }
   * - { non_field_errors: ["error"] }
   *
   * @param error - HTTP error response
   * @param defaultMessage - Fallback message if no error details found
   * @returns User-friendly error message
   */
  getErrorMessage(error: HttpErrorResponse | any, defaultMessage: string = 'An error occurred'): string {
    // Connection errors (network unavailable, CORS, etc.)
    if (error.status === 0) {
      return 'Cannot connect to the server. Please check your network connection.';
    }

    // Server returned error response
    if (error.error) {
      // Django REST Framework standard error format: { error: "message" }
      if (typeof error.error === 'string') {
        return error.error;
      }

      // Standardized response format: { success: false, message: "...", errors: {...} }
      if (error.error.success === false && error.error.message) {
        // If there are also field-level errors, append them
        if (error.error.errors && this.hasFieldErrors(error.error.errors)) {
          const fieldErrors = this.extractFieldErrors(error.error.errors);
          return `${error.error.message}: ${fieldErrors}`;
        }
        return error.error.message;
      }

      // Object with error property
      if (error.error.error) {
        return error.error.error;
      }

      // Object with detail property (common in DRF)
      if (error.error.detail) {
        if (typeof error.error.detail === 'string') {
          return error.error.detail;
        }
        // Array of details
        if (Array.isArray(error.error.detail)) {
          return error.error.detail.join(', ');
        }
      }

      // Validation errors with field names
      if (this.hasFieldErrors(error.error)) {
        return this.extractFieldErrors(error.error);
      }

      // Non-field errors (common in DRF forms)
      if (error.error.non_field_errors && Array.isArray(error.error.non_field_errors)) {
        return error.error.non_field_errors.join(', ');
      }
    }

    // HTTP status-specific messages
    switch (error.status) {
      case 400:
        return 'Invalid request. Please check your input.';
      case 401:
        return 'Authentication required. Please log in again.';
      case 403:
        return 'You do not have permission to perform this action.';
      case 404:
        return 'The requested resource was not found.';
      case 409:
        return 'Conflict: This action conflicts with existing data.';
      case 422:
        return 'Validation error. Please check your input.';
      case 500:
        return 'Server error. Please try again later.';
      case 503:
        return 'Service temporarily unavailable. Please try again later.';
      default:
        return error.message || defaultMessage;
    }
  }

  /**
   * Get specific field error message
   * Useful for form field validation errors
   *
   * @param error - HTTP error response
   * @param fieldName - Name of the field to get error for
   * @returns Error message for the field, or null if none found
   */
  getFieldError(error: HttpErrorResponse | any, fieldName: string): string | null {
    if (error.error && error.error[fieldName]) {
      if (Array.isArray(error.error[fieldName])) {
        return error.error[fieldName][0];
      }
      return error.error[fieldName];
    }
    return null;
  }

  /**
   * Check if error contains field-specific validation errors
   */
  private hasFieldErrors(errorObject: any): boolean {
    if (!errorObject || typeof errorObject !== 'object') {
      return false;
    }

    // Exclude known non-field error properties
    const nonFieldKeys = ['error', 'detail', 'non_field_errors', 'status', 'statusText'];
    const keys = Object.keys(errorObject).filter(key => !nonFieldKeys.includes(key));

    return keys.length > 0 && keys.some(key =>
      Array.isArray(errorObject[key]) || typeof errorObject[key] === 'string'
    );
  }

  /**
   * Extract and format field validation errors
   */
  private extractFieldErrors(errorObject: any): string {
    const errors: string[] = [];
    const nonFieldKeys = ['error', 'detail', 'non_field_errors', 'status', 'statusText'];

    for (const [field, messages] of Object.entries(errorObject)) {
      if (nonFieldKeys.includes(field)) {
        continue;
      }

      const fieldLabel = this.formatFieldName(field);

      if (Array.isArray(messages)) {
        errors.push(`${fieldLabel}: ${messages.join(', ')}`);
      } else if (typeof messages === 'string') {
        errors.push(`${fieldLabel}: ${messages}`);
      }
    }

    return errors.length > 0 ? errors.join('; ') : 'Validation errors occurred';
  }

  /**
   * Convert snake_case field names to human-readable format
   * Example: "old_password" => "Old Password"
   */
  private formatFieldName(field: string): string {
    return field
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  /**
   * Check if error is a specific HTTP status code
   */
  isStatus(error: HttpErrorResponse | any, statusCode: number): boolean {
    return error.status === statusCode;
  }

  /**
   * Check if error is an authentication error (401)
   */
  isAuthError(error: HttpErrorResponse | any): boolean {
    return this.isStatus(error, 401);
  }

  /**
   * Check if error is a permission error (403)
   */
  isPermissionError(error: HttpErrorResponse | any): boolean {
    return this.isStatus(error, 403);
  }

  /**
   * Check if error is a validation error (400 or 422)
   */
  isValidationError(error: HttpErrorResponse | any): boolean {
    return this.isStatus(error, 400) || this.isStatus(error, 422);
  }

  /**
   * Check if error is a network/connection error
   */
  isNetworkError(error: HttpErrorResponse | any): boolean {
    return error.status === 0;
  }

  /**
   * Get all field errors as an object
   * Useful for applying errors to form controls
   *
   * @param error - HTTP error response
   * @returns Object mapping field names to error messages
   *
   * Example:
   * ```typescript
   * const fieldErrors = this.errorHandler.getFieldErrors(err);
   * // { email: 'This field is required', password: 'Password too short' }
   *
   * Object.entries(fieldErrors).forEach(([field, message]) => {
   *   this.form.get(field)?.setErrors({ serverError: message });
   * });
   * ```
   */
  getFieldErrors(error: HttpErrorResponse | any): Record<string, string> {
    const result: Record<string, string> = {};

    if (!error?.error) {
      return result;
    }

    // Handle standardized response format
    const errorObj = error.error.errors || error.error;
    const nonFieldKeys = ['error', 'detail', 'non_field_errors', 'status', 'statusText', 'success', 'message', 'meta'];

    for (const [field, messages] of Object.entries(errorObj)) {
      if (nonFieldKeys.includes(field)) {
        continue;
      }

      if (Array.isArray(messages)) {
        result[field] = (messages as string[]).join(', ');
      } else if (typeof messages === 'string') {
        result[field] = messages;
      }
    }

    return result;
  }

  /**
   * Apply server errors to a reactive form
   * Sets server errors on matching form controls
   *
   * @param error - HTTP error response
   * @param form - Angular FormGroup to apply errors to
   *
   * Example:
   * ```typescript
   * this.http.post('/api/users', data).subscribe({
   *   error: (err) => {
   *     this.errorHandler.applyServerErrors(err, this.userForm);
   *   }
   * });
   * ```
   */
  applyServerErrors(error: HttpErrorResponse | any, form: any): void {
    const fieldErrors = this.getFieldErrors(error);

    Object.entries(fieldErrors).forEach(([field, message]) => {
      const control = form.get(field);
      if (control) {
        control.setErrors({ serverError: message });
        control.markAsTouched();
      }
    });
  }

  /**
   * Check if response is a standardized error response
   */
  isStandardizedError(error: HttpErrorResponse | any): boolean {
    return error?.error?.success === false;
  }

  /**
   * Get the message from a standardized error response
   */
  getStandardizedMessage(error: HttpErrorResponse | any): string | null {
    if (this.isStandardizedError(error)) {
      return error.error.message || null;
    }
    return null;
  }
}
