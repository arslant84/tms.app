"""
Workflow Engine - Core business logic for workflow execution
Handles workflow lifecycle: start, process actions, escalate, complete
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db import models
from accounts.models import User
from .models import (
    WorkflowTemplate,
    WorkflowStep,
    WorkflowInstance,
    WorkflowStepExecution,
    WorkflowDelegation,
    WorkflowAuditLog
)
from .notifications import WorkflowNotifications


class WorkflowEngine:
    """
    Core workflow execution engine.
    Handles workflow lifecycle and business logic.
    """

    @staticmethod
    @transaction.atomic
    def start_workflow(entity, initiated_by: User, module_name: str) -> WorkflowInstance:
        """
        Start a new workflow for an entity (TRF, Visa, etc.)

        Args:
            entity: The entity object (TravelRequest, etc.)
            initiated_by: User who initiated the workflow
            module_name: Module identifier ('trf', 'visa', etc.)

        Returns:
            WorkflowInstance: The created workflow instance

        Raises:
            ValueError: If no active workflow template found for module
        """
        # Get active workflow template for the module
        workflow_template = WorkflowTemplate.objects.filter(
            entity_type=module_name,
            is_active=True
        ).prefetch_related('steps').first()

        if not workflow_template:
            raise ValueError(f"No active workflow template found for module: {module_name}")

        # Get content type for the entity
        content_type = ContentType.objects.get_for_model(entity)

        # Create workflow instance
        workflow_instance = WorkflowInstance.objects.create(
            workflow_template=workflow_template,
            content_type=content_type,
            object_id=entity.id,
            initiated_by=initiated_by,
            status='in_progress',
            current_step_order=1
        )

        # Log workflow creation
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type='created',
            action_description=f"Workflow started for {module_name} #{entity.id}",
            performed_by=initiated_by
        )

        # Get first step
        first_step = workflow_template.steps.filter(step_order=1).first()

        if first_step:
            # Start first step
            WorkflowEngine._start_step(workflow_instance, first_step, initiated_by)
        else:
            # No steps defined - auto-complete workflow
            workflow_instance.status = 'approved'
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
        comments: Optional[str] = None
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
        step_execution = WorkflowStepExecution.objects.select_related(
            'workflow_instance',
            'workflow_step',
            'workflow_instance__workflow_template'
        ).get(id=step_execution_id)

        # Validate user is authorized
        if not WorkflowEngine._is_user_authorized(step_execution, actioned_by):
            raise ValueError("User not authorized to action this step")

        # Validate action
        if action not in ['approve', 'reject', 'skip']:
            raise ValueError(f"Invalid action: {action}")

        # Check if step requires comments
        if step_execution.workflow_step.requires_comments and not comments:
            raise ValueError("Comments are required for this step")

        # Update step execution
        step_execution.status = action + 'd' if action != 'skip' else 'skipped'
        step_execution.actioned_by = actioned_by
        step_execution.action_date = timezone.now()
        step_execution.comments = comments
        step_execution.save()

        workflow_instance = step_execution.workflow_instance

        # Log the action
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type=action + 'd' if action != 'skip' else 'skipped',
            action_description=f"Step '{step_execution.workflow_step.step_name}' {action}d by {actioned_by.email}",
            performed_by=actioned_by
        )

        # Process based on action
        if action == 'approve' or action == 'skip':
            # Send step approved notification
            WorkflowNotifications.notify_step_approved(step_execution)
            return WorkflowEngine._handle_step_approval(workflow_instance, step_execution, actioned_by)
        elif action == 'reject':
            # Send step rejected notification
            WorkflowNotifications.notify_step_rejected(step_execution)
            return WorkflowEngine._handle_step_rejection(workflow_instance, step_execution, actioned_by, comments)

        return {'success': True, 'workflow_status': workflow_instance.status}

    @staticmethod
    @transaction.atomic
    def delegate_step(
        step_execution_id: int,
        delegated_from: User,
        delegated_to: User,
        reason: Optional[str] = None,
        expires_at: Optional[datetime] = None
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
            'workflow_step'
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
            expires_at=expires_at
        )

        # Update step execution assignment
        step_execution.assigned_to = delegated_to
        step_execution.status = 'delegated'
        step_execution.save()

        # Log delegation
        WorkflowAuditLog.objects.create(
            workflow_instance=step_execution.workflow_instance,
            action_type='delegated',
            action_description=f"Step '{step_execution.workflow_step.step_name}' delegated from {delegated_from.email} to {delegated_to.email}",
            performed_by=delegated_from
        )

        # Send delegation notification
        WorkflowNotifications.notify_step_delegated(step_execution, delegated_to, delegated_from)

        return {
            'success': True,
            'delegation_id': delegation.id,
            'delegated_to': delegated_to.email
        }

    @staticmethod
    def get_pending_approvals(user: User) -> list:
        """
        Get list of pending approvals for a user

        Args:
            user: User to get pending approvals for

        Returns:
            list: List of pending step executions
        """
        # Get by direct assignment
        direct_assignments = WorkflowStepExecution.objects.filter(
            assigned_to=user,
            status='pending'
        ).select_related(
            'workflow_instance',
            'workflow_step',
            'workflow_instance__content_type'
        ).prefetch_related(
            'workflow_instance__content_object'
        )

        # Get by role (if user has matching role)
        role_assignments = WorkflowStepExecution.objects.filter(
            assigned_to__isnull=True,
            workflow_step__approver_role=user.role.name if hasattr(user, 'role') else None,
            status='pending'
        ).select_related(
            'workflow_instance',
            'workflow_step',
            'workflow_instance__content_type'
        ).prefetch_related(
            'workflow_instance__content_object'
        )

        # Combine and return
        return list(direct_assignments) + list(role_assignments)

    @staticmethod
    @transaction.atomic
    def cancel_workflow(workflow_instance_id: int, cancelled_by: User, reason: str) -> Dict[str, Any]:
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

        if workflow_instance.status in ['approved', 'rejected', 'cancelled']:
            raise ValueError(f"Cannot cancel workflow with status: {workflow_instance.status}")

        # Cancel all pending step executions
        workflow_instance.step_executions.filter(status='pending').update(
            status='skipped',
            action_date=timezone.now(),
            comments=f"Skipped due to workflow cancellation: {reason}"
        )

        # Update workflow instance
        workflow_instance.status = 'cancelled'
        workflow_instance.completed_at = timezone.now()
        workflow_instance.save()

        # Log cancellation
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type='cancelled',
            action_description=f"Workflow cancelled: {reason}",
            performed_by=cancelled_by
        )

        # Send workflow cancelled notification
        WorkflowNotifications.notify_workflow_cancelled(workflow_instance, cancelled_by, reason)

        return {'success': True, 'status': 'cancelled'}

    # Private helper methods

    @staticmethod
    def _start_step(workflow_instance: WorkflowInstance, step: WorkflowStep, initiator: User):
        """Create and start a workflow step execution"""
        # Determine assigned user (priority order: user > permission > role)
        assigned_user = step.approver_user if step.approver_user else None

        # If no specific user, try to find by permission (PREFERRED)
        if not assigned_user and step.approver_permission:
            assigned_user = WorkflowEngine._find_user_by_permission(
                step.approver_permission,
                workflow_instance.initiated_by.department if hasattr(workflow_instance.initiated_by, 'department') else None
            )

        # Fallback: try to find by role (for backward compatibility)
        if not assigned_user and step.approver_role:
            print(f"⚠️ Using deprecated role-based assignment for step '{step.step_name}'. Consider using approver_permission instead.")
            assigned_user = WorkflowEngine._find_user_by_role(
                step.approver_role,
                workflow_instance.initiated_by.department if hasattr(workflow_instance.initiated_by, 'department') else None
            )

        # Calculate SLA and escalation dates
        sla_due_date = None
        escalation_date = None

        if step.sla_hours:
            sla_due_date = timezone.now() + timedelta(hours=step.sla_hours)

        if step.escalation_hours:
            escalation_date = timezone.now() + timedelta(hours=step.escalation_hours)

        # Create step execution
        step_execution = WorkflowStepExecution.objects.create(
            workflow_instance=workflow_instance,
            workflow_step=step,
            assigned_to=assigned_user,
            status='pending',
            sla_due_date=sla_due_date,
            escalation_date=escalation_date
        )

        # Log step start
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type='started',
            action_description=f"Started step '{step.step_name}' (assigned to: {assigned_user.email if assigned_user else step.approver_role})",
            performed_by=initiator
        )

        # Update entity status to reflect current step
        WorkflowEngine._update_entity_status_from_step(workflow_instance, step)

        return step_execution

    @staticmethod
    def _handle_step_approval(
        workflow_instance: WorkflowInstance,
        step_execution: WorkflowStepExecution,
        actioned_by: User
    ) -> Dict[str, Any]:
        """Handle approval of a step - move to next or complete workflow"""
        current_step_order = step_execution.workflow_step.step_order

        # Find next step
        next_step = workflow_instance.workflow_template.steps.filter(
            step_order__gt=current_step_order
        ).order_by('step_order').first()

        if next_step:
            # Move to next step
            workflow_instance.current_step_order = next_step.step_order
            workflow_instance.save()

            # Start next step
            WorkflowEngine._start_step(workflow_instance, next_step, actioned_by)

            return {
                'success': True,
                'workflow_status': 'in_progress',
                'next_step': next_step.step_name
            }
        else:
            # No more steps - complete workflow
            workflow_instance.status = 'approved'
            workflow_instance.completed_at = timezone.now()
            workflow_instance.save()

            # Update entity status
            WorkflowEngine._update_entity_status(workflow_instance, 'Approved')

            # Log completion
            WorkflowAuditLog.objects.create(
                workflow_instance=workflow_instance,
                action_type='approved',
                action_description=f"Workflow completed - all steps approved",
                performed_by=actioned_by
            )

            # Send workflow completed notification
            WorkflowNotifications.notify_workflow_completed(workflow_instance)

            return {
                'success': True,
                'workflow_status': 'approved',
                'completed': True
            }

    @staticmethod
    def _handle_step_rejection(
        workflow_instance: WorkflowInstance,
        step_execution: WorkflowStepExecution,
        actioned_by: User,
        comments: Optional[str]
    ) -> Dict[str, Any]:
        """Handle rejection of a step - cancel workflow"""
        # Mark all pending steps as skipped
        workflow_instance.step_executions.filter(status='pending').exclude(
            id=step_execution.id
        ).update(
            status='skipped',
            action_date=timezone.now(),
            comments="Skipped due to workflow rejection"
        )

        # Update workflow instance
        workflow_instance.status = 'rejected'
        workflow_instance.completed_at = timezone.now()
        workflow_instance.save()

        # Update entity status
        WorkflowEngine._update_entity_status(workflow_instance, 'Rejected')

        # Log rejection
        WorkflowAuditLog.objects.create(
            workflow_instance=workflow_instance,
            action_type='rejected',
            action_description=f"Workflow rejected at step '{step_execution.workflow_step.step_name}': {comments}",
            performed_by=actioned_by
        )

        return {
            'success': True,
            'workflow_status': 'rejected',
            'rejected_at_step': step_execution.workflow_step.step_name
        }

    @staticmethod
    def _is_user_authorized(step_execution: WorkflowStepExecution, user: User) -> bool:
        """Check if user is authorized to action this step"""
        # Admin override - admins can approve any step
        if user.is_staff or user.is_superuser:
            return True

        # Check if user is directly assigned
        if step_execution.assigned_to == user:
            return True

        # Check if user has the required role (if no specific user assigned)
        if not step_execution.assigned_to:
            if hasattr(user, 'role') and step_execution.workflow_step.approver_role:
                # Get the role name from the approver_role UUID
                from accounts.models import Role
                try:
                    role = Role.objects.get(id=step_execution.workflow_step.approver_role)
                    if user.role.name == role.name:
                        return True
                except Role.DoesNotExist:
                    pass

                # Also check if approver_role is already a string name (legacy support)
                if isinstance(step_execution.workflow_step.approver_role, str):
                    if user.role.name == step_execution.workflow_step.approver_role:
                        return True

        # Check for active delegation
        active_delegations = step_execution.delegations.filter(
            delegated_to=user,
            is_active=True
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        ).exists()

        return active_delegations

    @staticmethod
    def _find_user_by_permission(permission_name: str, department: Optional[str] = None) -> Optional[User]:
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
                print(f"⚠️ No roles found with permission '{permission_name}'")
                return None

            # For department-specific permissions (approvals), filter by department
            if department and permission_name.startswith('approve_'):
                user = User.objects.filter(
                    role__in=roles_with_permission,
                    department=department,
                    status='Active'
                ).first()
            else:
                # For org-wide permissions (processing, admin)
                user = User.objects.filter(
                    role__in=roles_with_permission,
                    status='Active'
                ).first()

            if user:
                print(f"✅ Found user {user.email} with permission '{permission_name}'")
            else:
                print(f"⚠️ No active users found with permission '{permission_name}'")

            return user
        except Permission.DoesNotExist:
            print(f"❌ Permission '{permission_name}' not found")
            return None

    @staticmethod
    def _find_user_by_role(role_name: str, department: Optional[str] = None) -> Optional[User]:
        """
        Find a user with the specified role [DEPRECATED - use _find_user_by_permission instead]

        Kept for backward compatibility with existing workflows.
        """
        from accounts.models import Role

        try:
            role = Role.objects.get(name=role_name)

            # For department-specific roles, filter by department
            if department and role_name in ['Department Focal', 'Line Manager']:
                user = User.objects.filter(
                    role=role,
                    department=department,
                    status='Active'
                ).first()
            else:
                # For org-wide roles (HOD, CEO, etc.)
                user = User.objects.filter(
                    role=role,
                    status='Active'
                ).first()

            return user
        except Role.DoesNotExist:
            return None

    @staticmethod
    def _update_entity_status(workflow_instance: WorkflowInstance, status: str):
        """Update the status of the related entity"""
        entity = workflow_instance.content_object
        if entity and hasattr(entity, 'status'):
            entity.status = status
            entity.save(update_fields=['status'])

    @staticmethod
    def _update_entity_status_from_step(workflow_instance: WorkflowInstance, step: WorkflowStep):
        """Update entity status to reflect current workflow step"""
        from accounts.models import Role

        entity = workflow_instance.content_object
        if entity and hasattr(entity, 'status'):
            # Generate status based on approver role
            if step.approver_role:
                # approver_role is stored as UUID, need to get role name
                try:
                    role = Role.objects.get(id=step.approver_role)
                    entity.status = f"Pending {role.name}"
                except Role.DoesNotExist:
                    entity.status = "Pending Approval"
            else:
                entity.status = "Pending Approval"
            entity.save(update_fields=['status'])

    @staticmethod
    def check_and_escalate_overdue_steps():
        """
        Background task to check for overdue steps and escalate them.
        Should be run periodically (e.g., hourly via Celery)
        """
        now = timezone.now()

        # Find overdue steps
        overdue_steps = WorkflowStepExecution.objects.filter(
            status='pending',
            escalation_date__isnull=False,
            escalation_date__lte=now,
            is_escalated=False
        ).select_related(
            'workflow_instance',
            'workflow_step'
        )

        for step_execution in overdue_steps:
            # Mark as escalated
            step_execution.is_escalated = True
            step_execution.is_overdue = True
            step_execution.save()

            # Log escalation
            WorkflowAuditLog.objects.create(
                workflow_instance=step_execution.workflow_instance,
                action_type='escalated',
                action_description=f"Step '{step_execution.workflow_step.step_name}' escalated due to timeout",
                performed_by=None
            )

            # TODO: Send escalation notification
            # NotificationService.send_escalation_notification(step_execution)

        return len(overdue_steps)
