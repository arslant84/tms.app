"""
Shared business logic for TransportRequestViewSet: request-number
generation, workflow-start, and approve/reject dispatch - previously
duplicated or inline in the view (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 7).
"""

import logging

logger = logging.getLogger(__name__)


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


def start_transport_workflow(transport_request, request_data, initiated_by):
    """
    Start the approval workflow for a transport request. Shared by
    perform_create, perform_update, and the submit action - identical
    WorkflowRouter call + selected_approvers/skipped_steps parsing
    previously copy-pasted three times. Callers are responsible for the
    trf_id/TSR-embedded guard (skip calling this entirely when the
    request rides on a parent TSR's own approval) since that check
    differs slightly in shape across the three call sites.

    Unlike accommodation's equivalent, this does not swallow
    WorkflowRouter exceptions itself - each of the three original call
    sites had its own slightly different fallback-on-error behavior
    (legacy TransportApprovalStep creation in `submit`, silent pass in
    perform_create/perform_update), so that decision stays with the
    caller rather than being collapsed here.
    """
    from workflows.router import WorkflowRouter

    selected_approvers = request_data.get("selected_approvers", None)
    if selected_approvers:
        selected_approvers = {int(k): v for k, v in selected_approvers.items()}

    skipped_steps = request_data.get("skipped_steps", None)
    if skipped_steps:
        skipped_steps = {int(k): v for k, v in skipped_steps.items()}

    workflow_instance = WorkflowRouter.start_workflow_for_request(
        entity=transport_request,
        entity_type="transportrequest",
        initiated_by=initiated_by,
        selected_approvers=selected_approvers,
        skipped_steps=skipped_steps,
    )

    if workflow_instance:
        transport_request.refresh_from_db()
        logger.info(
            f" Workflow started for Transport Request #{transport_request.id}: Workflow Instance #{workflow_instance.id}"
        )
        logger.info(f" Status updated to: {transport_request.status}")
    else:
        logger.warning(" No active workflow configured for transportrequest")

    return workflow_instance


def process_transport_approval_action(transport_request, request, action, comments):
    """
    Approve or reject a transport request: dispatch to the active
    WorkflowInstance if one exists (syncing the legacy
    TransportApprovalStep row's status alongside it, for any UI still
    reading that model directly), else fall back to the legacy manual
    approval-step flow. `action` is "approve" or "reject".

    The two legacy-fallback branches are genuinely different (approve
    validates a pending step exists and advances status via a role-keyed
    progression map; reject has no such validation and unconditionally
    sets "Rejected") - preserved exactly as two branches rather than
    forced into one shared shape, to avoid changing either's behavior.

    Returns `(response_data, http_status)` for the caller to wrap in a
    DRF Response, or `None` in the one case where the original `reject`
    action had no explicit response (workflow instance found, but no
    pending step execution) - callers must handle that `None` the same
    way the original inline action did.
    """
    from accounts.models import AdminActionLog
    from accounts.utils import can_approve
    from django.contrib.contenttypes.models import ContentType
    from django.utils import timezone
    from workflows.engine import WorkflowEngine
    from workflows.models import WorkflowInstance

    from .serializers import TransportRequestDetailSerializer

    user = request.user
    is_approve = action == "approve"

    try:
        content_type = ContentType.objects.get_for_model(transport_request)
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type,
            object_id=transport_request.id,
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
                transport_request.refresh_from_db()

                legacy_step = transport_request.approval_steps.filter(
                    status="Pending"
                ).first()
                if legacy_step:
                    legacy_step.status = "Approved" if is_approve else "Rejected"
                    legacy_step.step_date = timezone.now()
                    legacy_step.comments = comments
                    legacy_step.save()

                return (
                    TransportRequestDetailSerializer(transport_request).data,
                    200,
                )
            elif is_approve:
                return ({"error": "No pending approval step found"}, 400)
            else:
                # reject: no explicit response here in the original action
                # (falls through and implicitly returns None) - preserved
                # as-is, not fixed, per this function's docstring.
                return None
        else:
            # Fallback to legacy approval/rejection logic
            if not (user.is_superuser or can_approve(user, "transport")):
                return (
                    {
                        "error": f"You do not have permission to {action} transport requests"
                    },
                    403,
                )

            if is_approve:
                logger.warning(
                    f" No workflow instance found for Transport #{transport_request.id}, using legacy approval"
                )

                current_step = transport_request.approval_steps.filter(
                    status="Pending"
                ).first()
                if not current_step:
                    return ({"error": "No pending approval step found"}, 400)

                current_step.status = "Approved"
                current_step.step_date = timezone.now()
                current_step.comments = comments
                current_step.save()

                status_progression = {
                    "Department Focal": "Pending HOD",
                    "HOD": "Approved",
                }
                next_status = status_progression.get(current_step.step_role)
                if next_status:
                    transport_request.status = next_status
                    transport_request.save()
            else:
                current_step = transport_request.approval_steps.filter(
                    status="Pending"
                ).first()
                if current_step:
                    current_step.status = "Rejected"
                    current_step.step_date = timezone.now()
                    current_step.comments = comments
                    current_step.save()

                transport_request.status = "Rejected"
                transport_request.save()

            AdminActionLog.log_action(
                user=user,
                action_type=(
                    "workflow_step_approved" if is_approve else "workflow_step_rejected"
                ),
                description=(
                    f"{'Approved' if is_approve else 'Rejected'} transport request "
                    f"#{transport_request.id}"
                    + (f" at step '{current_step.step_role}'" if is_approve else "")
                    + " (legacy fallback - no active WorkflowTemplate)"
                ),
                entity_type="transportrequest",
                entity_id=transport_request.id,
                request=request,
            )

            return (TransportRequestDetailSerializer(transport_request).data, 200)

    except Exception as e:
        logger.error(f" Error in {action} workflow: {str(e)}")
        import traceback

        traceback.print_exc()
        action_noun = "approval" if is_approve else "rejection"
        return ({"error": f"Failed to process {action_noun}: {str(e)}"}, 500)
