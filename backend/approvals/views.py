"""
Unified Approvals API

Provides a single endpoint for all pending approvals across all modules:
- Travel Requests (TRF/TSR)
- Transport Requests
- Visa Applications
- Accommodation Requests

Note: this app has no models. It is a thin read-aggregation and bulk-action
layer over `workflows.WorkflowInstance`/`WorkflowStepExecution` — step
advancement itself goes through `workflows.engine.WorkflowEngine`, not
anything defined here.
"""

from datetime import datetime

from accommodation.models import AccommodationRequest
from accounts.models import AdminActionLog, Role
from accounts.utils import can_approve, has_permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from transport.models import TransportRequest
from trf.models import TravelRequest
from utils.api_response import (
    get_pagination_params,
    paginated_response,
    success_response,
)
from visa.models import VisaApplication
from workflows.engine import WorkflowEngine
from workflows.models import WorkflowDelegation, WorkflowInstance, WorkflowStepExecution


@extend_schema(
    tags=["Approvals"],
    summary="List pending approvals",
    description="Get all pending approvals across all modules (TRF, Transport, Visa, Accommodation). "
    "Returns items based on user role and workflow assignments.",
    parameters=[
        OpenApiParameter(
            "page", OpenApiTypes.INT, description="Page number", default=1
        ),
        OpenApiParameter(
            "limit", OpenApiTypes.INT, description="Items per page", default=20
        ),
        OpenApiParameter(
            "type",
            OpenApiTypes.STR,
            description="Filter by type: trf, transport, visa, accommodation",
        ),
    ],
    responses={200: {"description": "List of pending approval items"}},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unified_approvals(request):
    """
    Get all pending approvals across all modules

    Returns a unified list of items pending approval based on:
    - User's role matching the workflow step's approver_role
    - OR user being specifically assigned to the step
    - OR user being admin (override)
    """
    user = request.user
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 20))
    item_type = request.GET.get(
        "type", None
    )  # 'trf', 'transport', 'visa', 'accommodation'

    offset = (page - 1) * limit

    # Approval-queue statuses: workflow step statuses are generated dynamically
    # as "Pending {role name}" or "Pending {step name}" (see
    # WorkflowEngine._update_entity_status_from_step), so any role/step name
    # in the system can produce a status never seen before. Match on prefix
    # instead of enumerating every role name, plus a few legacy fixed values.
    approval_status_filter = Q(status__istartswith="Pending") | Q(
        status__in=["Submitted", "Under Review"]
    )

    all_items = []

    def _batch_approvable_ids(entities, user):
        """
        Return the set of entity IDs (as strings) that `user` is authorized
        to approve. Replaces the N+1 per-entity DB lookups with 3 queries:

          1. All in-progress WorkflowInstances for the entity list.
          2. First pending WorkflowStepExecution per instance.
          3. Active delegations for the user on those steps.
        """
        if not entities:
            return set()
        if user.is_superuser:
            return {str(e.id) for e in entities}

        content_type = ContentType.objects.get_for_model(entities[0].__class__)
        entity_ids_str = [str(e.id) for e in entities]

        # Query 1 — in-progress workflow instances. Keyed by str(object_id) -
        # WorkflowInstance.object_id is a PositiveIntegerField, so without
        # the str() this dict (and everything built from its keys below:
        # entity_step_map, the approvable set, needs_delegation/obj_by_step)
        # would carry int object_ids, while the caller two callers down
        # (the `if str(transport.id) in approvable_transport_ids:` checks
        # in unified_approvals) always test membership with a str. Python's
        # `'127' in {127}` is False even though they "look" the same, so
        # every non-superuser's own pending approvals silently vanished
        # from their queue - only the user.is_superuser branch above
        # happened to already build its set with `str(e.id)`, so this only
        # ever affected real approvers, never a superuser testing the flow.
        instances = {
            str(wi.object_id): wi
            for wi in WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id__in=entity_ids_str,
                status="in_progress",
            )
        }
        if not instances:
            return set()

        # Query 2 — first pending step per instance (ordered by step_order)
        instance_step_map = {}
        for step in (
            WorkflowStepExecution.objects.filter(
                workflow_instance_id__in=[wi.id for wi in instances.values()],
                status="pending",
            )
            .select_related("workflow_step")
            .order_by("workflow_instance_id", "workflow_step__step_order")
        ):
            if step.workflow_instance_id not in instance_step_map:
                instance_step_map[step.workflow_instance_id] = step

        # Build object_id → step map
        entity_step_map = {
            obj_id: instance_step_map[wi.id]
            for obj_id, wi in instances.items()
            if wi.id in instance_step_map
        }
        if not entity_step_map:
            return set()

        user_role_id = str(user.role.id) if getattr(user, "role", None) else None
        user_role_name = user.role.name if getattr(user, "role", None) else None

        approvable = set()
        needs_delegation = []  # (object_id, step_execution_id)

        for obj_id, step in entity_step_map.items():
            # Directly assigned to this user
            if step.assigned_to_id and str(step.assigned_to_id) == str(user.id):
                approvable.add(obj_id)
                continue

            # Assigned to someone else → delegation only
            if step.assigned_to_id is not None:
                needs_delegation.append((obj_id, step.id))
                continue

            # Role-based matching
            if user_role_id and step.workflow_step.approver_role:
                role_val = step.workflow_step.approver_role
                if user_role_id == role_val or user_role_name == role_val:
                    approvable.add(obj_id)
                    continue

            needs_delegation.append((obj_id, step.id))

        # Query 3 — delegation check in one shot
        if needs_delegation:
            step_ids = [s_id for _, s_id in needs_delegation]
            obj_by_step = {s_id: obj_id for obj_id, s_id in needs_delegation}
            now = timezone.now()
            delegated = set(
                WorkflowDelegation.objects.filter(
                    workflow_step_execution_id__in=step_ids,
                    delegated_to=user,
                    is_active=True,
                )
                .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
                .values_list("workflow_step_execution_id", flat=True)
            )
            for step_id in delegated:
                if step_id in obj_by_step:
                    approvable.add(obj_by_step[step_id])

        return approvable

    # Helper function to format items
    def format_item(obj, item_type_name):
        # Get requestor name from various possible fields
        requestor_name = ""
        if hasattr(obj, "requestor_name"):
            requestor_name = obj.requestor_name
        elif hasattr(obj, "staff_name"):
            requestor_name = obj.staff_name
        elif hasattr(obj, "user") and obj.user:
            requestor_name = (
                obj.user.name if hasattr(obj.user, "name") else obj.user.email
            )

        # Get purpose from various possible fields
        purpose = ""
        if hasattr(obj, "purpose") and obj.purpose:
            purpose = obj.purpose
        elif hasattr(obj, "travel_purpose") and obj.travel_purpose:
            purpose = obj.travel_purpose
        elif hasattr(obj, "title") and obj.title:
            purpose = obj.title
        else:
            purpose = f"{item_type_name} Request"

        # Get request_number (formatted ID) or fallback to numeric ID
        request_identifier = getattr(obj, "request_number", None) or str(obj.id)

        return {
            "id": str(obj.id),  # Keep numeric ID for API calls
            "requestNumber": request_identifier,  # Display formatted request number
            "requestorName": requestor_name,
            "staffId": getattr(obj, "staff_id", "") or "",
            "itemType": item_type_name,
            "purpose": purpose,
            "status": obj.status,
            "submittedAt": (
                (
                    obj.submitted_at
                    if hasattr(obj, "submitted_at") and obj.submitted_at
                    else (
                        obj.submitted_date
                        if hasattr(obj, "submitted_date") and obj.submitted_date
                        else obj.created_at
                    )
                ).isoformat()
                if hasattr(obj, "created_at")
                else None
            ),
            "department": getattr(obj, "department", "")
            or getattr(obj, "department_code", ""),
        }

    # 1. Travel Requests (TRF/TSR) - exclude Accommodation type
    if not item_type or item_type == "trf":
        trfs = list(
            TravelRequest.objects.filter(approval_status_filter)
            .exclude(
                Q(travel_type="Accommodation")
                | Q(travel_type__icontains="Accommodation")
            )
            .order_by("-submitted_at")
        )
        approvable_trf_ids = _batch_approvable_ids(trfs, user)
        for trf in trfs:
            if str(trf.id) in approvable_trf_ids:
                item = format_item(trf, "TSR")
                item["travelType"] = getattr(trf, "travel_type", "")
                all_items.append(item)

    # 2. Transport Requests - exclude TSR-embedded ones (trf is set). Those
    # ride entirely on their linked TSR's own approval workflow and never get
    # a WorkflowInstance of their own (see WorkflowEngine's transport
    # cascade), so they are never independently approvable here - listing
    # them let a superuser's blanket bypass in _batch_approvable_ids show
    # them as actionable when clicking Approve always 400s with "No pending
    # approval step found".
    if not item_type or item_type == "transport":
        transports = list(
            TransportRequest.objects.filter(
                approval_status_filter, trf__isnull=True
            ).order_by("-submitted_at")
        )
        approvable_transport_ids = _batch_approvable_ids(transports, user)
        for transport in transports:
            if str(transport.id) in approvable_transport_ids:
                item = format_item(transport, "Transport")
                all_items.append(item)

    # 3. Visa Applications
    if not item_type or item_type == "visa":
        visas = list(
            VisaApplication.objects.filter(approval_status_filter).order_by(
                "-submitted_date"
            )
        )
        approvable_visa_ids = _batch_approvable_ids(visas, user)
        for visa in visas:
            if str(visa.id) in approvable_visa_ids:
                item = format_item(visa, "Visa")
                item["destination"] = getattr(visa, "destination", "")
                item["visaType"] = getattr(visa, "visa_type", "")
                all_items.append(item)

    # Accommodation requests are no longer a separate approval item: they ride
    # entirely on their linked TSR's own approval (see WorkflowEngine's
    # accommodation cascade) and are never independently approvable, so they
    # are intentionally excluded from this queue.

    # Sort all items by submission date (newest first)
    all_items.sort(key=lambda x: x["submittedAt"] or "", reverse=True)

    # Apply pagination
    total_count = len(all_items)
    paginated_items = all_items[offset : offset + limit]

    return success_response(
        data=paginated_items,
        message=f"Retrieved {len(paginated_items)} pending approval(s)",
        status_code=200,
        meta={
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit,
                "has_next": page < ((total_count + limit - 1) // limit),
                "has_previous": page > 1,
            }
        },
    )


