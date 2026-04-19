"""
Workflow Services - Helper classes for workflow operations
ADDITIVE - Provides new functionality without modifying existing code
"""
import logging
from typing import List, Dict, Set, Optional
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
        from workflows.models import WorkflowInstance, WorkflowStepExecution
        from django.utils import timezone

        content_type = ContentType.objects.get_for_model(model_class)

        # Build query for pending step executions
        # 1. Direct assignment to user (specific approver was selected)
        direct_assignment_q = Q(assigned_to=user)

        # 2. Role-based matching ONLY when no specific user is assigned (assigned_to is NULL)
        role_match_q = Q()
        if hasattr(user, 'role') and user.role:
            # Only match by role when assigned_to is NULL (no specific approver selected)
            role_match_q = Q(assigned_to__isnull=True) & (
                Q(workflow_step__approver_role=str(user.role.id)) |
                Q(workflow_step__approver_role=user.role.name)
            )

        # Get pending step executions that match user
        pending_steps = WorkflowStepExecution.objects.filter(
            status='pending',
            workflow_instance__content_type=content_type,
            workflow_instance__status='in_progress'
        ).filter(
            direct_assignment_q | role_match_q
        )

        # Get entity IDs from workflow instances
        entity_ids = list(pending_steps.values_list('workflow_instance__object_id', flat=True))

        # 3. Also check for active delegations
        delegated_steps = WorkflowStepExecution.objects.filter(
            status='pending',
            workflow_instance__content_type=content_type,
            workflow_instance__status='in_progress',
            delegations__delegated_to=user,
            delegations__is_active=True
        ).filter(
            Q(delegations__expires_at__isnull=True) | Q(delegations__expires_at__gt=timezone.now())
        )

        delegated_ids = list(delegated_steps.values_list('workflow_instance__object_id', flat=True))

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
        from workflows.models import WorkflowInstance, WorkflowStepExecution
        from django.utils import timezone

        # Superusers can approve everything
        if user.is_superuser:
            return True

        content_type = ContentType.objects.get_for_model(entity)

        # Get active workflow instance for this entity
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type,
            object_id=entity.id,
            status='in_progress'
        ).first()

        if not workflow_instance:
            return False

        # Get current pending step execution
        current_step = workflow_instance.step_executions.filter(
            status='pending'
        ).order_by('workflow_step__step_order').first()

        if not current_step:
            return False

        # Check direct assignment
        if current_step.assigned_to == user:
            return True

        # Check role match
        if hasattr(user, 'role') and user.role and current_step.workflow_step.approver_role:
            approver_role_value = current_step.workflow_step.approver_role

            # Compare by UUID
            if str(user.role.id) == approver_role_value:
                return True

            # Compare by name (legacy)
            if user.role.name == approver_role_value:
                return True

        # Check active delegation
        active_delegation = current_step.delegations.filter(
            delegated_to=user,
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).exists()

        return active_delegation

    @staticmethod
    def get_eligible_approvers_for_step(
        workflow_step,
        requester: User
    ) -> QuerySet:
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
                id=workflow_step.approver_user_id,
                status='Active'
            )

        department = getattr(requester, 'department', None)

        # Try permission-based lookup (preferred)
        if workflow_step.approver_permission:
            try:
                permission = Permission.objects.get(name=workflow_step.approver_permission)
                roles_with_permission = permission.role_set.all()

                queryset = User.objects.filter(
                    role__in=roles_with_permission,
                    status='Active'
                )

                # Filter by department for approval permissions
                if department and workflow_step.approver_permission.startswith('approve_'):
                    queryset = queryset.filter(department=department)

                return queryset.select_related('role', 'department').order_by('name')

            except Permission.DoesNotExist:
                logger.warning(f"Permission '{workflow_step.approver_permission}' not found")

        # Fallback to role-based lookup
        if workflow_step.approver_role:
            try:
                # Try to get role by UUID first
                try:
                    role = Role.objects.get(id=workflow_step.approver_role)
                except (Role.DoesNotExist, ValueError):
                    # Fallback: try by name (legacy)
                    role = Role.objects.get(name=workflow_step.approver_role)

                queryset = User.objects.filter(role=role, status='Active')

                # Filter by department for department-specific roles
                if department and role.name in ['Department Focal', 'Line Manager']:
                    dept_filtered = queryset.filter(department=department)
                    # Fall back to all users with this role when no dept match found
                    # (covers cross-department requests or unassigned departments)
                    if dept_filtered.exists():
                        queryset = dept_filtered

                return queryset.select_related('role', 'department').order_by('name')

            except Role.DoesNotExist:
                logger.warning(f"Role '{workflow_step.approver_role}' not found")

        return User.objects.none()

    @staticmethod
    def get_eligible_approvers_for_template(
        entity_type: str,
        requester: User
    ) -> Dict[int, List[Dict]]:
        """
        Get eligible approvers for all steps in a workflow template.

        Args:
            entity_type: The entity type (e.g., 'travelrequest', 'visaapplication')
            requester: The user submitting the request

        Returns:
            Dict mapping step_order to list of eligible approvers with their details
        """
        from workflows.models import WorkflowTemplate

        # Use case-insensitive matching for entity_type
        template = WorkflowTemplate.objects.filter(
            entity_type__iexact=entity_type,
            is_active=True
        ).prefetch_related('steps').first()

        if not template:
            return {}

        result = {}
        for step in template.steps.all().order_by('step_order'):
            approvers = WorkflowApprovalHelper.get_eligible_approvers_for_step(step, requester)
            result[step.step_order] = [
                {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.get_full_name(),
                    'department': user.department.name if user.department else None,
                    'role': user.role.name if user.role else None,
                }
                for user in approvers
            ]

        return result


