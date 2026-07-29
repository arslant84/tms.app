"""
Workflow Services - Helper classes for workflow operations
ADDITIVE - Provides new functionality without modifying existing code
"""

import logging
from typing import Dict, List, Optional, Set

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet

User = get_user_model()
logger = logging.getLogger(__name__)


class WorkflowApprovalHelper:
    """
    Helper class for filtering entities that a user can approve based on workflow steps.
    Uses workflow-based filtering instead of hardcoded role-to-status mappings.
    """

    @staticmethod
    def get_pending_entity_ids_for_user(user, model_class) -> List:
        """
        Get IDs of entities pending approval for a specific user based on workflow step assignments.

        This checks:
        1. Direct assignment to the user (when a specific approver was selected)
        2. User's role UUID matching the step's approver_role (only when no specific user is assigned)
        3. Active delegations to the user

        IMPORTANT: When a specific approver is selected (assigned_to is set), ONLY that user
        should see the request. Role-based matching is only used when no specific user is assigned.

        Args:
            user: The user to check approvals for
            model_class: The Django model class (e.g., TravelRequest, VisaApplication)

        Returns:
            List of entity IDs that the user can approve
        """
        from django.utils import timezone
        from workflows.models import WorkflowInstance, WorkflowStepExecution

        content_type = ContentType.objects.get_for_model(model_class)

        # Build query for pending step executions
        # 1. Direct assignment to user (specific approver was selected)
        direct_assignment_q = Q(assigned_to=user)

        # 2. Role-based matching ONLY when no specific user is assigned (assigned_to is NULL)
        role_match_q = Q()
        if hasattr(user, "role") and user.role:
            # Only match by role when assigned_to is NULL (no specific approver selected)
            role_match_q = Q(assigned_to__isnull=True) & (
                Q(workflow_step__approver_role=str(user.role.id))
                | Q(workflow_step__approver_role=user.role.name)
            )

        # Get pending step executions that match user
        pending_steps = WorkflowStepExecution.objects.filter(
            status="pending",
            workflow_instance__content_type=content_type,
            workflow_instance__status="in_progress",
        ).filter(direct_assignment_q | role_match_q)

        # Get entity IDs from workflow instances
        entity_ids = list(
            pending_steps.values_list("workflow_instance__object_id", flat=True)
        )

        # 3. Also check for active delegations
        delegated_steps = WorkflowStepExecution.objects.filter(
            status="pending",
            workflow_instance__content_type=content_type,
            workflow_instance__status="in_progress",
            delegations__delegated_to=user,
            delegations__is_active=True,
        ).filter(
            Q(delegations__expires_at__isnull=True)
            | Q(delegations__expires_at__gt=timezone.now())
        )

        delegated_ids = list(
            delegated_steps.values_list("workflow_instance__object_id", flat=True)
        )

        # Combine and deduplicate
        all_ids = list(set(entity_ids + delegated_ids))

        return all_ids

    @staticmethod
    def can_user_approve_entity(user, entity) -> bool:
        """
        Check if a specific user can approve a specific entity based on workflow step.

        Args:
            user: The user to check
            entity: The entity instance (e.g., TravelRequest object)

        Returns:
            bool: True if user can approve this entity
        """
        from django.utils import timezone
        from workflows.models import WorkflowInstance, WorkflowStepExecution

        # Superusers can approve everything
        if user.is_superuser:
            return True

        content_type = ContentType.objects.get_for_model(entity)

        # Get active workflow instance for this entity
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type, object_id=entity.id, status="in_progress"
        ).first()

        if not workflow_instance:
            return False

        # Get current pending step execution
        current_step = (
            workflow_instance.step_executions.filter(status="pending")
            .order_by("workflow_step__step_order")
            .first()
        )

        if not current_step:
            return False

        # Check direct assignment
        if current_step.assigned_to == user:
            return True

        # Check role match
        if (
            hasattr(user, "role")
            and user.role
            and current_step.workflow_step.approver_role
        ):
            approver_role_value = current_step.workflow_step.approver_role

            # Compare by UUID
            if str(user.role.id) == approver_role_value:
                return True

            # Compare by name (legacy)
            if user.role.name == approver_role_value:
                return True

        # Check active delegation
        active_delegation = (
            current_step.delegations.filter(delegated_to=user, is_active=True)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
            .exists()
        )

        return active_delegation

    @staticmethod
    def get_eligible_approvers_for_step(workflow_step, requester: User) -> QuerySet:
        """
        Get all users eligible to approve a specific workflow step.

        Args:
            workflow_step: The workflow step to find approvers for
            requester: The user submitting the request (for department filtering)

        Returns:
            QuerySet of eligible User objects
        """
        from accounts.models import Permission, Role

        # If step has specific user assigned, return only that user
        if workflow_step.approver_user:
            return User.objects.filter(
                id=workflow_step.approver_user_id, status="Active"
            )

        department = getattr(requester, "department", None)

        # Try permission-based lookup (preferred)
        if workflow_step.approver_permission:
            try:
                permission = Permission.objects.get(
                    name=workflow_step.approver_permission
                )
                roles_with_permission = permission.role_set.all()

                queryset = User.objects.filter(
                    role__in=roles_with_permission, status="Active"
                )

                # Filter by department for approval permissions
                if department and workflow_step.approver_permission.startswith(
                    "approve_"
                ):
                    queryset = queryset.filter(department=department)

                return queryset.select_related("role", "department").order_by("name")

            except Permission.DoesNotExist:
                logger.warning(
                    f"Permission '{workflow_step.approver_permission}' not found"
                )

        # Fallback to role-based lookup
        if workflow_step.approver_role:
            try:
                # Try to get role by UUID first
                try:
                    role = Role.objects.get(id=workflow_step.approver_role)
                except (Role.DoesNotExist, ValueError):
                    # Fallback: try by name (legacy)
                    role = Role.objects.get(name=workflow_step.approver_role)

                queryset = User.objects.filter(role=role, status="Active")

                # Filter by department for department-specific roles
                if department and role.name in ["Department Focal", "Line Manager"]:
                    dept_filtered = queryset.filter(department=department)
                    # Fall back to all users with this role when no dept match found
                    # (covers cross-department requests or unassigned departments)
                    if dept_filtered.exists():
                        queryset = dept_filtered

                return queryset.select_related("role", "department").order_by("name")

            except Role.DoesNotExist:
                logger.warning(f"Role '{workflow_step.approver_role}' not found")

        return User.objects.none()
