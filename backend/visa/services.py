"""
Request-number generation for VisaApplication.
"""


def generate_unique_visa_request_number(
    destination, trip_start_date, applicant_name
) -> str:
    """
    VIS-{Destination}-{TripStartDate}-{ApplicantName}-{ApplicationDate},
    unique. Takes explicit fields rather than a VisaApplication instance
    since one call site (VisaApplicationViewSet.perform_create) runs
    before the application is saved, working from serializer.
    validated_data instead.
    """
    from django.utils import timezone
    from utils.request_id_generator import (
        build_visa_request_id,
        ensure_unique_request_number,
    )
    from visa.models import VisaApplication

    candidate = build_visa_request_id(
        destination=destination,
        trip_start_date=trip_start_date,
        applicant_name=applicant_name,
        application_date=timezone.now(),
    )
    return ensure_unique_request_number(VisaApplication, candidate)
