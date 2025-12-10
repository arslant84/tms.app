"""
Notification triggers for workflow events.
Sends notifications when workflow instances change state.
"""

from notifications.services import NotificationService
from notifications.models import NotificationEventType


def _get_event_type(event_name):
    """Get NotificationEventType by name, returns None if not found"""
    try:
        return NotificationEventType.objects.get(name=event_name, is_active=True)
    except NotificationEventType.DoesNotExist:
        return None


class WorkflowNotifications:
    """
    Helper class for sending workflow-related notifications.
    """

    @staticmethod
    def notify_workflow_started(workflow_instance):
        """
        Send notification when a new workflow is started.

        Args:
            workflow_instance: WorkflowInstance that was started
        """
        try:
            # Notify the person who initiated the workflow
            NotificationService.create_notification(
                user=workflow_instance.initiated_by,
                title=f"Workflow Started: {workflow_instance.workflow_template.name}",
                message=f"Your {workflow_instance.workflow_template.entity_type} request has been submitted and the approval workflow has started.",
                event_type=_get_event_type('WORKFLOW_STARTED'),
                priority='normal',
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
                send_email=True
            )

            # Notify the first approver (if step executions exist)
            if workflow_instance.step_executions.exists():
                first_step = workflow_instance.step_executions.filter(
                    step_order=1,
                    status='pending'
                ).first()

                if first_step and first_step.assigned_to_user:
                    NotificationService.create_notification(
                        user=first_step.assigned_to_user,
                        title=f"New Approval Required: {workflow_instance.workflow_template.name}",
                        message=f"You have been assigned to approve {first_step.workflow_step.step_name} for a {workflow_instance.workflow_template.entity_type} request.",
                        event_type=_get_event_type('APPROVAL_REQUESTED'),
                        priority='high',
                        action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
                        send_email=True
                    )

            print(f"✅ Notifications sent for workflow start: {workflow_instance.id}")
        except Exception as e:
            print(f"❌ Failed to send workflow start notifications: {str(e)}")

    @staticmethod
    def notify_step_approved(step_execution):
        """
        Send notification when a workflow step is approved.

        Args:
            step_execution: WorkflowStepExecution that was approved
        """
        try:
            workflow_instance = step_execution.workflow_instance

            # Notify the requester
            NotificationService.create_notification(
                user=workflow_instance.initiated_by,
                title=f"Step Approved: {step_execution.workflow_step.step_name}",
                message=f"{step_execution.workflow_step.step_name} has been approved by {step_execution.actioned_by.get_full_name() if step_execution.actioned_by else 'Unknown'}. Your request is progressing.",
                event_type=_get_event_type('WORKFLOW_UPDATED'),
                priority='normal',
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
            send_email=True
            )

            # Notify the next approver (if exists)
            next_step = workflow_instance.step_executions.filter(
                step_order=step_execution.step_order + 1,
                status='pending'
            ).first()

            if next_step and next_step.assigned_to_user:
                NotificationService.create_notification(
                    user=next_step.assigned_to_user,
                    title=f"New Approval Required: {next_step.workflow_step.step_name}",
                    message=f"You have been assigned to approve {next_step.workflow_step.step_name} for a {workflow_instance.workflow_template.entity_type} request.",
                    event_type=_get_event_type('APPROVAL_REQUESTED'),
                    priority='high',
                    action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
                send_email=True
                )

            print(f"✅ Notifications sent for step approval: {step_execution.id}")
        except Exception as e:
            print(f"❌ Failed to send step approval notifications: {str(e)}")

    @staticmethod
    def notify_step_rejected(step_execution):
        """
        Send notification when a workflow step is rejected.

        Args:
            step_execution: WorkflowStepExecution that was rejected
        """
        try:
            workflow_instance = step_execution.workflow_instance

            # Notify the requester
            NotificationService.create_notification(
                user=workflow_instance.initiated_by,
                title=f"Request Rejected: {workflow_instance.workflow_template.name}",
                message=f"Your {workflow_instance.workflow_template.entity_type} request has been rejected at {step_execution.workflow_step.step_name}. Reason: {step_execution.comments or 'No reason provided'}",
                event_type=_get_event_type('WORKFLOW_REJECTED'),
                priority='urgent',
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
            send_email=True
            )

            print(f"✅ Notification sent for step rejection: {step_execution.id}")
        except Exception as e:
            print(f"❌ Failed to send step rejection notification: {str(e)}")

    @staticmethod
    def notify_step_delegated(step_execution, new_assignee):
        """
        Send notification when a workflow step is delegated.

        Args:
            step_execution: WorkflowStepExecution that was delegated
            new_assignee: User who received the delegation
        """
        try:
            workflow_instance = step_execution.workflow_instance

            # Notify the new assignee
            NotificationService.create_notification(
                user=new_assignee,
                title=f"Approval Delegated to You: {step_execution.workflow_step.step_name}",
                message=f"An approval for {workflow_instance.workflow_template.entity_type} has been delegated to you. Please review and take action.",
                event_type=_get_event_type('APPROVAL_DELEGATED'),
                priority='high',
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
            send_email=True
            )

            # Notify the requester
            NotificationService.create_notification(
                user=workflow_instance.initiated_by,
                title=f"Approval Delegated: {step_execution.workflow_step.step_name}",
                message=f"The approval step has been delegated to {new_assignee.get_full_name()}.",
                event_type=_get_event_type('WORKFLOW_UPDATED'),
                priority='normal',
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
            send_email=True
            )

            print(f"✅ Notifications sent for step delegation: {step_execution.id}")
        except Exception as e:
            print(f"❌ Failed to send step delegation notifications: {str(e)}")

    @staticmethod
    def notify_workflow_completed(workflow_instance):
        """
        Send notification when a workflow is completed.

        Args:
            workflow_instance: WorkflowInstance that was completed
        """
        try:
            # Notify the requester
            NotificationService.create_notification(
                user=workflow_instance.initiated_by,
                title=f"Request Approved: {workflow_instance.workflow_template.name}",
                message=f"Your {workflow_instance.workflow_template.entity_type} request has been fully approved! All approval steps are complete.",
                event_type=_get_event_type('WORKFLOW_APPROVED'),
                priority='high',
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
            send_email=True
            )

            print(f"✅ Notification sent for workflow completion: {workflow_instance.id}")
        except Exception as e:
            print(f"❌ Failed to send workflow completion notification: {str(e)}")

    @staticmethod
    def notify_workflow_cancelled(workflow_instance, cancelled_by, reason=None):
        """
        Send notification when a workflow is cancelled.

        Args:
            workflow_instance: WorkflowInstance that was cancelled
            cancelled_by: User who cancelled the workflow
            reason: Optional cancellation reason
        """
        try:
            # Notify the requester (if they're not the one who cancelled)
            if workflow_instance.initiated_by != cancelled_by:
                NotificationService.create_notification(
                    user=workflow_instance.initiated_by,
                    title=f"Request Cancelled: {workflow_instance.workflow_template.name}",
                    message=f"Your {workflow_instance.workflow_template.entity_type} request has been cancelled. {f'Reason: {reason}' if reason else ''}",
                    event_type=_get_event_type('WORKFLOW_CANCELLED'),
                    priority='normal',
                    action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
                send_email=True
                )

            print(f"✅ Notification sent for workflow cancellation: {workflow_instance.id}")
        except Exception as e:
            print(f"❌ Failed to send workflow cancellation notification: {str(e)}")
