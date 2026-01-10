"""
Base signal handler for workflow automation across all request types.

This module provides a generic workflow trigger that can be reused by all apps
(TRF, Transport, Visa, Accommodation) to avoid code duplication.
"""

from django.contrib.contenttypes.models import ContentType
from workflows.engine import WorkflowEngine
from workflows.models import WorkflowInstance
import logging

logger = logging.getLogger(__name__)


def start_workflow_on_status(
    instance,
    status_field='status',
    trigger_status='Submitted',
    initiated_by_field=None,
    module_name=None
):
    """
    Generic workflow trigger handler that starts a workflow when a request reaches a specific status.

    This function checks if:
    1. The instance status matches the trigger status
    2. No workflow already exists for this instance
    3. If both conditions are met, it starts a new workflow

    Args:
        instance: The model instance that triggered the signal
        status_field (str): Name of the status field to check (default: 'status')
        trigger_status (str): Status value that triggers workflow creation (default: 'Submitted')
        initiated_by_field (str): Name of the field containing the user who initiated the request.
                                 If None, will try common field names: 'requestor', 'created_by', 'user', 'requester'
        module_name (str): Module identifier for workflow template lookup.
                          If None, uses the app_label of the instance model.

    Returns:
        WorkflowInstance: The created workflow instance, or None if not created

    Raises:
        No exceptions are raised - all errors are logged
    """
    # Check if status matches trigger
    current_status = getattr(instance, status_field, None)
    if current_status != trigger_status:
        return None

    # Get module name from model if not provided
    if not module_name:
        module_name = instance._meta.app_label

    # Check if workflow already exists for this instance
    content_type = ContentType.objects.get_for_model(instance.__class__)

    # Try both field name conventions used in the codebase
    existing_workflow = WorkflowInstance.objects.filter(
        entity_content_type=content_type,
        entity_id=instance.id
    ).first()

    if not existing_workflow:
        # Also check the old convention (used by visa app)
        existing_workflow = WorkflowInstance.objects.filter(
            content_type=content_type,
            object_id=instance.id
        ).first()

    # Only create workflow if it doesn't exist yet
    if existing_workflow:
        logger.debug(
            f"Workflow already exists for {instance.__class__.__name__} #{instance.id}"
        )
        return None

    # Determine the user who initiated the request
    initiated_by = None
    if initiated_by_field:
        initiated_by = getattr(instance, initiated_by_field, None)
    else:
        # Try common field names
        for field_name in ['requestor', 'created_by', 'user', 'requester']:
            if hasattr(instance, field_name):
                initiated_by = getattr(instance, field_name)
                if initiated_by:
                    break

    if not initiated_by:
        logger.warning(
            f"Could not determine initiated_by user for {instance.__class__.__name__} #{instance.id}. "
            f"Workflow may not start correctly."
        )

    # Start the workflow
    try:
        workflow_instance = WorkflowEngine.start_workflow(
            entity=instance,
            initiated_by=initiated_by,
            module_name=module_name
        )

        logger.info(
            f"✅ Workflow started for {instance.__class__.__name__} #{instance.id}: "
            f"Workflow ID {workflow_instance.id}"
        )
        return workflow_instance

    except Exception as e:
        logger.error(
            f"❌ Failed to start workflow for {instance.__class__.__name__} #{instance.id}: {str(e)}",
            exc_info=True
        )
        return None
