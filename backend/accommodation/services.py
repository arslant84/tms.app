"""
Shared business logic for AccommodationRequestViewSet: request-number
generation, workflow-start (Phase 3), and approve/reject/assign
(Phase 4) - all previously duplicated or inline in the view.

Split out of accommodation_request_views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 6). The workflow-start logic
(`start_accommodation_workflow`) was byte-for-byte identical across all
three Phase 3 call sites, so it moved as a pure extraction. The
request-number generation had two genuinely different strategies across
call sites (perform_create/perform_update resolve the location through
`extract_context_from_location`; `submit` used the raw location string
as context and had its own exception fallback format) - these are kept
as two separate functions rather than forced into one, to avoid
silently changing which strategy either caller uses. The only actual
behavior change made in Phase 3 was unifying the three call sites'
slightly different log message wording (purely diagnostic text, not
observable via the API) into one consistent message.

Phase 4's `process_accommodation_approval_action` merges `approve`/
`reject`, which were *not* byte-for-byte identical: `reject` had no
explicit error response when a workflow instance existed but no
pending step was found (an existing gap, not introduced here - falls
through and returns None, exactly like the original), and `approve`
logged a warning before its legacy-fallback permission check that
`reject` never did. Both quirks are preserved exactly via the
`is_approve` branches below, not "fixed", since this is a behavior-
preserving extraction.
"""

import logging
from datetime import timedelta

from accounts.models import AdminActionLog
from accounts.utils import can_approve
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from utils.request_id_generator import (
    extract_context_from_location,
    generate_request_id,
)
from workflows.engine import WorkflowEngine
from workflows.models import WorkflowInstance
from workflows.router import WorkflowRouter

from .serializers import AccommodationRequestSerializer

logger = logging.getLogger(__name__)


def generate_accommodation_request_number(additional_data):
    """
    Generate a request number from `additional_data.location`, resolved
    through `extract_context_from_location`. Used by perform_create/
    perform_update. Returns None (and logs) on failure, matching those
    call sites' "will be generated later if needed" behavior - the
    caller simply doesn't set request_number in that case.
    """
    try:
        location = (
            additional_data.get("location", "")
            if isinstance(additional_data, dict)
            else ""
        )
        context = extract_context_from_location(location) if location else "ACCOM"
        request_number = generate_request_id("ACCOM", context)
        logger.info(f" Generated request number: {request_number}")
        return request_number
    except Exception as e:
        logger.error(f" Error generating request number: {str(e)}")
        return None


def generate_accommodation_request_number_with_fallback(accommodation_request):
    """
    Generate a request number for the `submit` action, using the raw
    `additional_data.location` string as context (not resolved through
    `extract_context_from_location`, unlike
    `generate_accommodation_request_number` above - this is a real
    pre-existing difference between the two call sites, preserved as-is).
    Always returns a string: falls back to a simple timestamp-based
    format on any failure, rather than leaving request_number unset.
    """
    try:
        context = "ACCOM"
        if accommodation_request.additional_data and isinstance(
            accommodation_request.additional_data, dict
        ):
            location = accommodation_request.additional_data.get("location", "")
            if location:
                context = location

        logger.debug(
            f" Extracted context for Accommodation Request #{accommodation_request.id}: {context}"
        )
        request_number = generate_request_id("ACCOM", context)
        logger.info(f" Generated request number: {request_number}")
        return request_number
    except Exception as e:
        logger.error(f" Error generating request number: {str(e)}")
        import traceback

        traceback.print_exc()
        from datetime import datetime

        fallback = f"ACCOM-{datetime.now().strftime('%Y%m%d-%H%M')}-ACCOM-{accommodation_request.id}"
        logger.warning(f" Using fallback request number: {fallback}")
        return fallback


