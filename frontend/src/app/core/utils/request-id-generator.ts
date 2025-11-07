/**
 * Request ID Generator Utility
 *
 * Implements unified request ID naming convention:
 * - General format: [TYPE]-[YYYYMMDD-HHMM]-[CONTEXT]-[UNIQUE_ID]
 * - Claims format: CLM-[YYYYMMDD-HHMM]-[XXXXX]-[XXXX] (no context, double unique IDs)
 *
 * Examples:
 * - TSR: TSR-20250702-1423-NYC-PCYX
 * - VIS: VIS-20250702-1423-USA-5X9R
 * - ACCOM: ACCOM-20250702-1423-DEL-2Y8P
 * - CLM: CLM-20250702-1423-QWSDF-P4Z5 (5+4 character unique IDs)
 * - TRN: TRN-20250702-1423-LOCAL-3K8M
 */

// Valid request types
export type RequestType = 'TSR' | 'VIS' | 'ACCOM' | 'CLM' | 'TRN';

// Characters to use for unique ID generation (avoiding ambiguous characters like 0/O, 1/I)
const UNIQUE_ID_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

/**
 * Generates a random string of specified length using non-ambiguous characters
 * @param length Length of the unique ID to generate
 * @returns Random string of specified length
 */
export function generateUniqueId(length: number = 4): string {
  let result = '';
  for (let i = 0; i < length; i++) {
    result += UNIQUE_ID_CHARS.charAt(Math.floor(Math.random() * UNIQUE_ID_CHARS.length));
  }
  return result;
}

/**
 * Formats a date as YYYYMMDD-HHMM
 * @param date Date to format
 * @returns Formatted date string
 */
export function formatDateForRequestId(date: Date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}${month}${day}-${hours}${minutes}`;
}

/**
 * Validates a context string to ensure it meets the requirements
 * @param context Context string to validate
 * @returns Validated context string (uppercase, no special characters)
 */
export function validateContext(context: string): string {
  // Remove special characters and spaces, convert to uppercase
  const sanitized = context.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();

  // Limit to 5 characters max
  return sanitized.substring(0, 5);
}

/**
 * Generates a unified request ID according to the specified format
 * @param type Request type (TSR, VIS, ACCOM, CLM, TRN)
 * @param context Context information (e.g., NYC for New York, USA for United States, LOCAL for local transport)
 * @param date Optional date to use (defaults to current date/time)
 * @returns Formatted request ID
 */
export function generateRequestId(
  type: RequestType,
  context: string,
  date: Date = new Date()
): string {
  const timestamp = formatDateForRequestId(date);
  const validContext = validateContext(context);

  // Special handling for claims - they need XXXXX-XXXX format instead of context-unique
  if (type === 'CLM') {
    const uniqueId1 = generateUniqueId(5); // 5 characters
    const uniqueId2 = generateUniqueId(4); // 4 characters
    return `${type}-${timestamp}-${uniqueId1}-${uniqueId2}`;
  }

  // For other types, use the original format
  const uniqueId = generateUniqueId();
  return `${type}-${timestamp}-${validContext}-${uniqueId}`;
}

/**
 * Parses a request ID into its component parts
 * @param requestId Request ID to parse
 * @returns Object containing the parsed components, or null if invalid
 */
export function parseRequestId(requestId: string): {
  type: RequestType;
  timestamp: string;
  context: string;
  uniqueId: string;
  date: Date;
} | null {
  const parts = requestId.split('-');

  // Claims have 5 parts: CLM-YYYYMMDD-HHMM-XXXXX-XXXX
  // Others have 5 parts: TYPE-YYYYMMDD-HHMM-CONTEXT-UNIQUEID
  if (parts.length !== 5) {
    return null;
  }

  const [type, dateStr, timeStr, part3, part4] = parts;

  let context: string;
  let uniqueId: string;

  if (type === 'CLM') {
    // For claims: part3 is first unique ID, part4 is second unique ID
    context = 'CLAIM'; // Standard context for claims
    uniqueId = `${part3}-${part4}`; // Combine both unique parts
  } else {
    // For other types: part3 is context, part4 is unique ID
    context = part3;
    uniqueId = part4;
  }

  // Validate type
  if (!['TSR', 'VIS', 'ACCOM', 'CLM', 'TRN'].includes(type)) {
    return null;
  }

  // Parse date
  try {
    const year = parseInt(dateStr.substring(0, 4));
    const month = parseInt(dateStr.substring(4, 6)) - 1; // JS months are 0-indexed
    const day = parseInt(dateStr.substring(6, 8));
    const hours = parseInt(timeStr.substring(0, 2));
    const minutes = parseInt(timeStr.substring(2, 4));

    const date = new Date(year, month, day, hours, minutes);

    return {
      type: type as RequestType,
      timestamp: `${dateStr}-${timeStr}`,
      context,
      uniqueId,
      date
    };
  } catch (error) {
    return null;
  }
}

/**
 * Extracts context from itinerary for TRF request IDs
 * Uses the destination of the first itinerary segment
 * @param itinerary Array of itinerary segments
 * @returns Context string (first 3 characters of destination)
 */
export function extractContextFromItinerary(itinerary: any[]): string {
  if (itinerary && itinerary.length > 0) {
    const firstSegment = itinerary[0];
    const destination = firstSegment.to_location || firstSegment.to || firstSegment.destination || '';
    return destination.substring(0, 3).toUpperCase() || 'TRF';
  }
  return 'TRF';
}

/**
 * Extracts context from visa country
 * @param country Destination country
 * @returns Context string (first 3 characters of country)
 */
export function extractContextFromCountry(country: string): string {
  return country ? country.substring(0, 3).toUpperCase() : 'VIS';
}

/**
 * Extracts context from accommodation location
 * @param location Accommodation location
 * @returns Context string (first 3 characters of location)
 */
export function extractContextFromLocation(location: string): string {
  return location ? location.substring(0, 3).toUpperCase() : 'ACCOM';
}
