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


def generate_unique_tsr_request_number(trf) -> str:
    """
    TSR-{TypeCode}-{FlightDate}-{ApplicantName}-{ApplicationDate}, unique
    per accounts. FlightDate is the earliest itinerary segment's date (a
    TRF may span several legs, e.g. an onward + return flight - the first
    one is what's meaningful for "when does this trip start" searches).
    ApplicantName is external_full_name for External Parties travel (that
    travel_type has no employee requestor_name), requestor_name otherwise.
    """
    from django.utils import timezone
    from trf.models import TrfItinerarySegment
    from utils.request_id_generator import (
        build_tsr_request_id,
        ensure_unique_request_number,
    )

    first_segment = (
        TrfItinerarySegment.objects.filter(trf=trf, segment_date__isnull=False)
        .order_by("segment_date")
        .first()
    )
    flight_date = first_segment.segment_date if first_segment else None

    applicant_name = (
        trf.external_full_name
        if trf.travel_type == "External Parties"
        else trf.requestor_name
    )

    candidate = build_tsr_request_id(
        travel_type=trf.travel_type,
        flight_date=flight_date,
        applicant_name=applicant_name,
        application_date=timezone.now(),
    )
    from trf.models import TravelRequest

    return ensure_unique_request_number(TravelRequest, candidate)


def start_trf_workflow(trf, request_data, initiated_by):
    """
    Start the approval workflow for a TRF. Shared by perform_create and
    the submit action (only two call sites here, not three - TravelRequestViewSet
    has no perform_update override) - identical WorkflowRouter call +
    selected_approvers/skipped_steps parsing. Callers keep their own
    exception-handling/fallback-to-legacy-approval-step behavior, since
    submit's fallback (creating a TrfApprovalStep) has no equivalent in
    perform_create.
    """
    from workflows.router import WorkflowRouter

    selected_approvers = request_data.get("selected_approvers", None)
    if selected_approvers:
        selected_approvers = {int(k): v for k, v in selected_approvers.items()}

    skipped_steps = request_data.get("skipped_steps", None)
    if skipped_steps:
        skipped_steps = {int(k): v for k, v in skipped_steps.items()}

    workflow_instance = WorkflowRouter.start_workflow_for_request(
        entity=trf,
        entity_type=trf.workflow_entity_type,
        initiated_by=initiated_by,
        selected_approvers=selected_approvers,
        skipped_steps=skipped_steps,
        fallback_entity_type="travelrequest",
    )

    if workflow_instance:
        trf.refresh_from_db()
        logger.info(
            f" Workflow started for TRF #{trf.id}: Workflow Instance #{workflow_instance.id}"
        )
        logger.info(f" Status updated to: {trf.status}")
    else:
        logger.warning(
            " No active workflow configured for travelrequest - using legacy approval system"
        )

    return workflow_instance


