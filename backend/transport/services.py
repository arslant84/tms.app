"""
Request-number generation for TransportRequest.
"""


def generate_unique_transport_request_number(transport_details, applicant_name) -> str:
    """
    TRN-{Destination}-{TravelDate}-{ApplicantName}-{ApplicationDate},
    unique. Destination and travel date both come from the first leg in
    transport_details (a JSON array) - there's no dedicated model field
    for either.
    """
    from django.utils import timezone
    from transport.models import TransportRequest
    from utils.request_id_generator import (
        build_transport_request_id,
        ensure_unique_request_number,
        extract_context_from_transport,
        parse_iso_date_safe,
    )

    destination = (
        extract_context_from_transport(transport_details) if transport_details else None
    )
    travel_date = (
        parse_iso_date_safe(transport_details[0].get("date"))
        if transport_details
        else None
    )
    candidate = build_transport_request_id(
        destination=destination,
        applicant_name=applicant_name,
        travel_date=travel_date,
        application_date=timezone.now(),
    )
    return ensure_unique_request_number(TransportRequest, candidate)
