"""
Celery tasks for the Approvals app.
"""

import logging

from celery import shared_task

logger = logging.getLogger("approvals")


@shared_task(
    bind=True,
    max_retries=2,
    queue="default",
    soft_time_limit=300,
    time_limit=360,
)
def bulk_approve_task(self, items, action, comments, user_id):
    """
    Process bulk approve/reject for multiple workflow items.

    Args:
        items: list of {"id": str, "type": str} dicts
        action: "approve" or "reject"
        comments: optional comment string applied to every step
        user_id: ID of the user who triggered the action (request.user.id)

    Returns a dict {"success": [...], "failed": [...]} describing each outcome.
    """
    from django.contrib.contenttypes.models import ContentType

    from accounts.models import AdminActionLog, User
    from accommodation.models import AccommodationRequest
    from transport.models import TransportRequest
    from trf.models import TravelRequest
    from visa.models import VisaApplication
    from workflows.engine import WorkflowEngine
    from workflows.models import WorkflowInstance

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error("bulk_approve_task: User %s not found", user_id)
        return {"error": "User not found"}

    type_model_map = {
        "trf": TravelRequest,
        "transport": TransportRequest,
        "visa": VisaApplication,
        "accommodation": AccommodationRequest,
    }

    results = {"success": [], "failed": []}

    for item in items:
        item_id = item.get("id")
        item_type = item.get("type", "").lower()

        if item_type not in type_model_map:
            results["failed"].append(
                {"id": item_id, "type": item_type, "error": f"Unknown item type: {item_type}"}
            )
            continue

        model = type_model_map[item_type]

        try:
            obj = model.objects.get(id=item_id)
            content_type = ContentType.objects.get_for_model(obj)

            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type, object_id=obj.id, status="in_progress"
            ).first()

            if not workflow_instance:
                results["failed"].append(
                    {"id": item_id, "type": item_type, "error": "No active workflow found"}
                )
                continue

            current_step = (
                workflow_instance.step_executions.filter(status="pending")
                .order_by("workflow_step__step_order")
                .first()
            )

            if not current_step:
                results["failed"].append(
                    {"id": item_id, "type": item_type, "error": "No pending workflow step"}
                )
                continue

            WorkflowEngine.process_action(
                step_execution_id=current_step.id,
                action=action,
                actioned_by=user,
                comments=comments,
            )
            obj.refresh_from_db()

            AdminActionLog.log_action(
                user=user,
                action_type=(
                    "workflow_bulk_approve" if action == "approve" else "workflow_bulk_reject"
                ),
                description=(
                    f"Bulk {action} (async) - {comments[:100]}"
                    if comments
                    else f"Bulk {action} (async)"
                ),
                entity_type=item_type,
                entity_id=str(item_id),
            )

            results["success"].append(
                {"id": item_id, "type": item_type, "new_status": obj.status}
            )

        except model.DoesNotExist:
            results["failed"].append(
                {"id": item_id, "type": item_type, "error": "Item not found"}
            )
        except Exception as exc:
            logger.error(
                "bulk_approve_task: error processing %s %s: %s", item_type, item_id, exc
            )
            results["failed"].append(
                {"id": item_id, "type": item_type, "error": str(exc)}
            )

    logger.info(
        "bulk_approve_task: %s — %d success, %d failed",
        action,
        len(results["success"]),
        len(results["failed"]),
    )
    return results
