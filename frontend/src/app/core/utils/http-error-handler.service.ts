import { Injectable } from '@angular/core';
import { FormGroup } from '@angular/forms';

/**
 * A backend error body whose exact shape varies by endpoint (see the format
 * list in the class docstring below). Fields are declared explicitly rather
 * than via a `[key: string]` index signature so dot-notation access
 * type-checks under `noPropertyAccessFromIndexSignature` - field-name keys
 * (the validation-error case) still go through `Object.entries`/brackets.
 */
interface ErrorBodyShape {
  success?: boolean;
  message?: string;
  errors?: unknown;
  error?: unknown;
  detail?: string | string[];
  non_field_errors?: string[];
  [field: string]: unknown;
}

/**
 * The minimal shape this service actually relies on. Callers hand this
 * service whatever their `catchError`/`subscribe({ error })` callback
 * receives - typically an `HttpErrorResponse`, but rxjs/TS types that as
 * `unknown`, and not every caller is even guaranteed to be looking at a real
 * HTTP error. Narrowing to just the fields used (rather than requiring a
 * full `HttpErrorResponse`) keeps every method here usable from a plain
 * `unknown` catch variable without a cast at every call site.
 */
interface HttpLikeError {
  status?: number;
  message?: string;
  error?: unknown;
}

function toHttpLikeError(error: unknown): HttpLikeError {
  return error && typeof error === 'object' ? (error as HttpLikeError) : {};
}

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
  providedIn: 'root',
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
  getErrorMessage(error: unknown, defaultMessage: string = 'An error occurred'): string {
    const httpError = toHttpLikeError(error);

    // Connection errors (network unavailable, CORS, etc.)
    if (httpError.status === 0) {
      return 'Cannot connect to the server. Please check your network connection.';
    }

    if (httpError.error) {
      const bodyMessage = this.extractBodyErrorMessage(httpError.error);
      if (bodyMessage) {
        return bodyMessage;
      }
    }

    const statusMessage = httpError.status ? this.getStatusMessage(httpError.status) : null;
    return statusMessage || httpError.message || defaultMessage;
  }

  /**
   * Try each known body-error shape in turn and return the first message
   * found, or null if none of them match.
   */
  private extractBodyErrorMessage(body: unknown): string | null {
    // Django REST Framework standard error format: { error: "message" }
    if (typeof body === 'string') {
      return body;
    }

    if (!body || typeof body !== 'object') {
      return null;
    }
    const errorBody = body as ErrorBodyShape;

    // Standardized response format: { success: false, message: "...", errors: {...} }
    if (errorBody.success === false && errorBody.message) {
      // If there are also field-level errors, append them
      if (errorBody.errors && this.hasFieldErrors(errorBody.errors)) {
        const fieldErrors = this.extractFieldErrors(errorBody.errors as Record<string, unknown>);
        return `${errorBody.message}: ${fieldErrors}`;
      }
      return errorBody.message as string;
    }

    // Object with error property
    if (typeof errorBody.error === 'string') {
      return errorBody.error;
    }

    // Object with detail property (common in DRF)
    if (errorBody.detail) {
      if (typeof errorBody.detail === 'string') {
        return errorBody.detail;
      }
      if (Array.isArray(errorBody.detail)) {
        return errorBody.detail.join(', ');
      }
    }

    // Validation errors with field names
    if (this.hasFieldErrors(errorBody)) {
      return this.extractFieldErrors(errorBody);
    }

    // Non-field errors (common in DRF forms)
    if (Array.isArray(errorBody.non_field_errors)) {
      return errorBody.non_field_errors.join(', ');
    }

    return null;
  }

  private static readonly STATUS_MESSAGES: Record<number, string> = {
    400: 'Invalid request. Please check your input.',
    401: 'Authentication required. Please log in again.',
    403: 'You do not have permission to perform this action.',
    404: 'The requested resource was not found.',
    409: 'Conflict: This action conflicts with existing data.',
    422: 'Validation error. Please check your input.',
    500: 'Server error. Please try again later.',
    503: 'Service temporarily unavailable. Please try again later.',
  };

  private getStatusMessage(status: number): string | null {
    return HttpErrorHandlerService.STATUS_MESSAGES[status] || null;
  }

  /**
   * Get specific field error message
   * Useful for form field validation errors
   *
   * @param error - HTTP error response
   * @param fieldName - Name of the field to get error for
   * @returns Error message for the field, or null if none found
   */
  getFieldError(error: unknown, fieldName: string): string | null {
    const body = toHttpLikeError(error).error;
    if (!body || typeof body !== 'object') {
      return null;
    }
    const value = (body as Record<string, unknown>)[fieldName];
    if (!value) {
      return null;
    }
    return Array.isArray(value) ? value[0] : (value as string);
  }

  /**
   * Check if error contains field-specific validation errors
   */
  private hasFieldErrors(errorObject: unknown): boolean {
    if (!errorObject || typeof errorObject !== 'object') {
      return false;
    }

    const record = errorObject as Record<string, unknown>;
    // Exclude known non-field error properties
    const nonFieldKeys = ['error', 'detail', 'non_field_errors', 'status', 'statusText'];
    const keys = Object.keys(record).filter(key => !nonFieldKeys.includes(key));

    return (
      keys.length > 0 &&
      keys.some(key => Array.isArray(record[key]) || typeof record[key] === 'string')
    );
  }

  /**
   * Extract and format field validation errors
   */
  private extractFieldErrors(errorObject: Record<string, unknown>): string {
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
  isStatus(error: unknown, statusCode: number): boolean {
    return toHttpLikeError(error).status === statusCode;
  }

  /**
   * Check if error is an authentication error (401)
   */
  isAuthError(error: unknown): boolean {
    return this.isStatus(error, 401);
  }

  /**
   * Check if error is a permission error (403)
   */
  isPermissionError(error: unknown): boolean {
    return this.isStatus(error, 403);
  }

  /**
   * Check if error is a validation error (400 or 422)
   */
  isValidationError(error: unknown): boolean {
    return this.isStatus(error, 400) || this.isStatus(error, 422);
  }

  /**
   * Check if error is a network/connection error
   */
  isNetworkError(error: unknown): boolean {
    return toHttpLikeError(error).status === 0;
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
  getFieldErrors(error: unknown): Record<string, string> {
    const result: Record<string, string> = {};

    const body = toHttpLikeError(error).error as ErrorBodyShape | undefined;
    if (!body) {
      return result;
    }

    // Handle standardized response format
    const errorObj = (body.errors || body) as Record<string, unknown>;
    const nonFieldKeys = [
      'error',
      'detail',
      'non_field_errors',
      'status',
      'statusText',
      'success',
      'message',
      'meta',
    ];

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
  applyServerErrors(error: unknown, form: FormGroup): void {
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
  isStandardizedError(error: unknown): boolean {
    const body = toHttpLikeError(error).error as ErrorBodyShape | undefined;
    return body?.success === false;
  }

  /**
   * Get the message from a standardized error response
   */
  getStandardizedMessage(error: unknown): string | null {
    if (this.isStandardizedError(error)) {
      const body = toHttpLikeError(error).error as ErrorBodyShape;
      return body.message || null;
    }
    return null;
  }
}
