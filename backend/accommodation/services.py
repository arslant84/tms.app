"""
Shared request-number generation and workflow-start logic for
AccommodationRequestViewSet, previously duplicated across
perform_create/perform_update/the submit action.

Split out of accommodation_request_views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 6, Phase 3). The workflow-start
logic (`start_accommodation_workflow`) was byte-for-byte identical
across all three call sites, so it moved as a pure extraction. The
request-number generation had two genuinely different strategies across
call sites (perform_create/perform_update resolve the location through
`extract_context_from_location`; `submit` used the raw location string
as context and had its own exception fallback format) - these are kept
as two separate functions rather than forced into one, to avoid
silently changing which strategy either caller uses. The only actual
behavior change made here is unifying the three call sites' slightly
different log message wording (purely diagnostic text, not observable
via the API) into one consistent message.
"""

import logging

from utils.request_id_generator import (
    extract_context_from_location,
    generate_request_id,
)
from workflows.router import WorkflowRouter

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