def start_accommodation_workflow(accommodation_request, request_data, initiated_by):
    """
    Start the approval workflow for an accommodation request. Shared by
    perform_create, perform_update, and the submit action - identical
    logic in all three, so this is a pure extraction with only the log
    message wording unified across the three (previously slightly
    different phrasing per call site).
    """
    selected_approvers = request_data.get("selected_approvers", None)
    if selected_approvers:
        selected_approvers = {int(k): v for k, v in selected_approvers.items()}

    skipped_steps = request_data.get("skipped_steps", None)
    if skipped_steps:
        skipped_steps = {int(k): v for k, v in skipped_steps.items()}

    try:
        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=accommodation_request,
            entity_type="accommodation",
            initiated_by=initiated_by,
            selected_approvers=selected_approvers,
            skipped_steps=skipped_steps,
        )

        if workflow_instance:
            accommodation_request.refresh_from_db()
            logger.info(
                f" Workflow started for Accommodation Request #{accommodation_request.id}: Workflow Instance #{workflow_instance.id}"
            )
            logger.info(f" Status updated to: {accommodation_request.status}")
        else:
            logger.warning(
                " No active workflow configured for accommodation - using legacy approval system"
            )
    except Exception as e:
        logger.error(
            f" Error starting workflow for Accommodation Request #{accommodation_request.id}: {str(e)}"
        )
        # Don't fail the caller (create/update/submit) if workflow start fails


def process_accommodation_approval_action(
    accommodation_request, request, action, comments
):
    """
    Approve or reject an accommodation request: dispatch to the active
    WorkflowInstance if one exists, else fall back to the legacy manual
    approval-step flow. `action` is "approve" or "reject". `request` is
    the DRF request (not just its `.user`) since the legacy-fallback
    AdminActionLog entry records the request's IP/user agent, same as
    the original inline actions did.

    Returns `(response_data, http_status)` for the caller to wrap in a
    DRF Response, or `None` in the one case where the original `reject`
    action had no explicit response (see module docstring) - callers
    must handle that `None` the same way the original inline action did.
    """
    user = request.user
    is_approve = action == "approve"
    target_status = "Approved" if is_approve else "Rejected"
    admin_action_type = (
        "workflow_step_approved" if is_approve else "workflow_step_rejected"
    )
    action_noun = "approval" if is_approve else "rejection"

    try:
        content_type = ContentType.objects.get_for_model(accommodation_request)
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type,
            object_id=accommodation_request.id,
            status="in_progress",
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
                    actioned_by=user,
                    comments=comments,
                )
                accommodation_request.refresh_from_db()
                return (
                    AccommodationRequestSerializer(accommodation_request).data,
                    200,
                )
            elif is_approve:
                return ({"error": "No pending approval step found"}, 400)
            else:
                # reject: no explicit response here in the original action
                # (falls through and implicitly returns None) - preserved
                # as-is, not fixed, per the module docstring.
                return None
        else:
            # Fallback to legacy approval/rejection logic
            if not (user.is_superuser or can_approve(user, "accommodation")):
                return (
                    {
                        "error": f"You do not have permission to {action} accommodation requests"
                    },
                    403,
                )

            if is_approve:
                logger.warning(
                    f" No workflow instance found for Accommodation #{accommodation_request.id}, using legacy approval"
                )

            if accommodation_request.status not in [
                "Pending",
                "Pending Department Focal",
                "Pending HOD",
            ]:
                return (
                    {"error": f"Cannot {action} request with current status"},
                    400,
                )

            accommodation_request.status = target_status
            accommodation_request.save()

            AdminActionLog.log_action(
                user=user,
                action_type=admin_action_type,
                description=(
                    f"{target_status} accommodation request #{accommodation_request.id} "
                    "(legacy fallback - no active WorkflowTemplate)"
                ),
                entity_type="accommodation",
                entity_id=accommodation_request.id,
                request=request,
            )

            return (AccommodationRequestSerializer(accommodation_request).data, 200)

    except Exception as e:
        logger.error(f" Error in {action} workflow: {str(e)}")
        import traceback

        traceback.print_exc()
        return ({"error": f"Failed to process {action_noun}: {str(e)}"}, 500)