class WorkflowNotificationRecipientResolver:
    """
    Resolves notification recipients based on workflow step notification configuration.
    This is completely new functionality that doesn't affect existing workflows.
    """

    @staticmethod
    def resolve_all_recipients(config, step_execution) -> Dict[str, List[User]]:
        """
        Resolve all recipients (TO, CC, BCC) for a notification configuration.

        Args:
            config: WorkflowStepNotificationConfig instance
            step_execution: WorkflowStepExecution instance

        Returns:
            dict: {
                'to': [User, User, ...],
                'cc': [User, User, ...],
                'bcc': [User, User, ...]
            }
        """
        return {
            'to': WorkflowNotificationRecipientResolver.resolve_to_recipients(config, step_execution),
            'cc': WorkflowNotificationRecipientResolver.resolve_cc_recipients(config, step_execution),
            'bcc': WorkflowNotificationRecipientResolver.resolve_bcc_recipients(config, step_execution)
        }

    @staticmethod
    def resolve_to_recipients(config, step_execution) -> List[User]:
        """
        Resolve primary (TO) recipients based on recipient_type.

        Args:
            config: WorkflowStepNotificationConfig instance
            step_execution: WorkflowStepExecution instance

        Returns:
            list: List of User objects
        """
        recipients = set()  # Use set to avoid duplicates

        if config.recipient_type == 'approver':
            # Current step approver
            if step_execution.assigned_to:
                recipients.add(step_execution.assigned_to)

        elif config.recipient_type == 'requestor':
            # Original requestor
            recipients.add(step_execution.workflow_instance.initiated_by)

        elif config.recipient_type == 'next_approver':
            # Next step approver
            next_step = step_execution.workflow_instance.step_executions.filter(
                workflow_step__step_order=step_execution.workflow_step.step_order + 1,
                status='pending'
            ).first()
            if next_step and next_step.assigned_to:
                recipients.add(next_step.assigned_to)

        elif config.recipient_type == 'previous_approvers':
            # All previous approvers
            previous_steps = step_execution.workflow_instance.step_executions.filter(
                workflow_step__step_order__lt=step_execution.workflow_step.step_order
            )
            for step in previous_steps:
                if step.assigned_to:
                    recipients.add(step.assigned_to)

        elif config.recipient_type == 'all_approvers':
            # All approvers in workflow
            all_steps = step_execution.workflow_instance.step_executions.all()
            for step in all_steps:
                if step.assigned_to:
                    recipients.add(step.assigned_to)

        elif config.recipient_type == 'role':
            # Specific roles
            for role in config.recipient_roles.all():
                users = User.objects.filter(role=role, status='Active')
                recipients.update(users)

        elif config.recipient_type == 'user':
            # Specific users
            recipients.update(config.recipient_users.filter(status='Active'))

        elif config.recipient_type == 'department_head':
            # Department head (HOD of requestor's department)
            requestor = step_execution.workflow_instance.initiated_by
            if hasattr(requestor, 'department') and requestor.department:
                from accounts.models import Role
                hod_role = Role.objects.filter(name='HOD').first()
                if hod_role:
                    hod = User.objects.filter(
                        role=hod_role,
                        department=requestor.department,
                        status='Active'
                    ).first()
                    if hod:
                        recipients.add(hod)

        return list(recipients)

    @staticmethod
    def resolve_cc_recipients(config, step_execution) -> List[User]:
        """
        Resolve CC recipients based on configuration.

        Args:
            config: WorkflowStepNotificationConfig instance
            step_execution: WorkflowStepExecution instance

        Returns:
            list: List of User objects
        """
        recipients = set()

        # CC requestor
        if config.cc_requestor:
            recipients.add(step_execution.workflow_instance.initiated_by)

        # CC previous approvers
        if config.cc_previous_approvers:
            previous_steps = step_execution.workflow_instance.step_executions.filter(
                workflow_step__step_order__lt=step_execution.workflow_step.step_order
            )
            for step in previous_steps:
                if step.assigned_to:
                    recipients.add(step.assigned_to)

        # CC next approver
        if config.cc_next_approver:
            next_step = step_execution.workflow_instance.step_executions.filter(
                workflow_step__step_order=step_execution.workflow_step.step_order + 1
            ).first()
            if next_step and next_step.assigned_to:
                recipients.add(next_step.assigned_to)

        # CC specific roles
        for role in config.cc_roles.all():
            users = User.objects.filter(role=role, status='Active')
            recipients.update(users)

        # CC specific users
        recipients.update(config.cc_users.filter(status='Active'))

        return list(recipients)

    @staticmethod
    def resolve_bcc_recipients(config, step_execution) -> List[User]:
        """
        Resolve BCC recipients (typically for audit/compliance).

        Args:
            config: WorkflowStepNotificationConfig instance
            step_execution: WorkflowStepExecution instance

        Returns:
            list: List of User objects
        """
        recipients = set()

        # BCC specific roles
        for role in config.bcc_roles.all():
            users = User.objects.filter(role=role, status='Active')
            recipients.update(users)

        # BCC specific users
        recipients.update(config.bcc_users.filter(status='Active'))

        return list(recipients)