def process_trf_approval_action(trf, request, action, step_role, comments):
    """
    Approve or reject a TRF at its current approval step: dispatch to the
    active WorkflowInstance if one exists (syncing a legacy TrfApprovalStep
    row alongside it, keyed by `step_role` via get_or_create - same
    mechanics as visa's legacy sync), else fall back to the legacy manual
    approval-step flow. `action` is "approve" or "reject".

    Returns a DRF Response directly (unlike accommodation/transport/visa's
    equivalents, which return a (data, status) tuple for the view to wrap)
    since every TRF response here already goes through this project's
    utils.api_response helpers, which build Response objects themselves.

    Preserves two real asymmetries between approve and reject rather than
    forcing them into one shape:
    - reject's WorkflowInstance-found-but-no-pending-step case returns an
      explicit 400 (unlike accommodation/transport/visa's reject, which
      silently falls through) - TRF's original reject already had this
      explicit branch, so it's kept, not "fixed" to match the others.
    - only approve's legacy-fallback branch creates the *next* pending
      TrfApprovalStep via the status-progression map; reject's legacy
      fallback has no equivalent (it just sets "Rejected" and stops) -
      and only approve distinguishes a WorkflowEngine ValueError
      (authorization failure) into its own 400 response; reject folds a
      ValueError into the same generic 500 handler as any other exception,
      exactly as the original two actions did.
    """
    from datetime import datetime

    from accounts.models import AdminActionLog
    from accounts.utils import can_approve
    from django.contrib.contenttypes.models import ContentType
    from django.utils import timezone
    from utils.api_response import (
        error_response,
        forbidden_response,
        server_error_response,
        success_response,
    )
    from workflows.engine import WorkflowEngine
    from workflows.models import WorkflowInstance

    from .models import TrfApprovalStep
    from .serializers import TravelRequestDetailSerializer

    is_approve = action == "approve"
    target_status = "Approved" if is_approve else "Rejected"
    verb = "approved" if is_approve else "rejected"

    try:
        content_type = ContentType.objects.get_for_model(trf)
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type, object_id=trf.id, status="in_progress"
        ).first()

        if workflow_instance:
            current_step = (
                workflow_instance.step_executions.filter(status="pending")
                .order_by("workflow_step__step_order")
                .first()
            )

            if current_step:
                WorkflowEngine.process_action(
                    step_execution_id=current_step.id,
                    action=action,
                    actioned_by=request.user,
                    comments=comments,
                )
                trf.refresh_from_db()

                approval_step, created = TrfApprovalStep.objects.get_or_create(
                    trf=trf,
                    step_role=step_role,
                    defaults={
                        "step_name": f"{step_role} Approval",
                        "status": "Pending",
                    },
                )
                approval_step.status = target_status
                approval_step.comments = comments
                approval_step.step_date = timezone.now()
                approval_step.save()

                trf_serializer = TravelRequestDetailSerializer(trf)
                return success_response(
                    data=trf_serializer.data,
                    message=f"Travel request {verb} successfully",
                    status_code=200,
                )
            else:
                return error_response(
                    message=(
                        "No pending approval step found for this role"
                        if is_approve
                        else "No pending approval step found"
                    ),
                    status_code=400,
                )
        else:
            # Fallback to legacy manual approval/rejection if no workflow found
            if not (request.user.is_superuser or can_approve(request.user, "trf")):
                return forbidden_response(
                    message=f"You do not have permission to {action} travel requests"
                )

            logger.warning(
                f" No workflow instance found for TRF #{trf.id}, using legacy "
                + ("approval" if is_approve else "rejection")
            )

            approval_step, created = TrfApprovalStep.objects.get_or_create(
                trf=trf,
                step_role=step_role,
                defaults={
                    "step_name": f"{step_role} Approval",
                    "status": "Pending",
                },
            )
            approval_step.status = target_status
            approval_step.comments = comments
            approval_step.step_date = datetime.now()
            approval_step.save()

            if is_approve:
                # Update TRF status based on approval workflow. Only real
                # roles that exist in this system's active workflow
                # templates (Department Focal, Line Manager, HOD) - "Travel
                # Desk" and "Finance" were never real roles here and never
                # matched any active TSR workflow step.
                status_progression = {
                    "Department Focal": "Pending HOD",
                    "Line Manager": "Pending HOD",
                    "HOD": "Approved",
                }
                if step_role in status_progression:
                    trf.status = status_progression[step_role]
                    trf.save()

                    # Create next approval step if not final
                    if trf.status != "Approved":
                        next_role = trf.status.replace("Pending ", "")
                        TrfApprovalStep.objects.get_or_create(
                            trf=trf,
                            step_role=next_role,
                            defaults={
                                "step_name": f"{next_role} Review",
                                "status": "Pending",
                            },
                        )
            else:
                trf.status = "Rejected"
                trf.save()

            AdminActionLog.log_action(
                user=request.user,
                action_type=f"workflow_step_{verb}",
                description=(
                    f"{target_status} TRF #{trf.id} at step '{step_role}' "
                    "(legacy fallback - no active WorkflowTemplate)"
                ),
                entity_type="travelrequest",
                entity_id=trf.id,
                request=request,
            )

            trf_serializer = TravelRequestDetailSerializer(trf)
            return success_response(
                data=trf_serializer.data,
                message=f"Travel request {verb} successfully",
                status_code=200,
            )

    except ValueError as e:
        if is_approve:
            # ValueError is raised by WorkflowEngine for authorization
            # failures - only approve's original action distinguished
            # this into its own 400; reject's original action let it fall
            # into the generic Exception handler below (preserved as-is).
            logger.error(f" ValueError in approve workflow: {str(e)}")
            return error_response(message=str(e), status_code=400)
        logger.error(f" Error in reject workflow: {str(e)}")
        import traceback

        traceback.print_exc()
        return server_error_response(
            message="Failed to process rejection", error_details=str(e)
        )
    except Exception as e:
        logger.error(f" Error in {action} workflow: {str(e)}")
        import traceback

        traceback.print_exc()
        return server_error_response(
            message=f"Failed to process {'approval' if is_approve else 'rejection'}",
            error_details=str(e),
        )


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
    Best-effort: notify trf's department's Department Focal(s) once all of
    its arrangements are complete. Safe to call from any of the four
    completion touchpoints (flight ticketing, meal status update, transport
    complete, accommodation assign) — a no-op if already notified or not yet
    fully arranged.

    Fires the 'fully_arranged' workflow event through the same
    admin-configurable notification dispatch every other event in the app
    uses (see workflows/notification_dispatch.py's trigger_configured_notifications
    and its 'department_focal' recipient type) - who gets notified, the
    email wording, and whether this is even active at all are editable via
    the Notification Config screen (per workflow template's final step),
    not hardcoded here. This function's only remaining job is the "is it
    actually fully arranged yet" check and once-only gating - genuine
    business logic, not something that belongs in a config screen.
    """
    if trf.department_focal_notified:
        return

    if not check_is_fully_arranged(trf):
        return

    try:
        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance
        from workflows.notification_dispatch import trigger_configured_notifications

        content_type = ContentType.objects.get_for_model(trf)
        workflow_instance = (
            WorkflowInstance.objects.filter(content_type=content_type, object_id=trf.id)
            .order_by("-started_at")
            .first()
        )
        step_execution = (
            workflow_instance.step_executions.order_by(
                "-workflow_step__step_order"
            ).first()
            if workflow_instance
            else None
        )
        if not step_execution:
            logger.warning(
                "No workflow step execution found for TRF #%s - cannot fire "
                "'fully_arranged' notification",
                trf.id,
            )
            return

        trigger_configured_notifications(step_execution, "fully_arranged")
    except Exception:
        logger.exception("Failed to notify Department Focal for TRF #%s", trf.id)
        return

    trf.department_focal_notified = True
    trf.save(update_fields=["department_focal_notified"])