def assign_accommodation(
    accommodation_request,
    staff_house_id,
    room_id,
    start_date_str,
    end_date_str,
    notes,
    assigned_room_info,
    actioned_by,
):
    """
    Assign accommodation to a request and create daily booking records,
    one per night in [start_date, end_date]. Validates the date range,
    checks the room isn't already booked on any of those nights, then
    creates the bookings and marks the request "Accommodation Assigned".
    Also completes the workflow's "Accommodation Admin" step if an
    in-progress WorkflowInstance exists (best-effort - failure here
    doesn't roll back the assignment).

    Returns `(response_data, http_status)` for the caller to wrap in a
    DRF Response.
    """
    from datetime import datetime

    from .models import AccommodationBooking, AccommodationRoom, AccommodationStaffHouse

    if not all([staff_house_id, room_id, start_date_str, end_date_str]):
        return (
            {"error": "staff_house, room, start_date, and end_date are required"},
            400,
        )

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError as e:
        return ({"error": f"Invalid date format. Use YYYY-MM-DD: {str(e)}"}, 400)

    if end_date < start_date:
        return (
            {"error": "end_date must be greater than or equal to start_date"},
            400,
        )

    try:
        staff_house = AccommodationStaffHouse.objects.get(id=staff_house_id)
        room = AccommodationRoom.objects.get(id=room_id, staff_house=staff_house)
    except AccommodationStaffHouse.DoesNotExist:
        return ({"error": f"Staff house with id {staff_house_id} not found"}, 404)
    except AccommodationRoom.DoesNotExist:
        return (
            {
                "error": f"Room with id {room_id} not found in staff house {staff_house_id}"
            },
            404,
        )

    # Check for existing bookings in the date range
    current_date = start_date
    conflicting_dates = []
    while current_date <= end_date:
        existing_booking = AccommodationBooking.objects.filter(
            room=room, date=current_date, status__in=["Confirmed", "Pending"]
        ).first()

        if existing_booking:
            conflicting_dates.append(current_date.strftime("%Y-%m-%d"))

        current_date += timedelta(days=1)

    if conflicting_dates:
        return (
            {
                "error": "Room is already booked for the following dates",
                "conflicting_dates": conflicting_dates,
            },
            409,
        )

    # Delete any existing bookings for this request (in case of reassignment)
    AccommodationBooking.objects.filter(
        accommodation_request=accommodation_request
    ).delete()

    # Create daily booking records
    created_bookings = []
    current_date = start_date

    try:
        while current_date <= end_date:
            booking = AccommodationBooking.objects.create(
                staff_house=staff_house,
                room=room,
                accommodation_request=accommodation_request,
                date=current_date,
                trf=accommodation_request.trf,
                status="Confirmed",
                notes=notes or f"TRF Assignment: {assigned_room_info}",
            )
            created_bookings.append(booking)
            current_date += timedelta(days=1)

        # Update accommodation request status
        accommodation_request.status = "Accommodation Assigned"

        # Update additional_comments with assignment info
        if accommodation_request.additional_comments:
            accommodation_request.additional_comments += f"\n\n{assigned_room_info}"
        else:
            accommodation_request.additional_comments = assigned_room_info

        accommodation_request.save()

        # Add workflow step execution if workflow is active
        try:
            from workflows.models import StepExecution, WorkflowStep

            content_type = ContentType.objects.get_for_model(accommodation_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=accommodation_request.id,
                status="in_progress",
            ).first()

            if workflow_instance:
                accommodation_step = WorkflowStep.objects.filter(
                    workflow_definition=workflow_instance.workflow_definition,
                    step_name="Accommodation Admin",
                ).first()

                if accommodation_step:
                    StepExecution.objects.create(
                        workflow_instance=workflow_instance,
                        workflow_step=accommodation_step,
                        assigned_role=actioned_by.role,
                        status="completed",
                        action_taken="assign",
                        actioned_by=actioned_by,
                        actioned_at=timezone.now(),
                        comments=f"Assigned: {assigned_room_info}",
                    )

                    workflow_instance.status = "completed"
                    workflow_instance.completed_at = timezone.now()
                    workflow_instance.save()
        except Exception as e:
            logger.warning(f" Could not add workflow step execution: {str(e)}")
            # Don't fail the assignment if workflow update fails

        return (
            {
                "message": f"Accommodation assigned successfully. Created {len(created_bookings)} booking records.",
                "bookings_created": len(created_bookings),
                "date_range": f"{start_date_str} to {end_date_str}",
                "accommodation_request": AccommodationRequestSerializer(
                    accommodation_request
                ).data,
            },
            200,
        )

    except Exception as e:
        # Rollback: delete any created bookings
        for booking in created_bookings:
            booking.delete()

        logger.error(f" Error creating booking records: {str(e)}")
        import traceback

        traceback.print_exc()

        return ({"error": f"Failed to create booking records: {str(e)}"}, 500)
