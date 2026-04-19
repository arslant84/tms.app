"""
Workflow Router - Automatic workflow initiation and routing
Handles starting workflows when requests are submitted
"""
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from accounts.models import User, Role
from .models import (
    WorkflowTemplate,
    WorkflowInstance,
    WorkflowStepExecution
)
from .notifications import WorkflowNotifications
from .engine import WorkflowEngine


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
        skipped_steps: Optional[Dict[int, str]] = None
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

        Returns:
            WorkflowInstance if workflow started, None if no workflow configured
        """
        # Get active workflow template for this entity type
        workflow_template = WorkflowTemplate.objects.filter(
            entity_type=entity_type,
            is_active=True
        ).prefetch_related('steps').first()

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
                skipped_steps=skipped_steps
            )

            logger.info(f"Workflow started: {workflow_instance.id} for {entity_type} #{entity.id}")
            return workflow_instance

        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}")
            raise

    @staticmethod
    def get_users_by_role(role_id: str) -> List[User]:
        """
        Get all users with a specific role

        Args:
            role_id: The role ID to filter by

        Returns:
            List of users with that role
        """
        try:
            role = Role.objects.get(id=role_id)
            return User.objects.filter(role=role, is_active=True)
        except Role.DoesNotExist:
            return []

    @staticmethod
    def assign_step_to_role_users(workflow_instance: WorkflowInstance, step_order: int):
        """
        Assign a workflow step to all users with the appropriate role

        Args:
            workflow_instance: The workflow instance
            step_order: The step order to assign
        """
        # Get step executions for this order
        step_executions = workflow_instance.step_executions.filter(
            workflow_step__step_order=step_order,
            status='pending'
        )

        for step_exec in step_executions:
            role_id = step_exec.workflow_step.approver_role

            if role_id:
                # Get users with this role
                users = WorkflowRouter.get_users_by_role(role_id)

                # If specific user assigned, use that
                if step_exec.assigned_to:
                    continue

                # Assign to first user with role (or implement round-robin)
                if users:
                    step_exec.assigned_to = users[0]
                    step_exec.save()

                    # Send notification
                    WorkflowNotifications.notify_approval_required(step_exec)

    @staticmethod
    def get_final_processing_admin(entity_type: str) -> Optional[User]:
        """
        Get the admin user responsible for final processing of this entity type

        Args:
            entity_type: The entity type

        Returns:
            User responsible for processing, or None
        """
        # Define admin roles for each module
        admin_role_map = {
            'travelrequest': 'Travel Desk',
            'transportrequest': 'Transport Admin',
            'visaapplication': 'Visa Admin',
            'accommodation': 'Accommodation Admin',
            'combinedrequest': 'Travel Desk',  # Combined requests routed to Travel Desk for coordination
        }

        admin_role_name = admin_role_map.get(entity_type)

        if not admin_role_name:
            return None

        try:
            role = Role.objects.get(name=admin_role_name)
            # Get first active user with this role
            return User.objects.filter(role=role, is_active=True).first()
        except Role.DoesNotExist:
            return None

    @staticmethod
    def notify_final_admin(workflow_instance: WorkflowInstance):
        """
        Notify the final processing admin when all approvals are complete

        Args:
            workflow_instance: The completed workflow instance
        """
        entity_type = workflow_instance.workflow_template.entity_type
        admin = WorkflowRouter.get_final_processing_admin(entity_type)

        if admin:
            WorkflowNotifications.notify_workflow_completed(
                workflow_instance=workflow_instance,
                processor_name=admin.get_full_name()
            )
