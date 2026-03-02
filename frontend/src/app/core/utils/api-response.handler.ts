/**
 * API Response Handler Utility
 *
 * Provides consistent handling of backend API responses across the frontend.
 * Handles all backend response formats including:
 * - Standardized responses: { success, message, data, meta }
 * - Legacy responses: { results, count } or raw arrays
 * - Paginated responses with meta.pagination
 *
 * Usage:
 *   import { handleApiResponse, handlePaginatedResponse, extractData } from '@core/utils/api-response.handler';
 *
 *   // Handle any API response
 *   this.apiService.getData().pipe(
 *     map(response => handleApiResponse<MyType>(response))
 *   ).subscribe(result => {
 *     if (result.success) {
 *       console.log(result.data);
 *     } else {
 *       console.error(result.message);
 *     }
 *   });
 *
 *   // Handle paginated responses
 *   this.apiService.getList().pipe(
 *     map(response => handlePaginatedResponse<MyType>(response))
 *   ).subscribe(result => {
 *     this.items = result.items;
 *     this.totalCount = result.pagination.totalCount;
 *   });
 */

/**
 * Standard API response structure (matches backend utils/api_response.py)
 */
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data: T;
  errors?: Record<string, string[]> | string[] | string;
  meta?: ApiResponseMeta;
}

/**
 * Response metadata
 */
export interface ApiResponseMeta {
  timestamp?: string;
  request_id?: string;
  pagination?: PaginationMeta;
  [key: string]: any;
}

/**
 * Pagination metadata structure
 */
