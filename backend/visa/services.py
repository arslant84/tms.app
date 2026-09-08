"""
Shared business logic for VisaApplicationViewSet: request-number
generation, workflow-start, approve/reject dispatch, and processing-
completion - previously duplicated or inline in the view (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 8).
"""

import logging

logger = logging.getLogger(__name__)


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


def start_visa_workflow(visa_application, request_data, initiated_by):
    """
    Start the approval workflow for a visa application. Shared by
    perform_create, perform_update, and the submit action - identical
    WorkflowRouter call + selected_approvers/skipped_steps parsing
    previously copy-pasted three times. Callers keep their own
    exception-handling/logging around this, since the three original call
    sites differed slightly there (same reasoning as transport's
    start_transport_workflow).
    """
    from workflows.router import WorkflowRouter

    selected_approvers = request_data.get("selected_approvers", None)
    if selected_approvers:
        selected_approvers = {int(k): v for k, v in selected_approvers.items()}

    skipped_steps = request_data.get("skipped_steps", None)
    if skipped_steps:
        skipped_steps = {int(k): v for k, v in skipped_steps.items()}

    workflow_instance = WorkflowRouter.start_workflow_for_request(
        entity=visa_application,
        entity_type="visaapplication",
        initiated_by=initiated_by,
        selected_approvers=selected_approvers,
        skipped_steps=skipped_steps,
    )

    if workflow_instance:
        visa_application.refresh_from_db()
        logger.info(
            f" Workflow started for Visa Application #{visa_application.id}: Workflow Instance #{workflow_instance.id}"
        )
        logger.info(f" Status updated to: {visa_application.status}")
    else:
        logger.warning(" No active workflow configured for visaapplication")

    return workflow_instance


def process_visa_approval_action(visa, request, action, comments, step_role):
    """
    Approve or reject a visa application: dispatch to the active
    WorkflowInstance if one exists (syncing a legacy VisaApprovalStep row
    alongside it, keyed by `step_role` via get_or_create - visa's own
    legacy-sync mechanics, different from transport's "first Pending
    step" lookup), else fall back to the legacy manual approval-step flow.
    `action` is "approve" or "reject".

    Returns `(response_data, http_status)` for the caller to wrap in a
    DRF Response, or `None` in the one case where the original `reject`
    action had no explicit response (workflow instance found, but no
    pending step execution) - same quirk as accommodation/transport's
    reject, preserved here too rather than fixed.
    """
    from accounts.models import AdminActionLog
    from accounts.utils import can_approve
    from django.contrib.contenttypes.models import ContentType
    from workflows.engine import WorkflowEngine
    from workflows.models import WorkflowInstance

    from .models import VisaApprovalStep
    from .serializers import VisaApplicationDetailSerializer

    user = request.user
    is_approve = action == "approve"
    target_status = "Approved" if is_approve else "Rejected"

    try:
        content_type = ContentType.objects.get_for_model(visa)
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type, object_id=visa.id, status="in_progress"
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
                visa.refresh_from_db()

                approval_step, created = VisaApprovalStep.objects.get_or_create(
                    visa=visa,
                    step_role=step_role,
                    defaults={
                        "step_name": f"{step_role} Approval",
                        "status": target_status,
                        "comments": comments,
                    },
                )
                if not created:
                    approval_step.status = target_status
                    approval_step.comments = comments
                    approval_step.save()

                return (VisaApplicationDetailSerializer(visa).data, 200)
            elif is_approve:
                return ({"error": "No pending approval step found"}, 400)
            else:
                # reject: no explicit response here in the original action
                # (falls through and implicitly returns None) - preserved
                # as-is, not fixed, per this function's docstring.
                return None
        else:
            # Fallback to legacy approval/rejection logic
            if not (user.is_superuser or can_approve(user, "visa")):
                return (
                    {
                        "error": f"You do not have permission to {action} visa applications"
                    },
                    403,
                )

            if is_approve:
                logger.warning(
                    f" No workflow instance found for Visa #{visa.id}, using legacy approval"
                )

            approval_step, created = VisaApprovalStep.objects.get_or_create(
                visa=visa,
                step_role=step_role,
                defaults={
                    "step_name": f"{step_role} Approval",
                    "status": target_status,
                    "comments": comments,
                },
            )
            if not created:
                approval_step.status = target_status
                approval_step.comments = comments
                approval_step.save()

            if is_approve:
                status_map = {"Department Focal": "Pending HOD", "HOD": "Approved"}
                visa.status = status_map.get(step_role, visa.status)
            else:
                visa.status = "Rejected"
            visa.save()

            AdminActionLog.log_action(
                user=user,
                action_type=(
                    "workflow_step_approved" if is_approve else "workflow_step_rejected"
                ),
                description=(
                    f"{target_status} visa application #{visa.id} at step '{step_role}' "
                    "(legacy fallback - no active WorkflowTemplate)"
                ),
                entity_type="visaapplication",
                entity_id=visa.id,
                request=request,
            )

            return (VisaApplicationDetailSerializer(visa).data, 200)

    except Exception as e:
        logger.error(f" Error in {action} workflow: {str(e)}")
        import traceback

        traceback.print_exc()
        action_noun = "approval" if is_approve else "rejection"
        return ({"error": f"Failed to process {action_noun}: {str(e)}"}, 500)


def finalize_visa_workflow_completion(visa, completed_by):
    """
    Mark the visa's "approved" WorkflowInstance as completed and fire the
    processing-completion notification + any linked-TRF department-focal
    notification.

    Extracted from the `complete` action, and now also called from
    perform_update's "Approved -> Completed" branch - previously that
    branch only flipped the WorkflowInstance to "completed" and stopped
    there, silently skipping notify_processing_completed and the TRF
    department-focal check whenever a client PATCHed status straight to
    "Completed" instead of calling the dedicated `complete` action. This
    is a deliberate behavior fix (see docs/CODEBASE_REFACTOR_ROADMAP.md
    item 8's bug note), not a silent side effect of the extraction -
    every caller now gets the same completion side effects regardless of
    which code path reached "Completed".
    """
    from django.contrib.contenttypes.models import ContentType
    from workflows.models import WorkflowInstance

    try:
        content_type = ContentType.objects.get_for_model(visa)
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type, object_id=visa.id, status="approved"
        ).first()

        if workflow_instance:
            workflow_instance.status = "completed"
            workflow_instance.save()
            logger.info(
                f" Workflow instance #{workflow_instance.id} marked as completed for Visa #{visa.id}"
            )

            from workflows.notifications import WorkflowNotifications

            WorkflowNotifications.notify_processing_completed(
                workflow_instance, completed_by=completed_by
            )
        else:
            logger.warning(f" No approved workflow instance found for Visa #{visa.id}")
    except Exception as e:
        logger.warning(f" Error updating workflow instance: {str(e)}")
        # Don't fail the completion if workflow update fails

    from trf.services import find_trf_for_visa, notify_department_focal_if_ready

    linked_trf = find_trf_for_visa(visa)
    if linked_trf:
        notify_department_focal_if_ready(linked_trf)
