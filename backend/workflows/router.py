"""
Workflow Router - Automatic workflow initiation and routing
Handles starting workflows when requests are submitted
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)
from accounts.models import User
from django.db import transaction

from .engine import WorkflowEngine
from .models import WorkflowInstance, WorkflowTemplate


class WorkflowRouter:
    """
    Routes requests through appropriate approval workflows
    """

    @staticmethod
    @transaction.atomic
    def start_workflow_for_request(
        entity: any,
        entity_type: str,
        initiated_by: User,
        selected_approvers: Optional[Dict[int, int]] = None,
        skipped_steps: Optional[Dict[int, str]] = None,
        fallback_entity_type: Optional[str] = None,
    ) -> Optional[WorkflowInstance]:
        """
        Start a workflow for a newly created request

        Args:
            entity: The request object (TravelRequest, etc.)
            entity_type: Type identifier (travelrequest, etc.)
            initiated_by: User who created the request
            selected_approvers: Optional dict mapping step_order to selected user_id
            skipped_steps: Optional dict mapping step_order to skip reason
                          (for steps where approver is not available)
            fallback_entity_type: Optional entity_type to fall back to if no
                          active template exists for entity_type - lets a
                          sub-type route through a shared parent template
                          until an admin creates a dedicated one

        Returns:
            WorkflowInstance if workflow started, None if no workflow configured
        """
        # Get active workflow template for this entity type (or its fallback)
        workflow_template = WorkflowTemplate.get_active_for(
            entity_type, fallback_entity_type
        )

        if not workflow_template:
            logger.info(f"No active workflow found for entity type: {entity_type}")
            return None

        # Check if workflow has steps
        if workflow_template.steps.count() == 0:
            logger.warning(f"Workflow template {workflow_template.name} has no steps")
            return None

        # Use the WorkflowEngine to start the workflow
        try:
            workflow_instance = WorkflowEngine.start_workflow(
                entity=entity,
                initiated_by=initiated_by,
                module_name=entity_type,
                selected_approvers=selected_approvers,
                skipped_steps=skipped_steps,
                fallback_module_name=fallback_entity_type,
            )

            logger.info(
                f"Workflow started: {workflow_instance.id} for {entity_type} #{entity.id}"
            )
            return workflow_instance

        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}")
            raise
