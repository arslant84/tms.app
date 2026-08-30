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
RequestType = Literal["TSR", "VIS", "ACCOM", "CLM", "TRN"]

# Characters to use for unique ID generation (avoiding ambiguous characters like 0/O, 1/I)
UNIQUE_ID_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_unique_id(length: int = 4) -> str:
    """
    Generates a random string of specified length using non-ambiguous characters

    Args:
        length: Length of the unique ID to generate

    Returns:
        Random string of specified length
    """
    return "".join(random.choice(UNIQUE_ID_CHARS) for _ in range(length))


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

    return date.strftime("%Y%m%d-%H%M")


def validate_context(context: str) -> str:
    """
    Validates a context string to ensure it meets the requirements

    Args:
        context: Context string to validate

    Returns:
        Validated context string (uppercase, no special characters)
    """
    # Remove special characters and spaces, convert to uppercase
    sanitized = re.sub(r"[^a-zA-Z0-9]", "", context).upper()

    # Limit to 5 characters max
    return sanitized[:5]


def generate_request_id(
    request_type: RequestType, context: str, date: Optional[datetime] = None
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
    if request_type == "CLM":
        unique_id1 = generate_unique_id(5)  # 5 characters
        unique_id2 = generate_unique_id(4)  # 4 characters
        return f"{request_type}-{timestamp}-{unique_id1}-{unique_id2}"

    # For other types, use the original format
    unique_id = generate_unique_id()
    return f"{request_type}-{timestamp}-{valid_context}-{unique_id}"


TSR_TYPE_CODES = {
    "Domestic": "DOM",
    "Overseas": "OVS",
    "Home Leave": "HL",
    "External Parties": "EXT",
}


def parse_iso_date_safe(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a "YYYY-MM-DD" string (the format frontend forms send dates in
    JSON fields as, e.g. accommodation's additional_data or transport's
    transport_details) into a datetime. Returns None on anything
    malformed or missing, rather than raising - a bad/absent date should
    degrade to omitting that ID segment, not fail the whole request.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def sanitize_name_for_request_id(name: str, max_length: int = 20) -> str:
    """
    Strip a person's name down to alphanumeric characters only (no spaces,
    punctuation, etc.) and cap its length, for embedding in a request ID
    that's later split/read by "-" separators.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9]", "", name or "")
    return sanitized[:max_length] or "APPLICANT"


def sanitize_context_for_request_id(context: str, max_length: int = 12) -> str:
    """
    Same idea as sanitize_name_for_request_id, but for a destination/
    location segment (e.g. "Kuala Lumpur" -> "KUALALUMPUR") - uppercase,
    since these read as place/category codes rather than names.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9]", "", context or "").upper()
    return sanitized[:max_length]


def build_named_request_id(
    prefix: str,
    applicant_name: str,
    context: Optional[str] = None,
    date_segment: Optional[datetime] = None,
    application_date: Optional[datetime] = None,
) -> str:
    """
    Shared builder for the "readable" request ID style requested to replace
    the old TYPE-timestamp-context-random scheme (generate_request_id
    above) for TSR/VIS/ACCOM/TRN: {PREFIX}-{Context?}-{Date?}-
    {ApplicantName}-{ApplicationDate}. Context and date_segment are
    genuinely optional per module (e.g. accommodation/transport have no
    structured date field to draw on) - an omitted segment is left out
    entirely rather than padded with a placeholder, so the ID doesn't
    imply data that doesn't exist.

    Returns the base candidate only - does not check uniqueness. Callers
    must handle collisions themselves via ensure_unique_request_number,
    since this module has no database access.
    """
    parts = [prefix]
    if context:
        sanitized_context = sanitize_context_for_request_id(context)
        if sanitized_context:
            parts.append(sanitized_context)
    if date_segment:
        parts.append(date_segment.strftime("%Y%m%d"))
    parts.append(sanitize_name_for_request_id(applicant_name))
    app_date = application_date or datetime.now()
    parts.append(app_date.strftime("%Y%m%d"))
    return "-".join(parts)


def ensure_unique_request_number(
    model_cls, candidate: str, field_name: str = "request_number"
) -> str:
    """
    Append -2, -3, ... to candidate only if it already exists, so the
    common case produces exactly the requested format and collisions
    (e.g. the same applicant resubmitting the same trip same-day) never
    fail a save with a uniqueness IntegrityError.
    """
    if not model_cls.objects.filter(**{field_name: candidate}).exists():
        return candidate

    suffix = 2
    while True:
        next_candidate = f"{candidate}-{suffix}"
        if not model_cls.objects.filter(**{field_name: next_candidate}).exists():
            return next_candidate
        suffix += 1


def build_tsr_request_id(
    travel_type: str,
    flight_date: Optional[datetime],
    applicant_name: str,
    application_date: Optional[datetime] = None,
) -> str:
    """TSR-{TypeCode}-{FlightDate}-{ApplicantName}-{ApplicationDate}.
    Unlike the other three builders, the type code is always present
    (travel_type is always known at submit time), so it's built directly
    rather than through the generic optional-context path."""
    type_code = TSR_TYPE_CODES.get(travel_type, "TRF")
    parts = ["TSR", type_code]
    if flight_date:
        parts.append(flight_date.strftime("%Y%m%d"))
    parts.append(sanitize_name_for_request_id(applicant_name))
    app_date = application_date or datetime.now()
    parts.append(app_date.strftime("%Y%m%d"))
    return "-".join(parts)


def build_visa_request_id(
    destination: Optional[str],
    trip_start_date: Optional[datetime],
    applicant_name: str,
    application_date: Optional[datetime] = None,
) -> str:
    """VIS-{Destination}-{TripStartDate}-{ApplicantName}-{ApplicationDate}."""
    return build_named_request_id(
        "VIS",
        applicant_name,
        context=destination,
        date_segment=trip_start_date,
        application_date=application_date,
    )


def build_accommodation_request_id(
    location: Optional[str],
    applicant_name: str,
    check_in_date: Optional[datetime] = None,
    application_date: Optional[datetime] = None,
) -> str:
    """ACCOM-{Location}-{CheckInDate}-{ApplicantName}-{ApplicationDate}.
    check_in_date has no dedicated model field - callers pull it from
    additional_data['requested_check_in_date'] (a string, so parsing
    happens at the call site, not here)."""
    return build_named_request_id(
        "ACCOM",
        applicant_name,
        context=location,
        date_segment=check_in_date,
        application_date=application_date,
    )


def build_transport_request_id(
    destination: Optional[str],
    applicant_name: str,
    travel_date: Optional[datetime] = None,
    application_date: Optional[datetime] = None,
) -> str:
    """TRN-{Destination}-{TravelDate}-{ApplicantName}-{ApplicationDate}.
    travel_date has no dedicated model field - callers pull it from
    transport_details[0]['date'] (a string, so parsing happens at the
    call site, not here)."""
    return build_named_request_id(
        "TRN",
        applicant_name,
        context=destination,
        date_segment=travel_date,
        application_date=application_date,
    )


def parse_request_id(request_id: str) -> Optional[dict]:
    """
    Parses a request ID into its component parts

    Args:
        request_id: Request ID to parse

    Returns:
        Dictionary containing the parsed components, or None if invalid
    """
    parts = request_id.split("-")

    # Claims have 5 parts: CLM-YYYYMMDD-HHMM-XXXXX-XXXX
    # Others have 5 parts: TYPE-YYYYMMDD-HHMM-CONTEXT-UNIQUEID
    if len(parts) != 5:
        return None

    request_type, date_str, time_str, part3, part4 = parts

    if request_type == "CLM":
        # For claims: part3 is first unique ID, part4 is second unique ID
        context = "CLAIM"  # Standard context for claims
        unique_id = f"{part3}-{part4}"  # Combine both unique parts
    else:
        # For other types: part3 is context, part4 is unique ID
        context = part3
        unique_id = part4

    # Validate type
    if request_type not in ["TSR", "VIS", "ACCOM", "CLM", "TRN"]:
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
            "type": request_type,
            "timestamp": f"{date_str}-{time_str}",
            "context": context,
            "unique_id": unique_id,
            "date": date,
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
            first_segment.get("to_location")
            or first_segment.get("to")
            or first_segment.get("destination")
            or ""
        )
        return destination if destination else "TRF"
    return "TRF"


def extract_context_from_country(country: str) -> str:
    """
    Extracts context from visa country

    Args:
        country: Destination country

    Returns:
        Context string (will be validated and limited to 5 chars by generate_request_id)
    """
    return country if country else "VIS"


def extract_context_from_location(location: str) -> str:
    """
    Extracts context from accommodation location

    Args:
        location: Accommodation location

    Returns:
        Context string (will be validated and limited to 5 chars by generate_request_id)
    """
    return location if location else "ACCOM"


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
            first_detail.get("to")
            or first_detail.get("to_location")
            or first_detail.get("destination")
            or ""
        )
        return destination if destination else "TRN"
    return "TRN"
