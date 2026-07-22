"""
Workflow Engine - Core business logic for workflow execution
Handles workflow lifecycle: start, process actions, escalate, complete
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
from typing import Any, Dict, Optional

from accounts.models import AdminActionLog, User
from accounts.utils import can_manage
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils import timezone

from .models import (
    WorkflowAuditLog,
    WorkflowDelegation,
    WorkflowInstance,
    WorkflowStep,
    WorkflowStepExecution,
    WorkflowTemplate,
)
from .notifications import WorkflowNotifications


class WorkflowEngine:
    """
    Core workflow execution engine.
    Handles workflow lifecycle and business logic.
    """

    @staticmethod
    @transaction.atomic
    def start_workflow(
        entity,
        initiated_by: User,
        module_name: str,
        selected_approvers: Optional[Dict[int, int]] = None,
        skipped_steps: Optional[Dict[int, str]] = None,
    ) -> WorkflowInstance:
        """
        Start a new workflow for an entity (TRF, Visa, etc.)

        Args:
            entity: The entity object (TravelRequest, etc.)
            initiated_by: User who initiated the workflow
            module_name: Module identifier ('trf', 'visa', etc.)
            selected_approvers: Optional dict mapping step_order to selected user_id
            skipped_steps: Optional dict mapping step_order to skip reason
                          (for steps where approver is not available)

        Returns:
            WorkflowInstance: The created workflow instance

        Raises:
            ValueError: If no active workflow template found for module
        """
        # Get active workflow template for the module
        workflow_template = (
            WorkflowTemplate.objects.filter(entity_type=module_name, is_active=True)
            .prefetch_related("steps")
            .first()
        )

        if not workflow_template:
            raise ValueError(
                f"No active workflow template found for module: {module_name}"
            )

        # Get content type for the entity
        content_type = ContentType.objects.get_for_model(entity)

        # Create workflow instance with optional selected approvers and skipped steps
        additional_data = {}
        if selected_approvers:
            # Store with string keys for JSON compatibility
            additional_data["selected_approvers"] = {
                str(k): v for k, v in selected_approvers.items()
            }
        if skipped_steps:
            # Store skipped steps with string keys for JSON compatibility
            additional_data["skipped_steps"] = {
                str(k): v for k, v in skipped_steps.items()
            }

        workflow_instance = WorkflowInstance.objects.create(
            workflow_template=workflow_template,
            content_type=content_type,
            object_id=entity.id,
            initiated_by=initiated_by,
            status="in_progress",
            current_step_order=1,
            additional_data=additional_data if additional_data else None,
        )

        # Log workflow creation
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type="created",
            action_description=f"Workflow started for {module_name} #{entity.id}",
            performed_by=initiated_by,
        )

        # Get first step
        first_step = workflow_template.steps.filter(step_order=1).first()

        if first_step:
            # Start first step
            WorkflowEngine._start_step(workflow_instance, first_step, initiated_by)
        else:
            # No steps defined - auto-complete workflow
            workflow_instance.status = "approved"
            workflow_instance.completed_at = timezone.now()
            workflow_instance.save()

        # Send workflow started notification
        WorkflowNotifications.notify_workflow_started(workflow_instance)

        return workflow_instance

    @staticmethod
    @transaction.atomic
    def process_action(
        step_execution_id: int,
        action: str,
        actioned_by: User,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process an approval action (approve, reject, skip)

        Args:
            step_execution_id: ID of the step execution
            action: Action to take ('approve', 'reject', 'skip')
            actioned_by: User taking the action
            comments: Optional comments

        Returns:
            dict: Result of the action with workflow status

        Raises:
            ValueError: If action is invalid or user not authorized
        """
        step_execution = (
            WorkflowStepExecution.objects.select_related(
                "workflow_instance",
                "workflow_step",
                "workflow_instance__workflow_template",
            )
            .select_for_update()
            .get(id=step_execution_id)
        )

        # Check if step has already been processed (handles rapid duplicate submissions)
        if step_execution.status != "pending":
            logger.warning(
                f" Step execution {step_execution_id} already processed with status '{step_execution.status}'. Ignoring duplicate request."
            )
            return {
                "success": True,
                "workflow_status": step_execution.workflow_instance.status,
                "message": f"Step already {step_execution.status}",
            }

        # Validate user is authorized
        if not WorkflowEngine._is_user_authorized(step_execution, actioned_by):
            raise ValueError("User not authorized to action this step")

        # Validate action
        if action not in ["approve", "reject", "skip"]:
            raise ValueError(f"Invalid action: {action}")

        # Check if step requires comments
        if step_execution.workflow_step.requires_comments and not comments:
            raise ValueError("Comments are required for this step")

        # Update step execution
        step_execution.status = action + "d" if action != "skip" else "skipped"
        step_execution.actioned_by = actioned_by
        step_execution.action_date = timezone.now()
        step_execution.comments = comments
        step_execution.save()

        workflow_instance = step_execution.workflow_instance

        # Log the action
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type=action + "d" if action != "skip" else "skipped",
            action_description=f"Step '{step_execution.workflow_step.step_name}' {action}d by {actioned_by.email}",
            performed_by=actioned_by,
        )

        # Admin-facing audit trail (separate from the workflow-scoped log above)
        admin_action_type = {
            "approve": "workflow_step_approved",
            "reject": "workflow_step_rejected",
            "skip": "workflow_step_approved",
        }[action]
        AdminActionLog.log_action(
            user=actioned_by,
            action_type=admin_action_type,
            description=f"{action.capitalize()}d step '{step_execution.workflow_step.step_name}' "
            f"on workflow instance #{workflow_instance.id}",
            entity_type=workflow_instance.content_type.model,
            entity_id=workflow_instance.object_id,
        )

        # Process based on action - notifications are handled via configuration
        # If no config exists, default notification behavior is used
        if action == "approve" or action == "skip":
            # Trigger notifications for approval (uses config or falls back to defaults)
            WorkflowNotifications.trigger_configured_notifications(
                step_execution, "approval"
            )
            return WorkflowEngine._handle_step_approval(
                workflow_instance, step_execution, actioned_by
            )
        elif action == "reject":
            # Trigger notifications for rejection (uses config or falls back to defaults)
            WorkflowNotifications.trigger_configured_notifications(
                step_execution, "rejection"
            )
            return WorkflowEngine._handle_step_rejection(
                workflow_instance, step_execution, actioned_by, comments
            )

        return {"success": True, "workflow_status": workflow_instance.status}

    @staticmethod
    @transaction.atomic
    def delegate_step(
        step_execution_id: int,
        delegated_from: User,
        delegated_to: User,
        reason: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Delegate a workflow step to another user

        Args:
            step_execution_id: ID of the step execution
            delegated_from: User delegating
            delegated_to: User receiving delegation
            reason: Reason for delegation
            expires_at: When delegation expires

        Returns:
            dict: Result of delegation

        Raises:
            ValueError: If delegation not allowed or user not authorized
        """
        step_execution = WorkflowStepExecution.objects.select_related(
            "workflow_step"
        ).get(id=step_execution_id)

        # Check if delegation is allowed
        if step_execution.workflow_step.can_skip is False:
            # Using can_skip as a proxy for delegation allowance in existing model
            # In production, we might add a can_delegate field
            pass

        # Validate user is current assignee
        if step_execution.assigned_to != delegated_from:
            raise ValueError("Only the assigned user can delegate this step")

        # Create delegation record
        delegation = WorkflowDelegation.objects.create(
            workflow_step_execution=step_execution,
            delegated_from=delegated_from,
            delegated_to=delegated_to,
            reason=reason,
            expires_at=expires_at,
        )

        # Update step execution assignment
        step_execution.assigned_to = delegated_to
        step_execution.status = "delegated"
        step_execution.save()

        # Log delegation
        WorkflowAuditLog.objects.create(
            workflow_instance=step_execution.workflow_instance,
            action_type="delegated",
            action_description=f"Step '{step_execution.workflow_step.step_name}' delegated from {delegated_from.email} to {delegated_to.email}",
            performed_by=delegated_from,
        )

        # Send delegation notification (uses config or falls back to defaults)
        WorkflowNotifications.trigger_configured_notifications(
            step_execution, "delegation"
        )

        return {
            "success": True,
            "delegation_id": delegation.id,
            "delegated_to": delegated_to.email,
        }

    @staticmethod
    def get_pending_approvals(user: User) -> list:
        """
        Get list of pending approvals for a user based on workflow step assignments.

        Checks:
        1. Direct assignment to the user
        2. User's role UUID matching the step's approver_role
        3. Active delegations to the user

        Args:
            user: User to get pending approvals for

        Returns:
            list: List of pending step executions
        """
        from django.db.models import Q

        # Get by direct assignment
        direct_assignments = (
            WorkflowStepExecution.objects.filter(
                assigned_to=user,
                status="pending",
                workflow_instance__status="in_progress",
            )
            .select_related(
                "workflow_instance", "workflow_step", "workflow_instance__content_type"
            )
            .prefetch_related("workflow_instance__content_object")
        )

        # Get by role (matching by UUID or name)
        role_q = Q()
        if hasattr(user, "role") and user.role:
            # Match by role UUID (primary) or role name (legacy)
            role_q = Q(workflow_step__approver_role=str(user.role.id)) | Q(
                workflow_step__approver_role=user.role.name
            )

        role_assignments = (
            WorkflowStepExecution.objects.filter(
                role_q, status="pending", workflow_instance__status="in_progress"
            )
            .select_related(
                "workflow_instance", "workflow_step", "workflow_instance__content_type"
            )
            .prefetch_related("workflow_instance__content_object")
        )

        # Get by active delegation
        delegated_assignments = (
            WorkflowStepExecution.objects.filter(
                status="pending",
                workflow_instance__status="in_progress",
                delegations__delegated_to=user,
                delegations__is_active=True,
            )
            .filter(
                Q(delegations__expires_at__isnull=True)
                | Q(delegations__expires_at__gt=timezone.now())
            )
            .select_related(
                "workflow_instance", "workflow_step", "workflow_instance__content_type"
            )
            .prefetch_related("workflow_instance__content_object")
        )

        # Combine, deduplicate and return
        all_steps = (
            list(direct_assignments)
            + list(role_assignments)
            + list(delegated_assignments)
        )
        seen_ids = set()
        unique_steps = []
        for step in all_steps:
            if step.id not in seen_ids:
                seen_ids.add(step.id)
                unique_steps.append(step)

        return unique_steps

    @staticmethod
    @transaction.atomic
    def cancel_workflow(
        workflow_instance_id: int, cancelled_by: User, reason: str
    ) -> Dict[str, Any]:
        """
        Cancel an active workflow

        Args:
            workflow_instance_id: ID of the workflow instance
            cancelled_by: User cancelling the workflow
            reason: Reason for cancellation

        Returns:
            dict: Result of cancellation
        """
        workflow_instance = WorkflowInstance.objects.get(id=workflow_instance_id)

        if workflow_instance.status in ["approved", "rejected", "cancelled"]:
            raise ValueError(
                f"Cannot cancel workflow with status: {workflow_instance.status}"
            )

        # Cancel all pending step executions
        workflow_instance.step_executions.filter(status="pending").update(
            status="skipped",
            action_date=timezone.now(),
            comments=f"Skipped due to workflow cancellation: {reason}",
        )

        # Update workflow instance
        workflow_instance.status = "cancelled"
        workflow_instance.completed_at = timezone.now()
        workflow_instance.save()

        # Log cancellation
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type="cancelled",
            action_description=f"Workflow cancelled: {reason}",
            performed_by=cancelled_by,
        )

        # Send workflow cancelled notification
        WorkflowNotifications.notify_workflow_cancelled(
            workflow_instance, cancelled_by, reason
        )

        return {"success": True, "status": "cancelled"}

    # Private helper methods

    @staticmethod
    def _start_step(
        workflow_instance: WorkflowInstance, step: WorkflowStep, initiator: User
    ):
        """Create and start a workflow step execution"""
        # Check if this step is marked for skip (user indicated approver not available)
        skipped_steps = (workflow_instance.additional_data or {}).get(
            "skipped_steps", {}
        )
        step_order_str = str(step.step_order)

        logger.info(
            f"_start_step: workflow={workflow_instance.id}, step={step.step_name}, step_order={step.step_order}, can_skip={step.can_skip}"
        )
        logger.info(f"_start_step: skipped_steps from additional_data: {skipped_steps}")
        logger.info(
            f"_start_step: checking if step_order {step.step_order} (str: '{step_order_str}') is in skipped_steps"
        )

        if step_order_str in skipped_steps or step.step_order in skipped_steps:
            # Step is marked for skip - verify it's allowed and auto-skip
            if step.can_skip:
                skip_reason = (
                    skipped_steps.get(step_order_str)
                    or skipped_steps.get(step.step_order)
                    or "Approver not available"
                )
                logger.info(
                    f"Auto-skipping step '{step.step_name}' - marked as skipped by requester: {skip_reason}"
                )

                # Create skipped step execution
                step_execution = WorkflowStepExecution.objects.create(
                    workflow_instance=workflow_instance,
                    workflow_step=step,
                    assigned_to=None,
                    status="skipped",
                    actioned_by=initiator,
                    action_date=timezone.now(),
                    comments=f"Skipped during submission: {skip_reason}",
                )

                # Log the skip
                WorkflowAuditLog.objects.create(
                    workflow_instance=workflow_instance,
                    action_type="skipped",
                    action_description=f"Step '{step.step_name}' skipped by requester: {skip_reason}",
                    performed_by=initiator,
                )

                # Move to next step
                return WorkflowEngine._handle_step_approval(
                    workflow_instance, step_execution, initiator
                )
            else:
                logger.warning(
                    f"Step '{step.step_name}' marked for skip but can_skip=False. Proceeding normally."
                )

        # Check if a step execution already exists for this step
        existing_execution = WorkflowStepExecution.objects.filter(
            workflow_instance=workflow_instance, workflow_step=step
        ).first()

        # Check for user-selected approver first (highest priority)
        assigned_user = None
        selected_approvers = (workflow_instance.additional_data or {}).get(
            "selected_approvers", {}
        )

        if (
            str(step.step_order) in selected_approvers
            or step.step_order in selected_approvers
        ):
            selected_user_id = selected_approvers.get(
                str(step.step_order)
            ) or selected_approvers.get(step.step_order)
            if selected_user_id:
                assigned_user = User.objects.filter(
                    id=selected_user_id, status="Active"
                ).first()
                if assigned_user:
                    logger.info(
                        f"Using user-selected approver {assigned_user.email} for step '{step.step_name}'"
                    )

        # Fall back to existing logic if no user-selected approver
        # Priority: approver_user > approver_permission > approver_role
        if not assigned_user:
            assigned_user = step.approver_user if step.approver_user else None

        # If no specific user, try to find by permission (PREFERRED)
        if not assigned_user and step.approver_permission:
            assigned_user = WorkflowEngine._find_user_by_permission(
                step.approver_permission,
                (
                    workflow_instance.initiated_by.department
                    if hasattr(workflow_instance.initiated_by, "department")
                    else None
                ),
            )

        # Fallback: try to find by role (for backward compatibility)
        if not assigned_user and step.approver_role:
            logger.warning(
                f"Using deprecated role-based assignment for step '{step.step_name}'. Consider using approver_permission instead."
            )
            assigned_user = WorkflowEngine._find_user_by_role(
                step.approver_role,
                (
                    workflow_instance.initiated_by.department
                    if hasattr(workflow_instance.initiated_by, "department")
                    else None
                ),
            )

        # Calculate SLA and escalation dates
        sla_due_date = None
        escalation_date = None

        if step.sla_hours:
            sla_due_date = timezone.now() + timedelta(hours=step.sla_hours)

        if step.escalation_hours:
            escalation_date = timezone.now() + timedelta(hours=step.escalation_hours)

        if existing_execution:
            # If step already exists and is pending, it's a race condition - skip
            if existing_execution.status == "pending":
                logger.warning(
                    f" Step execution already pending for workflow {workflow_instance.id}, step {step.step_name}. Skipping."
                )
                return existing_execution

            # If step exists but is in 'waiting' state (pre-created by serializer), activate it
            if existing_execution.status == "waiting":
                logger.info(
                    f" Activating pre-created step execution for workflow {workflow_instance.id}, step {step.step_name}."
                )
                existing_execution.status = "pending"
                existing_execution.assigned_to = assigned_user
                existing_execution.sla_due_date = sla_due_date
                existing_execution.escalation_date = escalation_date
                existing_execution.save()
                step_execution = existing_execution
                created = True  # Treat as newly created for logging/notifications
            else:
                # Step already processed (approved/rejected/skipped) - don't re-create
                logger.warning(
                    f" Step execution already processed ({existing_execution.status}) for workflow {workflow_instance.id}, step {step.step_name}. Skipping."
                )
                return existing_execution
        else:
            # Create step execution using get_or_create to handle race conditions
            step_execution, created = WorkflowStepExecution.objects.get_or_create(
                workflow_instance=workflow_instance,
                workflow_step=step,
                defaults={
                    "assigned_to": assigned_user,
                    "status": "pending",
                    "sla_due_date": sla_due_date,
                    "escalation_date": escalation_date,
                },
            )

            if not created:
                logger.warning(
                    f" Step execution created by concurrent request for workflow {workflow_instance.id}, step {step.step_name}."
                )
                return step_execution

        # Only log and notify for newly activated steps
        if not created:
            return step_execution

        # Log step start
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type="started",
            action_description=f"Started step '{step.step_name}' (assigned to: {assigned_user.email if assigned_user else step.approver_role})",
            performed_by=initiator,
        )

        # Update entity status to reflect current step
        WorkflowEngine._update_entity_status_from_step(workflow_instance, step)

        # Trigger configured notifications for step assignment
        WorkflowNotifications.trigger_configured_notifications(
            step_execution, "assignment"
        )

        return step_execution

    @staticmethod
    def _handle_step_approval(
        workflow_instance: WorkflowInstance,
        step_execution: WorkflowStepExecution,
        actioned_by: User,
    ) -> Dict[str, Any]:
        """Handle approval of a step - move to next or complete workflow"""
        current_step_order = step_execution.workflow_step.step_order

        # Find next step
        next_step = (
            workflow_instance.workflow_template.steps.filter(
                step_order__gt=current_step_order
            )
            .order_by("step_order")
            .first()
        )

        if next_step:
            # Move to next step
            workflow_instance.current_step_order = next_step.step_order
            workflow_instance.save()

            # Start next step
            result = WorkflowEngine._start_step(
                workflow_instance, next_step, actioned_by
            )

            # If _start_step returned a dict (from recursive _handle_step_approval), use that
            if isinstance(result, dict):
                return result

            # Ensure entity status is updated to reflect current pending step
            # This is necessary because _start_step may return early in some cases
            # without updating the entity status (e.g., existing execution, race conditions)
            WorkflowEngine._update_entity_status_from_step(workflow_instance, next_step)

            return {
                "success": True,
                "workflow_status": "in_progress",
                "next_step": next_step.step_name,
            }
        else:
            # No more steps - complete workflow
            workflow_instance.status = "approved"
            workflow_instance.completed_at = timezone.now()
            workflow_instance.save()

            # Update entity status
            WorkflowEngine._update_entity_status(workflow_instance, "Approved")

            # Log completion
            WorkflowAuditLog.objects.create(
                workflow_instance=workflow_instance,
                action_type="approved",
                action_description="Workflow completed - all steps approved",
                performed_by=actioned_by,
            )

            # Send workflow completed notification
            WorkflowNotifications.notify_workflow_completed(workflow_instance)

            return {"success": True, "workflow_status": "approved", "completed": True}

    @staticmethod
    def _handle_step_rejection(
        workflow_instance: WorkflowInstance,
        step_execution: WorkflowStepExecution,
        actioned_by: User,
        comments: Optional[str],
    ) -> Dict[str, Any]:
        """Handle rejection of a step - cancel workflow"""
        # Mark all pending steps as skipped
        workflow_instance.step_executions.filter(status="pending").exclude(
            id=step_execution.id
        ).update(
            status="skipped",
            action_date=timezone.now(),
            comments="Skipped due to workflow rejection",
        )

        # Update workflow instance
        workflow_instance.status = "rejected"
        workflow_instance.completed_at = timezone.now()
        workflow_instance.save()

        # Update entity status
        WorkflowEngine._update_entity_status(workflow_instance, "Rejected")

        # Log rejection
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type="rejected",
            action_description=f"Workflow rejected at step '{step_execution.workflow_step.step_name}': {comments}",
            performed_by=actioned_by,
        )

        return {
            "success": True,
            "workflow_status": "rejected",
            "rejected_at_step": step_execution.workflow_step.step_name,
        }

    @staticmethod
    def _is_user_authorized(step_execution: WorkflowStepExecution, user: User) -> bool:
        """Check if user is authorized to action this step.

        IMPORTANT: When a specific approver is selected (assigned_to is set),
        ONLY that user (or admin/delegated users) can approve. Role-based
        matching is only used when no specific user is assigned.
        """
        # Admin override - workflow managers can approve any step
        if user.is_superuser or can_manage(user, "workflow"):
            return True

        # Check if user is directly assigned (specific approver was selected)
        if step_execution.assigned_to == user:
            return True

        # If a specific approver is assigned (assigned_to is NOT null),
        # only that user can approve - skip role-based matching
        if step_execution.assigned_to is not None:
            # Only check delegations since assigned_to is set but doesn't match current user
            active_delegations = (
                step_execution.delegations.filter(delegated_to=user, is_active=True)
                .filter(
                    models.Q(expires_at__isnull=True)
                    | models.Q(expires_at__gt=timezone.now())
                )
                .exists()
            )
            return active_delegations

        # Role-based matching - only when NO specific user is assigned (assigned_to is NULL)
        if (
            hasattr(user, "role")
            and user.role
            and step_execution.workflow_step.approver_role
        ):
            from accounts.models import Role

            approver_role = step_execution.workflow_step.approver_role

            # Try to match by UUID first
            try:
                role = Role.objects.get(id=approver_role)
                if user.role.id == role.id:
                    return True
            except (Role.DoesNotExist, ValueError):
                pass

            # Also check if approver_role is a string name (legacy support)
            if isinstance(approver_role, str):
                # Check by role name
                if user.role.name == approver_role:
                    return True
                # Check if user's role UUID matches the string
                if str(user.role.id) == approver_role:
                    return True

        # Check for active delegation
        active_delegations = (
            step_execution.delegations.filter(delegated_to=user, is_active=True)
            .filter(
                models.Q(expires_at__isnull=True)
                | models.Q(expires_at__gt=timezone.now())
            )
            .exists()
        )

        return active_delegations

    @staticmethod
    def _find_user_by_permission(
        permission_name: str, department: Optional[str] = None
    ) -> Optional[User]:
        """
        Find a user with the specified permission (PREFERRED METHOD)

        Args:
            permission_name: Permission name (e.g., 'approve_transport', 'approve_trf')
            department: Optional department for department-specific approvals

        Returns:
            User: First active user with the permission, or None
        """
        from accounts.models import Permission

        try:
            permission = Permission.objects.get(name=permission_name)

            # Get all roles that have this permission
            roles_with_permission = permission.role_set.all()

            if not roles_with_permission.exists():
                logger.warning(f" No roles found with permission '{permission_name}'")
                return None

            # For department-specific permissions (approvals), filter by department
            if department and permission_name.startswith("approve_"):
                user = User.objects.filter(
                    role__in=roles_with_permission,
                    department=department,
                    status="Active",
                ).first()
            else:
                # For org-wide permissions (processing, admin)
                user = User.objects.filter(
                    role__in=roles_with_permission, status="Active"
                ).first()

            if user:
                logger.info(
                    f" Found user {user.email} with permission '{permission_name}'"
                )
            else:
                logger.warning(
                    f" No active users found with permission '{permission_name}'"
                )

            return user
        except Permission.DoesNotExist:
            logger.error(f" Permission '{permission_name}' not found")
            return None

    @staticmethod
    def _find_user_by_role(
        role_identifier: str, department: Optional[str] = None
    ) -> Optional[User]:
        """
        Find a user with the specified role [DEPRECATED - use _find_user_by_permission instead]

        Kept for backward compatibility with existing workflows.

        Args:
            role_identifier: Either a role UUID or role name string
            department: Optional department filter
        """
        from accounts.models import Role

        try:
            # Try to get role by UUID first (new workflow templates use UUIDs)
            try:
                role = Role.objects.get(id=role_identifier)
            except (Role.DoesNotExist, ValueError):
                # Fallback: try by name (legacy workflow templates)
                role = Role.objects.get(name=role_identifier)

            # For department-specific roles, filter by department
            if department and role.name in ["Department Focal", "Line Manager"]:
                user = User.objects.filter(
                    role=role, department=department, status="Active"
                ).first()
            else:
                # For org-wide roles (HOD, CEO, etc.)
                user = User.objects.filter(role=role, status="Active").first()

            if user:
                logger.info(
                    f" Found user {user.email} with role '{role.name}' (ID: {role.id})"
                )
            else:
                logger.warning(f" No active users found with role '{role.name}'")

            return user
        except Role.DoesNotExist:
            logger.error(f" Role not found: {role_identifier}")
            return None

    @staticmethod
    def _update_entity_status(workflow_instance: WorkflowInstance, status: str):
        """Update the status of the related entity"""
        entity = workflow_instance.content_object
        if entity and hasattr(entity, "status"):
            entity.status = status
            entity.save(update_fields=["status"])

    @staticmethod
    def _update_entity_status_from_step(
        workflow_instance: WorkflowInstance, step: WorkflowStep
    ):
        """Update entity status to reflect current workflow step"""
        from accounts.models import Role

        entity = workflow_instance.content_object
        if entity and hasattr(entity, "status"):
            old_status = entity.status
            new_status = None

            # Generate status based on approver role
            if step.approver_role:
                # approver_role is stored as UUID, need to get role name
                try:
                    role = Role.objects.get(id=step.approver_role)
                    new_status = f"Pending {role.name}"
                except Role.DoesNotExist:
                    logger.warning(
                        f"Role not found for approver_role '{step.approver_role}' in step '{step.step_name}'"
                    )
                    new_status = "Pending Approval"
            else:
                # No approver_role set, use step name as fallback
                if step.step_name:
                    new_status = f"Pending {step.step_name}"
                else:
                    new_status = "Pending Approval"

            entity.status = new_status
            entity.save(update_fields=["status"])
            logger.info(
                f"Updated entity status: '{old_status}' -> '{new_status}' (step: {step.step_name}, step_order: {step.step_order})"
            )
        else:
            logger.warning(
                f"Could not update entity status - entity: {entity}, has_status: {hasattr(entity, 'status') if entity else 'N/A'}"
            )

    @staticmethod
    def check_and_escalate_overdue_steps():
        """
        Background task to check for overdue steps and escalate them.
        Should be run periodically (e.g., hourly via Celery)
        """
        now = timezone.now()

        # Find overdue steps
        overdue_steps = WorkflowStepExecution.objects.filter(
            status="pending",
            escalation_date__isnull=False,
            escalation_date__lte=now,
            is_escalated=False,
        ).select_related("workflow_instance", "workflow_step")

        for step_execution in overdue_steps:
            # Mark as escalated
            step_execution.is_escalated = True
            step_execution.is_overdue = True
            step_execution.save()

            # Log escalation
            WorkflowAuditLog.objects.create(
                workflow_instance=step_execution.workflow_instance,
                action_type="escalated",
                action_description=f"Step '{step_execution.workflow_step.step_name}' escalated due to timeout",
                performed_by=None,
            )

            # TODO: Send escalation notification
            # NotificationService.send_escalation_notification(step_execution)

        return len(overdue_steps)
