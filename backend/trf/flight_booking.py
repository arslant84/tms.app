"""
Flight-booking helpers for TravelRequestViewSet.book_flight - extracted
as-is (see docs/CODEBASE_REFACTOR_ROADMAP.md item 9). These were already
small, single-purpose static/class methods on the ViewSet before this
move; converting `self._method(...)` call sites to plain module-level
function calls is the only change, no logic touched.
"""

import json
from datetime import datetime

from django.utils import timezone


def parse_flight_datetime(value):
    """Parse an ISO datetime string into an aware datetime, or None."""
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = timezone.make_aware(parsed)
    return parsed


def parse_flight_segments(raw_segments):
    """
    Parse the `segments` JSON payload for book_flight into
    (outbound, return) lists, each a list of dicts with a parsed
    `departure_time`/`arrival_time`. Raises ValueError with a
    user-facing message on any structural or field problem.
    """
    try:
        segments = json.loads(raw_segments) if raw_segments else []
    except (TypeError, ValueError):
        raise ValueError("segments must be valid JSON")
    if not isinstance(segments, list) or not segments:
        raise ValueError("At least one outbound flight segment is required")

    required_fields = [
        "direction",
        "flightNumber",
        "departureAirport",
        "arrivalAirport",
        "departureDateTime",
        "arrivalDateTime",
    ]
    outbound, return_legs = [], []
    for index, seg in enumerate(segments, start=1):
        missing = [f for f in required_fields if not seg.get(f)]
        if missing:
            raise ValueError(f"Segment {index} is missing: {', '.join(missing)}")
        if seg["direction"] not in ("OUTBOUND", "RETURN"):
            raise ValueError(f"Segment {index} has an invalid direction")
        parsed = {
            "flight_number": seg["flightNumber"],
            "departure_airport": seg["departureAirport"],
            "arrival_airport": seg["arrivalAirport"],
            "departure_time": parse_flight_datetime(seg["departureDateTime"]),
            "arrival_time": parse_flight_datetime(seg["arrivalDateTime"]),
        }
        (outbound if seg["direction"] == "OUTBOUND" else return_legs).append(parsed)

    if not outbound:
        raise ValueError("At least one outbound flight segment is required")
    return outbound, return_legs


def save_flight_segments(flight_booking, outbound, return_legs):
    """Replace a booking's segment rows with the freshly parsed legs."""
    from bookings.models import FlightBookingSegment, SegmentDirection

    flight_booking.segments.all().delete()
    rows = [
        FlightBookingSegment(
            booking=flight_booking,
            direction=SegmentDirection.OUTBOUND,
            sequence=sequence,
            **leg,
        )
        for sequence, leg in enumerate(outbound, start=1)
    ] + [
        FlightBookingSegment(
            booking=flight_booking,
            direction=SegmentDirection.RETURN,
            sequence=sequence,
            **leg,
        )
        for sequence, leg in enumerate(return_legs, start=1)
    ]
    FlightBookingSegment.objects.bulk_create(rows)


def validate_book_flight_fields(trf, pnr, airline, e_ticket, existing_booking):
    """Return a list of missing required field names (empty if valid)."""
    required = {"pnr": pnr}
    if trf.travel_type == "Overseas":
        required["airline"] = airline
    missing = [name for name, value in required.items() if not value]
    # E-ticket is required the first time a booking is created; an
    # existing booking already has one on file, so re-uploading isn't
    # forced on every edit.
    if not e_ticket and not (existing_booking and existing_booking.e_ticket):
        missing.append("eTicket")
    return missing
