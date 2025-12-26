"""
Workflow Services - Helper classes for workflow operations
ADDITIVE - Provides new functionality without modifying existing code
"""
from typing import List, Dict, Set
from django.contrib.auth import get_user_model

User = get_user_model()


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
