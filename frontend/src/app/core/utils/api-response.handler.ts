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
export interface ApiResponse<T = unknown> {
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
  [key: string]: unknown;
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
  errors?: Record<string, string[]> | string[] | string | null;
}

/**
 * A response body whose exact shape isn't known ahead of time - these
 * handlers exist precisely to sniff it out. Every field the handlers below
 * look for is declared (rather than relying on a `[key: string]` index
 * signature) so dot-notation access on a narrowed value type-checks under
 * `noPropertyAccessFromIndexSignature`.
 */
interface UnknownRecord {
  success?: unknown;
  message?: unknown;
  data?: unknown;
  errors?: unknown;
  meta?: unknown;
  pagination?: unknown;
  page?: unknown;
  limit?: unknown;
  page_size?: unknown;
  total_count?: unknown;
  total_pages?: unknown;
  has_next?: unknown;
  has_previous?: unknown;
  results?: unknown;
  count?: unknown;
  next?: unknown;
  previous?: unknown;
  error?: unknown;
  detail?: unknown;
  non_field_errors?: unknown;
  status?: unknown;
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null;
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
export function handleApiResponse<T>(response: unknown): NormalizedResponse<T> {
  // Handle null/undefined response
  if (response === null || response === undefined) {
    return {
      success: false,
      message: 'No response received',
      data: null,
      errors: null,
    };
  }

  // Handle standardized response format
  if (isRecord(response) && 'success' in response) {
    return {
      success: response.success === true,
      message: (response.message as string) || (response.success ? 'Success' : 'Error'),
      data: (response.data as T) ?? null,
      errors: response.errors as NormalizedResponse<T>['errors'],
    };
  }

  // Handle legacy/raw response (assume success)
  return {
    success: true,
    message: 'Success',
    data: response as T,
    errors: null,
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
function defaultPaginationFor(defaultPageSize: number): PaginatedData<never>['pagination'] {
  return {
    page: 1,
    pageSize: defaultPageSize,
    totalCount: 0,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
  };
}

/** Raw array response - the entire array is the item list. */
function paginatedFromArray<T>(response: unknown[], defaultPageSize: number): PaginatedData<T> {
  return {
    items: response as T[],
    pagination: {
      ...defaultPaginationFor(defaultPageSize),
      totalCount: response.length,
      totalPages: Math.ceil(response.length / defaultPageSize) || 1,
    },
  };
}

/** Standardized response with meta.pagination: { success, data: [...], meta: { pagination: {...} } } */
function paginatedFromMeta<T>(
  response: UnknownRecord,
  defaultPageSize: number
): PaginatedData<T> | undefined {
  const meta = response.meta as UnknownRecord | undefined;
  const pag = meta?.pagination as UnknownRecord | undefined;
  if (response.success === undefined || !pag) {
    return undefined;
  }
  return {
    items: (response.data as T[]) || [],
    pagination: {
      page: (pag.page as number) || 1,
      pageSize: (pag.limit as number) || defaultPageSize,
      totalCount: (pag.total_count as number) || 0,
      totalPages: (pag.total_pages as number) || 1,
      hasNext: (pag.has_next as boolean) ?? false,
      hasPrevious: (pag.has_previous as boolean) ?? false,
    },
  };
}

/** Standardized response where data itself is the array: { success, data: [...] } */
function paginatedFromDataArray<T>(
  response: UnknownRecord,
  defaultPageSize: number
): PaginatedData<T> | undefined {
  if (response.success === undefined || !Array.isArray(response.data)) {
    return undefined;
  }
  const data = response.data as T[];
  return {
    items: data,
    pagination: {
      ...defaultPaginationFor(defaultPageSize),
      totalCount: data.length,
      totalPages: Math.ceil(data.length / defaultPageSize) || 1,
    },
  };
}

/** DRF default pagination format: { results: [], count: N } */
function paginatedFromDrf<T>(
  response: UnknownRecord,
  defaultPageSize: number
): PaginatedData<T> | undefined {
  if (!('results' in response)) {
    return undefined;
  }
  const results = (response.results as T[]) || [];
  const pageSize = (response.page_size as number) || defaultPageSize;
  const totalCount = (response.count as number) || results.length || 0;
  return {
    items: results,
    pagination: {
      page: (response.page as number) || 1,
      pageSize,
      totalCount,
      totalPages: Math.ceil(totalCount / pageSize) || 1,
      hasNext: response.next !== null,
      hasPrevious: response.previous !== null,
    },
  };
}

export function handlePaginatedResponse<T>(
  response: unknown,
  defaultPageSize: number = 10
): PaginatedData<T> {
  const fallback: PaginatedData<T> = {
    items: [],
    pagination: defaultPaginationFor(defaultPageSize),
  };

  if (response === null || response === undefined) {
    return fallback;
  }

  if (Array.isArray(response)) {
    return paginatedFromArray<T>(response, defaultPageSize);
  }

  if (!isRecord(response)) {
    return fallback;
  }

  return (
    paginatedFromMeta<T>(response, defaultPageSize) ||
    paginatedFromDataArray<T>(response, defaultPageSize) ||
    paginatedFromDrf<T>(response, defaultPageSize) ||
    fallback
  );
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
export function extractData<T>(response: unknown): T | null {
  if (response === null || response === undefined) {
    return null;
  }

  if (isRecord(response)) {
    // Standardized response
    if ('success' in response) {
      return (response.data as T) ?? null;
    }

    // DRF pagination format
    if ('results' in response) {
      return response.results as T;
    }
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
function formatValidationErrors(errors: unknown): string {
  if (typeof errors === 'string') {
    return errors;
  }
  if (Array.isArray(errors)) {
    return errors.join(', ');
  }
  // Object with field errors
  return Object.entries(errors as UnknownRecord)
    .map(([field, msgs]) => {
      const messageList = Array.isArray(msgs) ? msgs : [msgs];
      return `${field}: ${messageList.join(', ')}`;
    })
    .join('; ');
}

const HTTP_STATUS_MESSAGES: Record<number, string> = {
  400: 'Invalid request. Please check your input.',
  401: 'Authentication required. Please log in.',
  403: 'Permission denied.',
  404: 'Resource not found.',
  413: 'File too large.',
  429: 'Too many requests. Please try again later.',
  500: 'Server error. Please try again later.',
  503: 'Service unavailable. Please try again later.',
};

export function extractErrorMessage(error: unknown): string {
  if (!isRecord(error)) {
    return 'An unexpected error occurred';
  }

  const body = isRecord(error.error) ? error.error : undefined;

  // Handle standardized error response
  if (body?.message) {
    return body.message as string;
  }

  // Handle validation errors object
  if (body?.errors) {
    return formatValidationErrors(body.errors);
  }

  // Handle DRF default error format
  if (body?.detail) {
    return body.detail as string;
  }

  // Handle non_field_errors
  if (body?.non_field_errors) {
    return Array.isArray(body.non_field_errors)
      ? body.non_field_errors.join(', ')
      : (body.non_field_errors as string);
  }

  // Handle plain error message
  if (error.message) {
    return error.message as string;
  }

  // Handle HTTP status messages
  if (error.status) {
    const status = error.status as number;
    return HTTP_STATUS_MESSAGES[status] || `Request failed with status ${status}`;
  }

  return 'An unexpected error occurred';
}

/**
 * Check if response indicates success
 *
 * @param response - Raw response from the API
 * @returns true if response indicates success
 */
export function isSuccessResponse(response: unknown): boolean {
  if (response === null || response === undefined) {
    return false;
  }

  // Standardized response
  if (isRecord(response) && 'success' in response) {
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
export function getResponseMessage(response: unknown, defaultMessage: string = ''): string {
  if (isRecord(response) && typeof response.message === 'string') {
    return response.message;
  }
  return defaultMessage;
}