@extend_schema(
    tags=["Approvals"],
    summary="Bulk approve/reject",
    description="Approve or reject multiple items at once. Supports TRF, Transport, Visa, and Accommodation requests.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": ["trf", "transport", "visa", "accommodation"],
                            },
                        },
                    },
                },
                "action": {"type": "string", "enum": ["approve", "reject"]},
                "comments": {"type": "string"},
            },
            "required": ["items", "action"],
        }
    },
    responses={
        200: {"description": "Bulk action completed with results"},
        400: {"description": "Invalid request data"},
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_approve(request):
    """
    Bulk approve or reject multiple items at once

    Request body:
    {
        "items": [
            {"id": "123", "type": "trf"},
            {"id": "456", "type": "transport"},
            ...
        ],
        "action": "approve" or "reject",
        "comments": "Optional comments for all items"
    }
    """
    import logging

    from django.db import transaction
    from utils.api_response import error_response, success_response

    logger = logging.getLogger(__name__)
    user = request.user

    items = request.data.get("items", [])
    action = request.data.get("action", "").lower()
    comments = request.data.get("comments", "")

    if not items:
        return error_response(
            message="No items provided for bulk action", status_code=400
        )

    if action not in ["approve", "reject"]:
        return error_response(
            message='Invalid action. Must be "approve" or "reject"', status_code=400
        )

    # For large batches dispatch a Celery task so the request returns immediately.
    # Small batches (<=10 items) run synchronously for instant UI feedback.
    ASYNC_THRESHOLD = 10
    if len(items) > ASYNC_THRESHOLD:
        from approvals.tasks import bulk_approve_task

        task = bulk_approve_task.apply_async(
            args=[items, action, comments, request.user.id],
            queue="default",
        )
        return success_response(
            data={"task_id": task.id},
            message=f"Bulk {action} queued for {len(items)} items — poll /api/tasks/{task.id}/ for results",
            status_code=202,
        )

    type_model_map = {
        "trf": TravelRequest,
        "transport": TransportRequest,
        "visa": VisaApplication,
        "accommodation": AccommodationRequest,
    }

    results = {"success": [], "failed": []}

    with transaction.atomic():
        for item in items:
            item_id = item.get("id")
            item_type = item.get("type", "").lower()

            if item_type not in type_model_map:
                results["failed"].append(
                    {
                        "id": item_id,
                        "type": item_type,
                        "error": f"Unknown item type: {item_type}",
                    }
                )
                continue

            model = type_model_map[item_type]

            try:
                obj = model.objects.get(id=item_id)

                # Check if user can approve this item
                from django.contrib.contenttypes.models import ContentType

                content_type = ContentType.objects.get_for_model(obj)

                workflow_instance = WorkflowInstance.objects.filter(
                    content_type=content_type, object_id=obj.id, status="in_progress"
                ).first()

                if not workflow_instance:
                    results["failed"].append(
                        {
                            "id": item_id,
                            "type": item_type,
                            "error": "No active workflow found",
                        }
                    )
                    continue

                # Get current pending step
                current_step = (
                    workflow_instance.step_executions.filter(status="pending")
                    .order_by("workflow_step__step_order")
                    .first()
                )

                if not current_step:
                    results["failed"].append(
                        {
                            "id": item_id,
                            "type": item_type,
                            "error": "No pending workflow step",
                        }
                    )
                    continue

                # Advance the step via WorkflowEngine.process_action — the
                # canonical, transactional implementation (see
                # docs/APPROVAL_WORKFLOW_FIX_ROADMAP.md Fix 2). This also
                # updates the entity's status and sends notifications, so the
                # inline status-transition and notification logic that used
                # to live here is no longer needed.
                WorkflowEngine.process_action(
                    step_execution_id=current_step.id,
                    action=action,
                    actioned_by=user,
                    comments=comments,
                )
                obj.refresh_from_db()

                # Bulk-specific audit entry, distinct from the per-step entry
                # WorkflowEngine.process_action already writes — this one
                # records that the action was taken via the bulk endpoint.
                AdminActionLog.log_action(
                    user=user,
                    action_type=(
                        "workflow_bulk_approve"
                        if action == "approve"
                        else "workflow_bulk_reject"
                    ),
                    description=(
                        f"Bulk {action} - {comments[:100]}"
                        if comments
                        else f"Bulk {action}"
                    ),
                    entity_type=item_type,
                    entity_id=str(item_id),
                    request=request,
                )

                results["success"].append(
                    {"id": item_id, "type": item_type, "new_status": obj.status}
                )

            except model.DoesNotExist:
                results["failed"].append(
                    {"id": item_id, "type": item_type, "error": "Item not found"}
                )
            except Exception as e:
                logger.error(
                    f"Error processing bulk {action} for {item_type} {item_id}: {str(e)}"
                )
                results["failed"].append(
                    {"id": item_id, "type": item_type, "error": str(e)}
                )

    return success_response(
        data=results,
        message=f'Bulk {action} completed: {len(results["success"])} success, {len(results["failed"])} failed',
        status_code=200,
    )


@extend_schema(
    tags=["Approvals"],
    summary="Get approval history",
    description="Get approval history for a specific item or all items. Shows workflow step executions and status changes.",
    parameters=[
        OpenApiParameter(
            "item_id", OpenApiTypes.STR, description="ID of the specific item"
        ),
        OpenApiParameter(
            "item_type",
            OpenApiTypes.STR,
            description="Type: trf, transport, visa, accommodation",
        ),
        OpenApiParameter(
            "page", OpenApiTypes.INT, description="Page number", default=1
        ),
        OpenApiParameter(
            "limit", OpenApiTypes.INT, description="Items per page", default=20
        ),
    ],
    responses={200: {"description": "Approval history records"}},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def approval_history(request):
    """
    Get approval history for a specific item or all items

    Query params:
    - item_id: ID of the specific item (optional)
    - item_type: Type of item (trf, transport, visa, accommodation) (required if item_id is provided)
    - page: Page number (default: 1)
    - limit: Items per page (default: 20)
    """
    from django.contrib.contenttypes.models import ContentType
    from utils.api_response import error_response, success_response

    user = request.user
    item_id = request.GET.get("item_id")
    item_type = request.GET.get("item_type", "").lower()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 20))

    offset = (page - 1) * limit

    type_model_map = {
        "trf": TravelRequest,
        "transport": TransportRequest,
        "visa": VisaApplication,
        "accommodation": AccommodationRequest,
    }

    history_items = []

    if item_id and item_type:
        # Get history for specific item
        if item_type not in type_model_map:
            return error_response(
                message=f"Invalid item type: {item_type}", status_code=400
            )

        model = type_model_map[item_type]

        try:
            obj = model.objects.get(id=item_id)
            content_type = ContentType.objects.get_for_model(obj)

            # Get all workflow instances for this item
            workflows = WorkflowInstance.objects.filter(
                content_type=content_type, object_id=obj.id
            ).order_by("-created_at")

            for workflow in workflows:
                # Get all step executions
                steps = workflow.step_executions.select_related(
                    "workflow_step", "actioned_by", "assigned_to"
                ).order_by("workflow_step__step_order")

                for step in steps:
                    history_items.append(
                        {
                            "id": str(step.id),
                            "item_id": str(obj.id),
                            "item_type": item_type,
                            "step_name": step.workflow_step.step_name,
                            "step_order": step.workflow_step.step_order,
                            "status": step.status,
                            "assigned_to": (
                                {
                                    "id": (
                                        step.assigned_to.id
                                        if step.assigned_to
                                        else None
                                    ),
                                    "name": (
                                        step.assigned_to.get_full_name()
                                        if step.assigned_to
                                        else None
                                    ),
                                    "email": (
                                        step.assigned_to.email
                                        if step.assigned_to
                                        else None
                                    ),
                                }
                                if step.assigned_to
                                else None
                            ),
                            "actioned_by": (
                                {
                                    "id": (
                                        step.actioned_by.id
                                        if step.actioned_by
                                        else None
                                    ),
                                    "name": (
                                        step.actioned_by.get_full_name()
                                        if step.actioned_by
                                        else None
                                    ),
                                    "email": (
                                        step.actioned_by.email
                                        if step.actioned_by
                                        else None
                                    ),
                                }
                                if step.actioned_by
                                else None
                            ),
                            "action_date": (
                                step.action_date.isoformat()
                                if step.action_date
                                else None
                            ),
                            "comments": step.comments,
                            "created_at": step.created_at.isoformat(),
                            "workflow_status": workflow.status,
                        }
                    )

        except model.DoesNotExist:
            return error_response(
                message=f"{item_type.upper()} with id {item_id} not found",
                status_code=404,
            )

    else:
        # Get all recent approval history (admin only for full history)
        from django.conf import settings

        # Get recent workflow step executions
        step_executions = (
            WorkflowStepExecution.objects.select_related(
                "workflow_instance", "workflow_step", "actioned_by", "assigned_to"
            )
            .exclude(status="pending")
            .order_by("-action_date")
        )

        # For non-admin users, filter to their own items
        has_approval_access = (
            user.is_superuser
            or has_permission(user, "view_pending_approvals")
            or can_approve(user)
        )
        if not has_approval_access and not settings.DEBUG:
            # This is a simplified filter - in production you'd want more precise filtering
            step_executions = step_executions.filter(
                Q(actioned_by=user) | Q(assigned_to=user)
            )

        for step in step_executions[:100]:  # Limit to 100 for performance
            workflow = step.workflow_instance

            # Get the actual item details
            try:
                content_type = workflow.content_type
                model_class = content_type.model_class()
                obj = model_class.objects.get(id=workflow.object_id)

                # Determine item type
                model_name = content_type.model
                if model_name == "travelrequest":
                    detected_type = "trf"
                elif model_name == "transportrequest":
                    detected_type = "transport"
                elif model_name == "visaapplication":
                    detected_type = "visa"
                elif model_name == "accommodationrequest":
                    detected_type = "accommodation"
                else:
                    detected_type = model_name

                history_items.append(
                    {
                        "id": str(step.id),
                        "item_id": str(workflow.object_id),
                        "item_type": detected_type,
                        "item_summary": getattr(obj, "purpose", None)
                        or getattr(obj, "title", None)
                        or str(obj),
                        "step_name": step.workflow_step.step_name,
                        "status": step.status,
                        "actioned_by": (
                            {
                                "id": step.actioned_by.id if step.actioned_by else None,
                                "name": (
                                    step.actioned_by.get_full_name()
                                    if step.actioned_by
                                    else None
                                ),
                                "email": (
                                    step.actioned_by.email if step.actioned_by else None
                                ),
                            }
                            if step.actioned_by
                            else None
                        ),
                        "action_date": (
                            step.action_date.isoformat() if step.action_date else None
                        ),
                        "comments": step.comments,
                    }
                )
            except Exception:
                continue

    # Apply pagination
    total_count = len(history_items)
    paginated_items = history_items[offset : offset + limit]

    return success_response(
        data=paginated_items,
        message=f"Retrieved {len(paginated_items)} approval history record(s)",
        status_code=200,
        meta={
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (
                    (total_count + limit - 1) // limit if total_count > 0 else 1
                ),
                "has_next": (
                    page < ((total_count + limit - 1) // limit)
                    if total_count > 0
                    else False
                ),
                "has_previous": page > 1,
            }
        },
    )