export interface PaginationMeta {
  page: number;
  limit: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

/**
 * Paginated data result
 */
export interface PaginatedData<T> {
  items: T[];
  pagination: {
    page: number;
    pageSize: number;
    totalCount: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

/**
 * Normalized result for any API response
 */
export interface NormalizedResponse<T> {
  success: boolean;
  message: string;
  data: T | null;
  errors?: any;
}

/**
 * Handle any API response and normalize it to a standard structure
 *
 * @param response - Raw response from the API
 * @returns Normalized response object
 *
 * @example
 * this.http.get('/api/users/1').pipe(
 *   map(response => handleApiResponse<User>(response))
 * ).subscribe(result => {
 *   if (result.success) {
 *     this.user = result.data;
 *   }
 * });
 */
export function handleApiResponse<T>(response: any): NormalizedResponse<T> {
  // Handle null/undefined response
  if (response === null || response === undefined) {
    return {
      success: false,
      message: 'No response received',
      data: null,
      errors: null
    };
  }

  // Handle standardized response format
  if (typeof response === 'object' && 'success' in response) {
    return {
      success: response.success,
      message: response.message || (response.success ? 'Success' : 'Error'),
      data: response.data ?? null,
      errors: response.errors
    };
  }

  // Handle legacy/raw response (assume success)
  return {
    success: true,
    message: 'Success',
    data: response as T,
    errors: null
  };
}

/**
 * Handle paginated API responses from different formats
 *
 * Supports:
 * - Standardized: { success, data: [...], meta: { pagination: {...} } }
 * - DRF default: { results: [...], count: N }
 * - Raw array response
 *
 * @param response - Raw paginated response from the API
 * @returns Normalized paginated data
 *
 * @example
 * this.http.get('/api/users').pipe(
 *   map(response => handlePaginatedResponse<User>(response))
 * ).subscribe(result => {
 *   this.users = result.items;
 *   this.totalPages = result.pagination.totalPages;
 * });
 */
export function handlePaginatedResponse<T>(response: any, defaultPageSize: number = 10): PaginatedData<T> {
  const defaultPagination = {
    page: 1,
    pageSize: defaultPageSize,
    totalCount: 0,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false
  };

  // Handle null/undefined response
  if (response === null || response === undefined) {
    return { items: [], pagination: defaultPagination };
  }

  // Handle raw array response
  if (Array.isArray(response)) {
    return {
      items: response as T[],
      pagination: {
        ...defaultPagination,
        totalCount: response.length,
        totalPages: Math.ceil(response.length / defaultPageSize) || 1
      }
    };
  }

  // Handle standardized response with meta.pagination
  if (response.success !== undefined && response.meta?.pagination) {
    const pag = response.meta.pagination;
    return {
      items: (response.data || []) as T[],
      pagination: {
        page: pag.page || 1,
        pageSize: pag.limit || defaultPageSize,
        totalCount: pag.total_count || 0,
        totalPages: pag.total_pages || 1,
        hasNext: pag.has_next ?? false,
        hasPrevious: pag.has_previous ?? false
      }
    };
  }

  // Handle standardized response where data is the array
  if (response.success !== undefined && Array.isArray(response.data)) {
    return {
      items: response.data as T[],
      pagination: {
        ...defaultPagination,
        totalCount: response.data.length,
        totalPages: Math.ceil(response.data.length / defaultPageSize) || 1
      }
    };
  }

  // Handle DRF default pagination format: { results: [], count: N }
  if ('results' in response) {
    const totalCount = response.count || response.results?.length || 0;
    return {
      items: (response.results || []) as T[],
      pagination: {
        page: response.page || 1,
        pageSize: response.page_size || defaultPageSize,
        totalCount: totalCount,
        totalPages: Math.ceil(totalCount / (response.page_size || defaultPageSize)) || 1,
        hasNext: response.next !== null,
        hasPrevious: response.previous !== null
      }
    };
  }

  // Fallback: treat the entire response as data
  return { items: [], pagination: defaultPagination };
}

/**
 * Extract data from any API response format
 *
 * Use when you just need the data without pagination metadata.
 *
 * @param response - Raw response from the API
 * @returns Extracted data or null
 *
 * @example
 * this.http.get('/api/user').pipe(
 *   map(response => extractData<User>(response))
 * ).subscribe(user => {
 *   this.currentUser = user;
 * });
 */
export function extractData<T>(response: any): T | null {
  if (response === null || response === undefined) {
    return null;
  }

  // Standardized response
  if (typeof response === 'object' && 'success' in response) {
    return response.data ?? null;
  }

  // DRF pagination format
  if ('results' in response) {
    return response.results as T;
  }

  // Raw response
  return response as T;
}

/**
 * Extract error message from API error response
 *
 * @param error - Error response from the API
 * @returns Human-readable error message
 *
 * @example
 * this.http.post('/api/users', data).subscribe({
 *   error: (err) => {
 *     this.errorMessage = extractErrorMessage(err);
 *   }
 * });
 */
export function extractErrorMessage(error: any): string {
  // Handle standardized error response
  if (error?.error?.message) {
    return error.error.message;
  }

  // Handle validation errors object
  if (error?.error?.errors) {
    const errors = error.error.errors;
    if (typeof errors === 'string') {
      return errors;
    }
    if (Array.isArray(errors)) {
      return errors.join(', ');
    }
    // Object with field errors
    const messages = Object.entries(errors)
      .map(([field, msgs]) => {
        const messageList = Array.isArray(msgs) ? msgs : [msgs];
        return `${field}: ${messageList.join(', ')}`;
      });
    return messages.join('; ');
  }

  // Handle DRF default error format
  if (error?.error?.detail) {
    return error.error.detail;
  }

  // Handle non_field_errors
  if (error?.error?.non_field_errors) {
    return Array.isArray(error.error.non_field_errors)
      ? error.error.non_field_errors.join(', ')
      : error.error.non_field_errors;
  }

  // Handle plain error message
  if (error?.message) {
    return error.message;
  }

  // Handle HTTP status messages
  if (error?.status) {
    switch (error.status) {
      case 400: return 'Invalid request. Please check your input.';
      case 401: return 'Authentication required. Please log in.';
      case 403: return 'Permission denied.';
      case 404: return 'Resource not found.';
      case 413: return 'File too large.';
      case 429: return 'Too many requests. Please try again later.';
      case 500: return 'Server error. Please try again later.';
      case 503: return 'Service unavailable. Please try again later.';
      default: return `Request failed with status ${error.status}`;
    }
  }

  return 'An unexpected error occurred';
}

/**
 * Check if response indicates success
 *
 * @param response - Raw response from the API
 * @returns true if response indicates success
 */
export function isSuccessResponse(response: any): boolean {
  if (response === null || response === undefined) {
    return false;
  }

  // Standardized response
  if (typeof response === 'object' && 'success' in response) {
    return response.success === true;
  }

  // Any non-null response from a successful HTTP call is considered success
  return true;
}

/**
 * Get message from API response
 *
 * @param response - Raw response from the API
 * @returns Message string or default
 */
export function getResponseMessage(response: any, defaultMessage: string = ''): string {
  if (response?.message) {
    return response.message;
  }
  return defaultMessage;
}
