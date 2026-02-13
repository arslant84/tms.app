"""
Request ID Generator Utility

Implements unified request ID naming convention:
- General format: [TYPE]-[YYYYMMDD-HHMM]-[CONTEXT]-[UNIQUE_ID]
- Claims format: CLM-[YYYYMMDD-HHMM]-[XXXXX]-[XXXX] (no context, double unique IDs)

Examples:
- TSR: TSR-20250702-1423-NYC-PCYX
- VIS: VIS-20250702-1423-USA-5X9R
- ACCOM: ACCOM-20250702-1423-DEL-2Y8P
- CLM: CLM-20250702-1423-QWSDF-P4Z5 (5+4 character unique IDs)
- TRN: TRN-20250702-1423-LOCAL-3K8M
"""

import random
import re
from datetime import datetime
from typing import Literal, Optional, Tuple

# Valid request types
RequestType = Literal['TSR', 'VIS', 'ACCOM', 'CLM', 'TRN']

# Characters to use for unique ID generation (avoiding ambiguous characters like 0/O, 1/I)
UNIQUE_ID_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_unique_id(length: int = 4) -> str:
    """
    Generates a random string of specified length using non-ambiguous characters

    Args:
        length: Length of the unique ID to generate

    Returns:
        Random string of specified length
    """
    return ''.join(random.choice(UNIQUE_ID_CHARS) for _ in range(length))


def format_date_for_request_id(date: Optional[datetime] = None) -> str:
    """
    Formats a date as YYYYMMDD-HHMM

    Args:
        date: Date to format (defaults to current date/time)

    Returns:
        Formatted date string
    """
    if date is None:
        date = datetime.now()

    return date.strftime('%Y%m%d-%H%M')


def validate_context(context: str) -> str:
    """
    Validates a context string to ensure it meets the requirements

    Args:
        context: Context string to validate

    Returns:
        Validated context string (uppercase, no special characters)
    """
    # Remove special characters and spaces, convert to uppercase
    sanitized = re.sub(r'[^a-zA-Z0-9]', '', context).upper()

    # Limit to 5 characters max
    return sanitized[:5]


def generate_request_id(
    request_type: RequestType,
    context: str,
    date: Optional[datetime] = None
) -> str:
    """
    Generates a unified request ID according to the specified format

    Args:
        request_type: Request type (TSR, VIS, ACCOM, CLM, TRN)
        context: Context information (e.g., NYC for New York, USA for United States)
        date: Optional date to use (defaults to current date/time)

    Returns:
        Formatted request ID
    """
    timestamp = format_date_for_request_id(date)
    valid_context = validate_context(context)

    # Special handling for claims - they need XXXXX-XXXX format instead of context-unique
    if request_type == 'CLM':
        unique_id1 = generate_unique_id(5)  # 5 characters
        unique_id2 = generate_unique_id(4)  # 4 characters
        return f"{request_type}-{timestamp}-{unique_id1}-{unique_id2}"

    # For other types, use the original format
    unique_id = generate_unique_id()
    return f"{request_type}-{timestamp}-{valid_context}-{unique_id}"


def parse_request_id(request_id: str) -> Optional[dict]:
    """
    Parses a request ID into its component parts

    Args:
        request_id: Request ID to parse

    Returns:
        Dictionary containing the parsed components, or None if invalid
    """
    parts = request_id.split('-')

    # Claims have 5 parts: CLM-YYYYMMDD-HHMM-XXXXX-XXXX
    # Others have 5 parts: TYPE-YYYYMMDD-HHMM-CONTEXT-UNIQUEID
    if len(parts) != 5:
        return None

    request_type, date_str, time_str, part3, part4 = parts

    if request_type == 'CLM':
        # For claims: part3 is first unique ID, part4 is second unique ID
        context = 'CLAIM'  # Standard context for claims
        unique_id = f"{part3}-{part4}"  # Combine both unique parts
    else:
        # For other types: part3 is context, part4 is unique ID
        context = part3
        unique_id = part4

    # Validate type
    if request_type not in ['TSR', 'VIS', 'ACCOM', 'CLM', 'TRN']:
        return None

    # Parse date
    try:
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        hours = int(time_str[:2])
        minutes = int(time_str[2:4])

        date = datetime(year, month, day, hours, minutes)

        return {
            'type': request_type,
            'timestamp': f"{date_str}-{time_str}",
            'context': context,
            'unique_id': unique_id,
            'date': date
        }
    except (ValueError, IndexError):
        return None


def extract_context_from_itinerary(itinerary: list) -> str:
    """
    Extracts context from itinerary for TRF request IDs
    Uses the destination of the first itinerary segment

    Args:
        itinerary: List of itinerary segments

    Returns:
        Context string (destination will be validated and limited to 5 chars by generate_request_id)
    """
    if itinerary and len(itinerary) > 0:
        first_segment = itinerary[0]
        destination = (
            first_segment.get('to_location') or
            first_segment.get('to') or
            first_segment.get('destination') or
            ''
        )
        return destination if destination else 'TRF'
    return 'TRF'


def extract_context_from_country(country: str) -> str:
    """
    Extracts context from visa country

    Args:
        country: Destination country

    Returns:
        Context string (will be validated and limited to 5 chars by generate_request_id)
    """
    return country if country else 'VIS'


def extract_context_from_location(location: str) -> str:
    """
    Extracts context from accommodation location

    Args:
        location: Accommodation location

    Returns:
        Context string (will be validated and limited to 5 chars by generate_request_id)
    """
    return location if location else 'ACCOM'


def extract_context_from_transport(transport_details: list) -> str:
    """
    Extracts context from transport details for TRN request IDs
    Uses the destination of the first transport detail

    Args:
        transport_details: List of transport detail objects from transport_details JSON field
                          Expected format: [{'to': 'Location', 'from': '...', ...}, ...]

    Returns:
        Context string (destination will be validated and limited to 5 chars by generate_request_id)
    """
    if transport_details and len(transport_details) > 0:
        first_detail = transport_details[0]
        # Handle both formats: JSON field (to, from) and model field (to_location, from_location)
        destination = (
            first_detail.get('to') or
            first_detail.get('to_location') or
            first_detail.get('destination') or
            ''
        )
        return destination if destination else 'TRN'
    return 'TRN'
