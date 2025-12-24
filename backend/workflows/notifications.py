"""
Notification triggers for workflow events.
Sends notifications when workflow instances change state.
"""

from notifications.services import NotificationService
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
                        action_url=f"/{workflow_instance.workflow_template.entity_type}/{workflow_instance.entity_id}",
                        send_email=True
                    )
                else:
                    print(f"⚠️ First step has no assigned user - notifications may not be sent")

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
                print(f"ℹ️ No notification configs found for step '{step_execution.workflow_step.step_name}' event '{event_type}'")
                return

            print(f"📧 Found {configs.count()} notification config(s) for event '{event_type}'")

            for config in configs:
                try:
                    # Resolve recipients based on recipient_types (JSONField)
                    recipients = WorkflowNotifications._resolve_recipients(
                        config.recipient_types,
                        config.custom_recipients,
                        step_execution
                    )

                    if not recipients:
                        print(f"⚠️ No recipients resolved for notification config #{config.id}")
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
                        # Email notifications are controlled by send_email parameter (user's config)
                        send_email = True  # Email will be sent if user wants it
                        send_system = config.send_system_notification  # In-app notification

                        if send_system:
                            NotificationService.create_notification(
                                user=recipient,
                                title=title,
                                message=message,
                                event_type=template.event_type,
                                priority='normal',
                                action_url=f"/{step_execution.workflow_instance.workflow_template.entity_type}/{step_execution.workflow_instance.entity_id}",
                                send_email=send_email,
                                content_object=step_execution.workflow_instance
                            )

                    print(f"✅ Sent notification to {len(recipients)} recipient(s) using template '{template.name}'")

                except Exception as e:
                    print(f"❌ Failed to send notification for config #{config.id}: {str(e)}")

        except Exception as e:
            print(f"❌ Failed to trigger configured notifications: {str(e)}")

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
                    print(f"⚠️ Failed to resolve role {role_id}: {str(e)}")

        # Handle custom email addresses
        if custom_recipients:
            for email in custom_recipients:
                try:
                    user = User.objects.filter(email=email, status='Active').first()
                    if user:
                        recipients.add(user)
                except Exception as e:
                    print(f"⚠️ Failed to resolve custom recipient {email}: {str(e)}")

        return list(recipients)

    @staticmethod
    def _build_notification_context(step_execution):
        """Build context dictionary for template rendering"""
        workflow_instance = step_execution.workflow_instance
        return {
            'workflow_name': workflow_instance.workflow_template.name,
            'entity_type': workflow_instance.workflow_template.entity_type,
            'entity_id': workflow_instance.entity_id,
            'step_name': step_execution.workflow_step.step_name,
            'assigned_to': step_execution.assigned_to.get_full_name() if step_execution.assigned_to else 'Unassigned',
            'requester': workflow_instance.initiated_by.get_full_name(),
            'status': step_execution.status,
            'sla_due_date': step_execution.sla_due_date.strftime('%Y-%m-%d %H:%M') if step_execution.sla_due_date else 'N/A',
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
