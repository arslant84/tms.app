"""
Department Focal notification logic.

Department Focal is an existing approval-step Role (see
accounts/migrations/0008_populate_roles_permissions.py) that has no
per-department single-user mapping — "the" Department Focal for a request is
every active User with that Role whose own department matches the request's
department (a plain text field on TravelRequest, matched case-insensitively
against the Department Focal's User.department.name FK).
"""

import logging

logger = logging.getLogger("trf")


def find_trf_for_visa(visa):
    """
    Reverse of get_linked_visa_applications: given a VisaApplication, find
    the TravelRequest it references (if any) via the same unenforced
    trf_reference_number text match.
    """
    from trf.models import TravelRequest

    if not visa.trf_reference_number:
        return None
    return TravelRequest.objects.filter(
        request_number=visa.trf_reference_number
    ).first()


def get_linked_visa_applications(trf):
    """
    VisaApplication has no ForeignKey to TravelRequest at all — the only
    link is trf_reference_number, a free-text field matched against
    trf.request_number. Unlike transport/accommodation's real (if nullable)
    FKs, this join is unenforced: a blank/typo'd reference means a visa
    silently won't be found here. Treat this as best-effort, not authoritative.
    """
    from visa.models import VisaApplication

    if not trf.request_number:
        return VisaApplication.objects.none()
    return VisaApplication.objects.filter(trf_reference_number=trf.request_number)


def module_status_summary(trf) -> dict:
    """
    Per-module arrangement status for display — one entry per module this
    request actually needed, "Not applicable" for the rest. Powers both
    check_is_fully_arranged and the Department Focal queue's status columns.
    """
    from trf.models import TrfDailyMealSelection, TrfItinerarySegment

    summary = {}

    if TrfItinerarySegment.objects.filter(trf=trf).exists():
        # Show the real booking status (Pending/Requested/Confirmed/Ticketed)
        # rather than a flattened Pending/Ticketed binary — a TRF whose
        # own top-level status already reads "Flight Booked" can still have
        # an unticketed (e.g. Confirmed) booking underneath, and collapsing
        # that to a bare "Pending" reads as if nothing had happened yet.
        active_bookings = trf.flight_bookings.exclude(status="CANCELLED")
        if active_bookings.exists():
            not_yet_ticketed = active_bookings.exclude(status="TICKETED").first()
            representative = not_yet_ticketed or active_bookings.first()
            summary["flight"] = representative.get_status_display()
        else:
            summary["flight"] = "Not booked yet"
    else:
        summary["flight"] = "Not applicable"

    if TrfDailyMealSelection.objects.filter(trf=trf).exists():
        summary["meal"] = trf.meal_processing_status or "Pending"
    else:
        summary["meal"] = "Not applicable"

    # Transport/Accommodation/Visa's own `status` field is the same kind of
    # dynamic, workflow-driven text TransportRequest/AccommodationRequest/
    # VisaApplication use for their *own* approval process (e.g. "Pending
    # HOD", "Rejected", "Approved") before it ever reaches the terminal
    # fulfillment status checked below. Showing the real value (like the
    # Flight column above) instead of collapsing everything short of
    # "done" into a bare "Pending" means a rejection or an in-progress
    # approval is visible here, not indistinguishable from "not started".
    summary["transport"] = _representative_status(
        trf.transport_requests.all(), done_status="Completed"
    )
    summary["accommodation"] = _representative_status(
        trf.accommodation_requests.all(), done_status="Accommodation Assigned"
    )
    summary["visa"] = _representative_status(
        get_linked_visa_applications(trf), done_status="Completed"
    )

    return summary


def _representative_status(queryset, done_status):
    """
    "Not applicable" if queryset is empty; otherwise the status of the
    first not-yet-done record (so a rejection or in-progress approval is
    visible), or done_status itself once every record has reached it.
    """
    if not queryset.exists():
        return "Not applicable"
    not_done = queryset.exclude(status=done_status).first()
    return not_done.status if not_done else done_status


def check_is_fully_arranged(trf) -> bool:
    """
    True once every downstream arrangement this specific request actually
    needed is complete. Each module is only checked if the request actually
    has something in it for that module — a request with no meal selections,
    for example, doesn't need meal_processing_status to be anything.
    """
    summary = module_status_summary(trf)
    done_values = {"Not applicable", "Ticketed", "Completed", "Accommodation Assigned"}
    return all(value in done_values for value in summary.values())


def notify_department_focal_if_ready(trf) -> None:
    """
    Best-effort: notify every Department Focal for trf's department once all
    of its arrangements are complete. Safe to call from any of the four
    completion touchpoints (flight ticketing, meal status update, transport
    complete, accommodation assign) — a no-op if already notified or not yet
    fully arranged.
    """
    if trf.department_focal_notified:
        return

    if not check_is_fully_arranged(trf):
        return

    try:
        from accounts.models import User
        from notifications.services import NotificationService

        focals = User.objects.filter(
            role__name="Department Focal",
            department__name__iexact=(trf.department or "").strip(),
            is_active=True,
        )
        for focal in focals:
            NotificationService.create_notification(
                user=focal,
                title=f"Travel arrangements completed — {trf.request_number}",
                message=(
                    f"All travel arrangements for {trf.requestor_name}'s "
                    f"request {trf.request_number} are now complete."
                ),
                action_url=f"/trf/{trf.id}",
                content_object=trf,
                send_email=True,
            )
    except Exception:
        logger.exception("Failed to notify Department Focal for TRF #%s", trf.id)
        return

    trf.department_focal_notified = True
    trf.save(update_fields=["department_focal_notified"])
