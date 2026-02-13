"""
Notification triggers for workflow events.
Sends notifications when workflow instances change state.
"""
import logging
from notifications.services import NotificationService

logger = logging.getLogger(__name__)
from notifications.models import NotificationEventType, NotificationTemplate


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
            # Get first approver
            first_approver_name = "the approval team"
            if workflow_instance.step_executions.exists():
                first_step = workflow_instance.step_executions.filter(
                    workflow_step__step_order=1
                ).first()
                if first_step and first_step.assigned_to:
                    first_approver_name = first_step.assigned_to.get_full_name()

            # Notify the person who initiated the workflow
            NotificationService.create_notification(
                user=workflow_instance.initiated_by,
                title=f"Workflow Started: {workflow_instance.workflow_template.name}",
                message=f"Your {workflow_instance.workflow_template.entity_type} request has been submitted and the approval workflow has started.",
                event_type=_get_event_type('WORKFLOW_STARTED'),
                priority='normal',
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                additional_data={
                    'requestorName': workflow_instance.initiated_by.get_full_name(),
                    'requestType': workflow_instance.workflow_template.entity_type.title(),
                    'entityId': str(workflow_instance.object_id),
                    'approverName': first_approver_name,
                    'actionUrl': f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                },
                send_email=True
            )

            # Notify the first approver (if step executions exist)
            if workflow_instance.step_executions.exists():
                first_step = workflow_instance.step_executions.filter(
                    workflow_step__step_order=1,
                    status='pending'
                ).first()

                if first_step and first_step.assigned_to:
                    NotificationService.create_notification(
                        user=first_step.assigned_to,
                        title=f"New Approval Required: {workflow_instance.workflow_template.name}",
                        message=f"You have been assigned to approve {first_step.workflow_step.step_name} for a {workflow_instance.workflow_template.entity_type} request.",
                        event_type=_get_event_type('APPROVAL_REQUESTED'),
                        priority='high',
                        action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                        additional_data={
                            'approverName': first_step.assigned_to.get_full_name(),
                            'requestType': workflow_instance.workflow_template.entity_type.title(),
                            'entityId': str(workflow_instance.object_id),
                            'requestorName': workflow_instance.initiated_by.get_full_name(),
                            'dueDate': first_step.sla_due_date.strftime('%B %d, %Y at %I:%M %p') if first_step.sla_due_date else 'Not specified',
                            'urgencyHint': 'High priority' if getattr(first_step.workflow_step, 'is_urgent', False) else 'Normal priority',
                            'actionUrl': f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                        },
                        send_email=True
                    )
                else:
                    logger.warning(f" First step has no assigned user - notifications may not be sent")

            logger.info(f" Notifications sent for workflow start: {workflow_instance.id}")
        except Exception as e:
            logger.error(f" Failed to send workflow start notifications: {str(e)}")

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
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                additional_data={
                    'requestorName': workflow_instance.initiated_by.get_full_name(),
                    'requestType': workflow_instance.workflow_template.entity_type.title(),
                    'entityId': str(workflow_instance.object_id),
                    'approverName': step_execution.actioned_by.get_full_name() if step_execution.actioned_by else 'Unknown',
                    'stepName': step_execution.workflow_step.step_name,
                    'actionUrl': f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                },
                send_email=True
            )

            # Notify the next approver (if exists)
            next_step = workflow_instance.step_executions.filter(
                workflow_step__step_order=step_execution.workflow_step.step_order + 1,
                status='pending'
            ).first()

            if next_step and next_step.assigned_to:
                NotificationService.create_notification(
                    user=next_step.assigned_to,
                    title=f"New Approval Required: {next_step.workflow_step.step_name}",
                    message=f"You have been assigned to approve {next_step.workflow_step.step_name} for a {workflow_instance.workflow_template.entity_type} request.",
                    event_type=_get_event_type('APPROVAL_REQUESTED'),
                    priority='high',
                    action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                    additional_data={
                        'approverName': next_step.assigned_to.get_full_name(),
                        'requestType': workflow_instance.workflow_template.entity_type.title(),
                        'entityId': str(workflow_instance.object_id),
                        'requestorName': workflow_instance.initiated_by.get_full_name(),
                        'dueDate': next_step.sla_due_date.strftime('%B %d, %Y at %I:%M %p') if next_step.sla_due_date else 'Not specified',
                        'urgencyHint': 'High priority' if getattr(next_step.workflow_step, 'is_urgent', False) else 'Normal priority',
                        'actionUrl': f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                        'processorHint': f"Please review and approve {next_step.workflow_step.step_name}",
                    },
                    send_email=True
                )

            logger.info(f" Notifications sent for step approval: {step_execution.id}")
        except Exception as e:
            logger.error(f" Failed to send step approval notifications: {str(e)}")

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
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                additional_data={
                    'requestorName': workflow_instance.initiated_by.get_full_name(),
                    'requestType': workflow_instance.workflow_template.entity_type.title(),
                    'entityId': str(workflow_instance.object_id),
                    'approverName': step_execution.actioned_by.get_full_name() if step_execution.actioned_by else 'Unknown',
                    'rejectionReason': step_execution.comments or 'No reason provided',
                    'actionUrl': f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                },
                send_email=True
            )

            logger.info(f" Notification sent for step rejection: {step_execution.id}")
        except Exception as e:
            logger.error(f" Failed to send step rejection notification: {str(e)}")

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
            # Get the original assignee (delegator)
            delegator_name = step_execution.assigned_to.get_full_name() if step_execution.assigned_to else 'Previous approver'

            # Notify the new assignee
            NotificationService.create_notification(
                user=new_assignee,
                title=f"Approval Delegated to You: {step_execution.workflow_step.step_name}",
                message=f"An approval for {workflow_instance.workflow_template.entity_type} has been delegated to you. Please review and take action.",
                event_type=_get_event_type('APPROVAL_DELEGATED'),
                priority='high',
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                additional_data={
                    'approverName': new_assignee.get_full_name(),
                    'delegatorName': delegator_name,
                    'requestType': workflow_instance.workflow_template.entity_type.title(),
                    'entityId': str(workflow_instance.object_id),
                    'actionUrl': f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                },
                send_email=True
            )

            # Notify the requester
            NotificationService.create_notification(
                user=workflow_instance.initiated_by,
                title=f"Approval Delegated: {step_execution.workflow_step.step_name}",
                message=f"The approval step has been delegated to {new_assignee.get_full_name()}.",
                event_type=_get_event_type('WORKFLOW_UPDATED'),
                priority='normal',
                action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                additional_data={
                    'requestorName': workflow_instance.initiated_by.get_full_name(),
                    'requestType': workflow_instance.workflow_template.entity_type.title(),
                    'entityId': str(workflow_instance.object_id),
                    'approverName': new_assignee.get_full_name(),
                    'delegatorName': delegator_name,
                    'actionUrl': f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                },
                send_email=True
            )

            logger.info(f" Notifications sent for step delegation: {step_execution.id}")
        except Exception as e:
            logger.error(f" Failed to send step delegation notifications: {str(e)}")

    @staticmethod
    def notify_workflow_completed(workflow_instance):
        """
        Send notification when a workflow is completed (all approvals done).
        Checks for configured 'workflow_completed' notifications.

        Args:
            workflow_instance: WorkflowInstance that was completed
        """
        try:
            from .models import WorkflowStepNotificationConfig

            # Check if any step has workflow_completed notification configured
            workflow_steps = workflow_instance.workflow_template.steps.all()
            configs = WorkflowStepNotificationConfig.objects.filter(
                workflow_step__in=workflow_steps,
                event_type='workflow_completed',
                is_active=True
            )

            if configs.exists():
                logger.info(f" Found {configs.count()} workflow_completed notification config(s)")

                # Use last step execution for context
                last_step_execution = workflow_instance.step_executions.order_by('-workflow_step__step_order').first()

                if last_step_execution:
                    # Trigger configured notifications
                    WorkflowNotifications.trigger_configured_notifications(
                        last_step_execution, 'workflow_completed'
                    )
                else:
                    logger.warning(f" No step executions found for workflow {workflow_instance.id}")
            else:
                # Fall back to default notification (only to requestor)
                logger.info(f" No workflow_completed configs found, using default notification")

                # Get last approver for completion context
                last_step_execution = workflow_instance.step_executions.order_by('-workflow_step__step_order').first()
                processor_name = last_step_execution.actioned_by.get_full_name() if last_step_execution and last_step_execution.actioned_by else 'The approval team'

                from django.utils import timezone
                completion_date = timezone.now().strftime('%B %d, %Y at %I:%M %p')

                NotificationService.create_notification(
                    user=workflow_instance.initiated_by,
                    title=f"Request Approved: {workflow_instance.workflow_template.name}",
                    message=f"Your {workflow_instance.workflow_template.entity_type} request has been fully approved! All approval steps are complete.",
                    event_type=_get_event_type('WORKFLOW_APPROVED'),
                    priority='high',
                    action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                    additional_data={
                        'requestorName': workflow_instance.initiated_by.get_full_name(),
                        'requestType': workflow_instance.workflow_template.entity_type.title(),
                        'entityId': str(workflow_instance.object_id),
                        'processorName': processor_name,
                        'completionDate': completion_date,
                        'completionDetails': 'All approval steps have been successfully completed.',
                        'actionUrl': f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                    },
                    send_email=True
                )

            logger.info(f" Workflow completion notifications sent for: {workflow_instance.id}")
        except Exception as e:
            logger.error(f" Failed to send workflow completion notification: {str(e)}")

    @staticmethod
    def notify_workflow_cancelled(workflow_instance, cancelled_by, reason=None):
        """
        Send notification when a workflow is cancelled.
        Checks for configured 'workflow_cancelled' notifications.

        Args:
            workflow_instance: WorkflowInstance that was cancelled
            cancelled_by: User who cancelled the workflow
            reason: Optional cancellation reason
        """
        try:
            from .models import WorkflowStepNotificationConfig

            # Check if any step has workflow_cancelled notification configured
            workflow_steps = workflow_instance.workflow_template.steps.all()
            configs = WorkflowStepNotificationConfig.objects.filter(
                workflow_step__in=workflow_steps,
                event_type='workflow_cancelled',
                is_active=True
            )

            if configs.exists():
                logger.info(f" Found {configs.count()} workflow_cancelled notification config(s)")

                # Use current step execution for context
                current_step = workflow_instance.step_executions.filter(status='pending').first()
                if not current_step:
                    current_step = workflow_instance.step_executions.order_by('-workflow_step__step_order').first()

                if current_step:
                    # Trigger configured notifications
                    WorkflowNotifications.trigger_configured_notifications(
                        current_step, 'workflow_cancelled'
                    )
            else:
                # Fall back to default notification
                logger.info(f" No workflow_cancelled configs found, using default notification")
                if workflow_instance.initiated_by != cancelled_by:
                    NotificationService.create_notification(
                        user=workflow_instance.initiated_by,
                        title=f"Request Cancelled: {workflow_instance.workflow_template.name}",
                        message=f"Your {workflow_instance.workflow_template.entity_type} request has been cancelled. {f'Reason: {reason}' if reason else ''}",
                        event_type=_get_event_type('WORKFLOW_CANCELLED'),
                        priority='normal',
                        action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
                        send_email=True
                    )

            logger.info(f" Workflow cancellation notifications sent for: {workflow_instance.id}")
        except Exception as e:
            logger.error(f" Failed to send workflow cancellation notification: {str(e)}")

    @staticmethod
    def trigger_configured_notifications(step_execution, event_type):
        """
        Trigger notifications based on WorkflowStepNotificationConfig.
        Reads configured notifications for the step and event type, then sends them.

        Args:
            step_execution: WorkflowStepExecution instance
            event_type: Event type ('assignment', 'approval', 'rejection', etc.)
        """
        try:
            from .models import WorkflowStepNotificationConfig
            from .services import WorkflowNotificationRecipientResolver

            # Get all active notification configs for this step and event type
            configs = WorkflowStepNotificationConfig.objects.filter(
                workflow_step=step_execution.workflow_step,
                event_type=event_type,
                is_active=True
            ).select_related('notification_template')

            if not configs.exists():
                logger.debug(f" No notification configs found for step '{step_execution.workflow_step.step_name}' event '{event_type}'")
                return

            logger.debug(f" Found {configs.count()} notification config(s) for event '{event_type}'")

            for config in configs:
                try:
                    # Resolve recipients based on recipient_types (JSONField)
                    recipients = WorkflowNotifications._resolve_recipients(
                        config.recipient_types,
                        config.custom_recipients,
                        step_execution
                    )

                    if not recipients:
                        logger.warning(f" No recipients resolved for notification config #{config.id}")
                        continue

                    # Get notification template
                    template = config.notification_template

                    # Prepare context for template
                    context = WorkflowNotifications._build_notification_context(step_execution)

                    # Render template
                    title = WorkflowNotifications._render_template(template.subject, context)
                    message = WorkflowNotifications._render_template(template.body, context)

                    # Send notification to each recipient
                    for recipient in recipients:
                        # Use configuration settings for email and in-app notifications
                        send_email_flag = config.send_email
                        send_system_flag = config.send_system_notification

                        # Send notification if either channel is enabled
                        if send_email_flag or send_system_flag:
                            NotificationService.create_notification(
                                user=recipient,
                                title=title,
                                message=message,
                                event_type=template.event_type,
                                priority=config.priority,
                                action_url=f"/{step_execution.workflow_instance.workflow_template.entity_type}/{step_execution.workflow_instance.object_id}",
                                send_email=send_email_flag,
                                content_object=step_execution.workflow_instance,
                                additional_data=context  # Pass context for email template rendering
                            )
                        else:
                            logger.warning(f" Notification config #{config.id} has both email and in-app disabled - skipping")

                    logger.info(f" Sent notification to {len(recipients)} recipient(s) using template '{template.name}'")

                except Exception as e:
                    logger.error(f" Failed to send notification for config #{config.id}: {str(e)}")

        except Exception as e:
            logger.error(f" Failed to trigger configured notifications: {str(e)}")

    @staticmethod
    def _resolve_recipients(recipient_types, custom_recipients, step_execution):
        """
        Resolve recipients based on recipient_types list and custom_recipients.

        Args:
            recipient_types: List of recipient type strings (e.g., ['current_approver', 'requester'])
            custom_recipients: List of custom email addresses
            step_execution: WorkflowStepExecution instance

        Returns:
            list: List of User objects
        """
        from accounts.models import User
        recipients = set()

        for recipient_type in recipient_types:
            if recipient_type == 'current_approver' or recipient_type == 'step_approver':
                if step_execution.assigned_to:
                    recipients.add(step_execution.assigned_to)

            elif recipient_type == 'requester':
                recipients.add(step_execution.workflow_instance.initiated_by)

            elif recipient_type == 'previous_approvers':
                previous_steps = step_execution.workflow_instance.step_executions.filter(
                    workflow_step__step_order__lt=step_execution.workflow_step.step_order,
                    status='approved'
                )
                for step in previous_steps:
                    if step.assigned_to:
                        recipients.add(step.assigned_to)

            elif recipient_type == 'next_approvers':
                next_step = step_execution.workflow_instance.step_executions.filter(
                    workflow_step__step_order=step_execution.workflow_step.step_order + 1
                ).first()
                if next_step and next_step.assigned_to:
                    recipients.add(next_step.assigned_to)

            elif recipient_type == 'all_stakeholders':
                # Include requester and all approvers
                recipients.add(step_execution.workflow_instance.initiated_by)
                all_steps = step_execution.workflow_instance.step_executions.all()
                for step in all_steps:
                    if step.assigned_to:
                        recipients.add(step.assigned_to)

            elif recipient_type.startswith('role_'):
                # Dynamic role-based recipient (e.g., 'role_123')
                role_id = recipient_type.replace('role_', '')
                try:
                    from accounts.models import Role
                    role = Role.objects.get(id=role_id)
                    users = User.objects.filter(role=role, status='Active')
                    recipients.update(users)
                except Exception as e:
                    logger.warning(f" Failed to resolve role {role_id}: {str(e)}")

        # Handle custom email addresses
        if custom_recipients:
            for email in custom_recipients:
                try:
                    user = User.objects.filter(email=email, status='Active').first()
                    if user:
                        recipients.add(user)
                except Exception as e:
                    logger.warning(f" Failed to resolve custom recipient {email}: {str(e)}")

        return list(recipients)

    @staticmethod
    def _build_notification_context(step_execution):
        """Build context dictionary for template rendering"""
        from django.utils import timezone
        workflow_instance = step_execution.workflow_instance

        # Get processor/approver info
        processor_name = step_execution.actioned_by.get_full_name() if step_execution.actioned_by else 'The approval team'
        approver_name = step_execution.assigned_to.get_full_name() if step_execution.assigned_to else 'Unassigned'

        # Get completion date
        completion_date = timezone.now().strftime('%B %d, %Y at %I:%M %p')

        # Get due date formatted nicely
        due_date = step_execution.sla_due_date.strftime('%B %d, %Y at %I:%M %p') if step_execution.sla_due_date else 'Not specified'

        return {
            # Workflow information
            'workflow_name': workflow_instance.workflow_template.name,
            'workflowName': workflow_instance.workflow_template.name,

            # Entity information (both snake_case and camelCase for compatibility)
            'entity_type': workflow_instance.workflow_template.entity_type,
            'entityType': workflow_instance.workflow_template.entity_type,
            'request_type': workflow_instance.workflow_template.entity_type.title(),
            'requestType': workflow_instance.workflow_template.entity_type.title(),

            'entity_id': str(workflow_instance.object_id),
            'entityId': str(workflow_instance.object_id),

            # Step information
            'step_name': step_execution.workflow_step.step_name,
            'stepName': step_execution.workflow_step.step_name,

            # People - for improved templates
            'requestorName': workflow_instance.initiated_by.get_full_name(),
            'approverName': approver_name,
            'processorName': processor_name,
            'userName': workflow_instance.initiated_by.get_full_name(),  # For comment notifications

            # People - legacy compatibility
            'assigned_to': approver_name,
            'assignedTo': approver_name,
            'requester': workflow_instance.initiated_by.get_full_name(),
            'requesterName': workflow_instance.initiated_by.get_full_name(),

            # Dates
            'dueDate': due_date,
            'completionDate': completion_date,

            # Status
            'status': step_execution.status,
            'urgencyHint': 'High priority' if getattr(step_execution.workflow_step, 'is_urgent', False) else 'Normal priority',
            'processorHint': f"Please review and approve {step_execution.workflow_step.step_name}",
            'completionDetails': 'All approval steps have been successfully completed.',
            'rejectionReason': step_execution.comments or 'No reason provided',

            # Legacy compatibility
            'sla_due_date': step_execution.sla_due_date.strftime('%Y-%m-%d %H:%M') if step_execution.sla_due_date else 'N/A',
            'slaDueDate': step_execution.sla_due_date.strftime('%Y-%m-%d %H:%M') if step_execution.sla_due_date else 'N/A',

            # Action URL
            'actionUrl': f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.object_id}",
        }

    @staticmethod
    def _render_template(template_text, context):
        """
        Simple template rendering - replaces {{variable}} with context values.
        For more complex rendering, could use Django templates or Jinja2.
        """
        import re
        result = template_text
        for key, value in context.items():
            result = re.sub(r'\{\{\s*' + key + r'\s*\}\}', str(value), result)
        return result
