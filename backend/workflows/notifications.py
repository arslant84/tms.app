"""
Notification triggers for workflow events.
Sends notifications when workflow instances change state.
"""

import logging

from django.conf import settings
from notifications.services import NotificationService

logger = logging.getLogger(__name__)
from notifications.models import NotificationEventType, NotificationTemplate

# Maps a workflow's entity_type (after collapsing TRF sub-types, see
# _get_display_request_type) to the actual frontend route segment. These
# don't match 1:1 - the Angular routes are /trf, /transport, /visa,
# /accommodation, not the raw "travelrequest"/"transportrequest"/etc.
# entity_type strings.
_ENTITY_TYPE_ROUTE_SEGMENT = {
    "travelrequest": "trf",
    "transportrequest": "transport",
    "visaapplication": "visa",
    "accommodationrequest": "accommodation",
}


def _get_event_type(event_name):
    """Get NotificationEventType by name, returns None if not found"""
    try:
        return NotificationEventType.objects.get(name=event_name, is_active=True)
    except NotificationEventType.DoesNotExist:
        return None


def _get_display_request_type(entity_type):
    """
    Human-facing "request type" for notification text. TRF's entity_type may
    be a per-travel-type sub-type (travelrequest_domestic, etc. - see
    docs/TSR_SUBMODULE_WORKFLOW_ROADMAP.md) rather than the base
    "travelrequest" string every other module uses as-is; collapse those back
    to "travelrequest" before .title()-ing so notification text doesn't leak
    the raw internal sub-type string (e.g. "Travelrequest_Overseas").
    """
    base_type = entity_type.split("_", 1)[0] if entity_type else entity_type
    return base_type.title()


def _get_action_url(entity_type, object_id):
    """
    Absolute URL to the request's detail page, for the email's "View" button
    and its "Review & Approve" link.

    This used to be f"/{entity_type}/{object_id}" - the raw entity_type
    ("transportrequest", "travelrequest_overseas", etc.) instead of the
    actual Angular route segment ("transport", "trf"), so the link 404'd
    into the wildcard route and landed on the dashboard. It was also never
    made absolute for the additional_data["actionUrl"] variant (used by the
    template's own "[Review & Approve](...)" markdown link, as opposed to
    the button's action_url which does go through EmailTemplateRenderer's
    own absolute-URL conversion) - a bare relative path has no meaning
    clicked from an email client.
    """
    base_type = entity_type.split("_", 1)[0] if entity_type else entity_type
    route_segment = _ENTITY_TYPE_ROUTE_SEGMENT.get(base_type, base_type)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:4200").rstrip(
        "/"
    )
    return f"{frontend_url}/{route_segment}/{object_id}"


class WorkflowNotifications:
    """
    Helper class for sending workflow-related notifications.
    """

    @staticmethod
    def _get_entity_id(workflow_instance):
        """
        Get the formatted request number from the entity (e.g., "VISA-2024-0013").
        Falls back to object_id if request_number is not available.
        """
        entity = workflow_instance.content_object
        request_number = getattr(entity, "request_number", None) if entity else None
        return request_number or str(workflow_instance.object_id)

    @staticmethod
    def notify_workflow_started(workflow_instance):
        """
        Send notification when a new workflow is started.

        Args:
            workflow_instance: WorkflowInstance that was started
        """
        try:
            # Get formatted entity ID (e.g., "VISA-2024-0013")
            entity_id = WorkflowNotifications._get_entity_id(workflow_instance)

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
                event_type=_get_event_type("WORKFLOW_STARTED"),
                priority="normal",
                action_url=_get_action_url(
                    workflow_instance.workflow_template.entity_type,
                    workflow_instance.object_id,
                ),
                additional_data={
                    "requestorName": workflow_instance.initiated_by.get_full_name(),
                    "requestType": _get_display_request_type(
                        workflow_instance.workflow_template.entity_type
                    ),
                    "entityId": entity_id,
                    "approverName": first_approver_name,
                    "actionUrl": _get_action_url(
                        workflow_instance.workflow_template.entity_type,
                        workflow_instance.object_id,
                    ),
                },
                send_email=True,
            )

            # Note: the first approver is notified separately, by the config-driven
            # 'assignment' event fired from WorkflowEngine._start_step() when their
            # step execution is created - not duplicated here.

            logger.info(
                f" Notifications sent for workflow start: {workflow_instance.id}"
            )
        except Exception as e:
            logger.error(f" Failed to send workflow start notifications: {str(e)}")

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
                event_type="workflow_completed",
                is_active=True,
            )

            if configs.exists():
                logger.info(
                    f" Found {configs.count()} workflow_completed notification config(s)"
                )

                # Use last step execution for context
                last_step_execution = workflow_instance.step_executions.order_by(
                    "-workflow_step__step_order"
                ).first()

                if last_step_execution:
                    # Trigger configured notifications
                    WorkflowNotifications.trigger_configured_notifications(
                        last_step_execution, "workflow_completed"
                    )
                else:
                    logger.warning(
                        f" No step executions found for workflow {workflow_instance.id}"
                    )
            else:
                logger.info(
                    " No workflow_completed configs found, using default notification"
                )

                # Get last step execution for context
                last_step_execution = workflow_instance.step_executions.order_by(
                    "-workflow_step__step_order"
                ).first()

                # Skip default if the last step already had configured 'approval' notifications —
                # those notifications already told the requester their request was approved,
                # so sending this default too would be a duplicate.
                has_configured_approval_notification = (
                    last_step_execution is not None
                    and WorkflowStepNotificationConfig.objects.filter(
                        workflow_step=last_step_execution.workflow_step,
                        event_type="approval",
                        is_active=True,
                    ).exists()
                )

                if has_configured_approval_notification:
                    logger.info(
                        f" Skipping default workflow_completed notification — configured approval notification already sent for step '{last_step_execution.workflow_step.step_name}'"
                    )
                else:
                    processor_name = (
                        last_step_execution.actioned_by.get_full_name()
                        if last_step_execution and last_step_execution.actioned_by
                        else "The approval team"
                    )
                    entity_id = WorkflowNotifications._get_entity_id(workflow_instance)

                    from django.utils import timezone

                    completion_date = timezone.now().strftime("%B %d, %Y at %I:%M %p")

                    NotificationService.create_notification(
                        user=workflow_instance.initiated_by,
                        title=f"Request Approved: {workflow_instance.workflow_template.name}",
                        message=f"Your {workflow_instance.workflow_template.entity_type} request has been fully approved! All approval steps are complete.",
                        event_type=_get_event_type("WORKFLOW_APPROVED"),
                        priority="high",
                        action_url=_get_action_url(
                            workflow_instance.workflow_template.entity_type,
                            workflow_instance.object_id,
                        ),
                        additional_data={
                            "requestorName": workflow_instance.initiated_by.get_full_name(),
                            "requestType": _get_display_request_type(
                                workflow_instance.workflow_template.entity_type
                            ),
                            "entityId": entity_id,
                            "processorName": processor_name,
                            "completionDate": completion_date,
                            "completionDetails": "All approval steps have been successfully completed.",
                            "actionUrl": _get_action_url(
                                workflow_instance.workflow_template.entity_type,
                                workflow_instance.object_id,
                            ),
                        },
                        send_email=True,
                    )

            logger.info(
                f" Workflow completion notifications sent for: {workflow_instance.id}"
            )
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
                event_type="workflow_cancelled",
                is_active=True,
            )

            if configs.exists():
                logger.info(
                    f" Found {configs.count()} workflow_cancelled notification config(s)"
                )

                # Use current step execution for context
                current_step = workflow_instance.step_executions.filter(
                    status="pending"
                ).first()
                if not current_step:
                    current_step = workflow_instance.step_executions.order_by(
                        "-workflow_step__step_order"
                    ).first()

                if current_step:
                    # Trigger configured notifications
                    WorkflowNotifications.trigger_configured_notifications(
                        current_step, "workflow_cancelled"
                    )
            else:
                # Fall back to default notification
                logger.info(
                    " No workflow_cancelled configs found, using default notification"
                )
                if workflow_instance.initiated_by != cancelled_by:
                    NotificationService.create_notification(
                        user=workflow_instance.initiated_by,
                        title=f"Request Cancelled: {workflow_instance.workflow_template.name}",
                        message=f"Your {workflow_instance.workflow_template.entity_type} request has been cancelled. {f'Reason: {reason}' if reason else ''}",
                        event_type=_get_event_type("WORKFLOW_CANCELLED"),
                        priority="normal",
                        action_url=_get_action_url(
                            workflow_instance.workflow_template.entity_type,
                            workflow_instance.object_id,
                        ),
                        send_email=True,
                    )

            logger.info(
                f" Workflow cancellation notifications sent for: {workflow_instance.id}"
            )
        except Exception as e:
            logger.error(
                f" Failed to send workflow cancellation notification: {str(e)}"
            )

    @staticmethod
    def trigger_configured_notifications(step_execution, event_type):
        """
        Trigger notifications based on WorkflowStepNotificationConfig.
        If no configuration exists for the event type, falls back to default behavior.

        Args:
            step_execution: WorkflowStepExecution instance
            event_type: Event type ('assignment', 'approval', 'rejection', etc.)
        """
        try:
            from .models import WorkflowStepNotificationConfig

            # Get all active notification configs for this step and event type
            configs = WorkflowStepNotificationConfig.objects.filter(
                workflow_step=step_execution.workflow_step,
                event_type=event_type,
                is_active=True,
            ).select_related("notification_template")

            if not configs.exists():
                # No custom config - use default notification behavior
                logger.debug(
                    f" No notification configs found for step '{step_execution.workflow_step.step_name}' event '{event_type}', using defaults"
                )
                WorkflowNotifications._send_default_notification(
                    step_execution, event_type
                )
                return

            logger.debug(
                f" Found {configs.count()} notification config(s) for event '{event_type}'"
            )

            for config in configs:
                try:
                    # Resolve recipients based on recipient_types (JSONField)
                    recipients = WorkflowNotifications._resolve_recipients(
                        config.recipient_types, config.custom_recipients, step_execution
                    )

                    if not recipients:
                        logger.warning(
                            f" No recipients resolved for notification config #{config.id}"
                        )
                        continue

                    # Get notification template
                    template = config.notification_template

                    # Prepare context for template
                    context = WorkflowNotifications._build_notification_context(
                        step_execution
                    )

                    # Render template
                    title = WorkflowNotifications._render_template(
                        template.subject, context
                    )
                    message = WorkflowNotifications._render_template(
                        template.body, context
                    )

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
                                action_url=_get_action_url(
                                    step_execution.workflow_instance.workflow_template.entity_type,
                                    step_execution.workflow_instance.object_id,
                                ),
                                send_email=send_email_flag,
                                content_object=step_execution.workflow_instance,
                                additional_data=context,  # Pass context for email template rendering
                            )
                        else:
                            logger.warning(
                                f" Notification config #{config.id} has both email and in-app disabled - skipping"
                            )

                    logger.info(
                        f" Sent notification to {len(recipients)} recipient(s) using template '{template.name}'"
                    )

                except Exception as e:
                    logger.error(
                        f" Failed to send notification for config #{config.id}: {str(e)}"
                    )

        except Exception as e:
            logger.error(f" Failed to trigger configured notifications: {str(e)}")

    @staticmethod
    def _send_default_notification(step_execution, event_type):
        """
        Send default notifications when no WorkflowStepNotificationConfig exists.
        This provides backwards-compatible behavior for workflows without custom configs.

        Default behavior by event type:
        - assignment: Notify the assigned approver
        - approval: Notify the requester that step was approved
        - rejection: Notify the requester that request was rejected
        - delegation: Notify the new assignee
        - workflow_completed: Notify the requester
        - workflow_cancelled: Notify the requester
        """
        try:
            workflow_instance = step_execution.workflow_instance
            entity_id = WorkflowNotifications._get_entity_id(workflow_instance)

            if event_type == "assignment":
                # Notify the assigned approver
                if step_execution.assigned_to:
                    NotificationService.create_notification(
                        user=step_execution.assigned_to,
                        title=f"New Approval Required: {step_execution.workflow_step.step_name}",
                        message=f"You have been assigned to approve {step_execution.workflow_step.step_name} for a {workflow_instance.workflow_template.entity_type} request from {workflow_instance.initiated_by.get_full_name()}.",
                        event_type=_get_event_type("APPROVAL_REQUESTED"),
                        priority="high",
                        action_url=_get_action_url(
                            workflow_instance.workflow_template.entity_type,
                            workflow_instance.object_id,
                        ),
                        additional_data={
                            "approverName": step_execution.assigned_to.get_full_name(),
                            "requestType": _get_display_request_type(
                                workflow_instance.workflow_template.entity_type
                            ),
                            "entityId": entity_id,
                            "requestorName": workflow_instance.initiated_by.get_full_name(),
                            "actionUrl": _get_action_url(
                                workflow_instance.workflow_template.entity_type,
                                workflow_instance.object_id,
                            ),
                        },
                        send_email=True,
                    )

            elif event_type == "approval":
                # Notify the requester that step was approved
                approver_name = (
                    step_execution.actioned_by.get_full_name()
                    if step_execution.actioned_by
                    else "Unknown"
                )
                NotificationService.create_notification(
                    user=workflow_instance.initiated_by,
                    title=f"Step Approved: {step_execution.workflow_step.step_name}",
                    message=f"{step_execution.workflow_step.step_name} has been approved by {approver_name}. Your request is progressing.",
                    event_type=_get_event_type("WORKFLOW_UPDATED"),
                    priority="normal",
                    action_url=_get_action_url(
                        workflow_instance.workflow_template.entity_type,
                        workflow_instance.object_id,
                    ),
                    additional_data={
                        "requestorName": workflow_instance.initiated_by.get_full_name(),
                        "requestType": _get_display_request_type(
                            workflow_instance.workflow_template.entity_type
                        ),
                        "entityId": entity_id,
                        "approverName": approver_name,
                        "stepName": step_execution.workflow_step.step_name,
                        "actionUrl": _get_action_url(
                            workflow_instance.workflow_template.entity_type,
                            workflow_instance.object_id,
                        ),
                    },
                    send_email=True,
                )

                # Also notify the next approver if exists
                next_step = workflow_instance.step_executions.filter(
                    workflow_step__step_order=step_execution.workflow_step.step_order
                    + 1,
                    status="pending",
                ).first()
                if next_step and next_step.assigned_to:
                    NotificationService.create_notification(
                        user=next_step.assigned_to,
                        title=f"New Approval Required: {next_step.workflow_step.step_name}",
                        message=f"You have been assigned to approve {next_step.workflow_step.step_name} for a {workflow_instance.workflow_template.entity_type} request.",
                        event_type=_get_event_type("APPROVAL_REQUESTED"),
                        priority="high",
                        action_url=_get_action_url(
                            workflow_instance.workflow_template.entity_type,
                            workflow_instance.object_id,
                        ),
                        additional_data={
                            "approverName": next_step.assigned_to.get_full_name(),
                            "requestType": _get_display_request_type(
                                workflow_instance.workflow_template.entity_type
                            ),
                            "entityId": entity_id,
                            "requestorName": workflow_instance.initiated_by.get_full_name(),
                            "actionUrl": _get_action_url(
                                workflow_instance.workflow_template.entity_type,
                                workflow_instance.object_id,
                            ),
                        },
                        send_email=True,
                    )

            elif event_type == "rejection":
                # Notify the requester that request was rejected
                approver_name = (
                    step_execution.actioned_by.get_full_name()
                    if step_execution.actioned_by
                    else "Unknown"
                )
                NotificationService.create_notification(
                    user=workflow_instance.initiated_by,
                    title=f"Request Rejected: {workflow_instance.workflow_template.name}",
                    message=f"Your {workflow_instance.workflow_template.entity_type} request has been rejected at {step_execution.workflow_step.step_name}. Reason: {step_execution.comments or 'No reason provided'}",
                    event_type=_get_event_type("WORKFLOW_REJECTED"),
                    priority="urgent",
                    action_url=_get_action_url(
                        workflow_instance.workflow_template.entity_type,
                        workflow_instance.object_id,
                    ),
                    additional_data={
                        "requestorName": workflow_instance.initiated_by.get_full_name(),
                        "requestType": _get_display_request_type(
                            workflow_instance.workflow_template.entity_type
                        ),
                        "entityId": entity_id,
                        "approverName": approver_name,
                        "rejectionReason": step_execution.comments
                        or "No reason provided",
                        "actionUrl": _get_action_url(
                            workflow_instance.workflow_template.entity_type,
                            workflow_instance.object_id,
                        ),
                    },
                    send_email=True,
                )

            elif event_type == "delegation":
                # Notify the new assignee (if assigned_to was just updated)
                if step_execution.assigned_to:
                    NotificationService.create_notification(
                        user=step_execution.assigned_to,
                        title=f"Approval Delegated to You: {step_execution.workflow_step.step_name}",
                        message=f"An approval for {workflow_instance.workflow_template.entity_type} has been delegated to you. Please review and take action.",
                        event_type=_get_event_type("APPROVAL_DELEGATED"),
                        priority="high",
                        action_url=_get_action_url(
                            workflow_instance.workflow_template.entity_type,
                            workflow_instance.object_id,
                        ),
                        additional_data={
                            "approverName": step_execution.assigned_to.get_full_name(),
                            "requestType": _get_display_request_type(
                                workflow_instance.workflow_template.entity_type
                            ),
                            "entityId": entity_id,
                            "actionUrl": _get_action_url(
                                workflow_instance.workflow_template.entity_type,
                                workflow_instance.object_id,
                            ),
                        },
                        send_email=True,
                    )

            logger.info(
                f" Sent default notification for event '{event_type}' on step '{step_execution.workflow_step.step_name}'"
            )

        except Exception as e:
            logger.error(
                f" Failed to send default notification for event '{event_type}': {str(e)}"
            )

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
            if (
                recipient_type == "current_approver"
                or recipient_type == "step_approver"
            ):
                if step_execution.assigned_to:
                    recipients.add(step_execution.assigned_to)

            elif recipient_type == "requester":
                recipients.add(step_execution.workflow_instance.initiated_by)

            elif recipient_type == "previous_approvers":
                previous_steps = step_execution.workflow_instance.step_executions.filter(
                    workflow_step__step_order__lt=step_execution.workflow_step.step_order,
                    status="approved",
                )
                for step in previous_steps:
                    if step.assigned_to:
                        recipients.add(step.assigned_to)

            elif recipient_type == "next_approvers":
                next_step = step_execution.workflow_instance.step_executions.filter(
                    workflow_step__step_order=step_execution.workflow_step.step_order
                    + 1
                ).first()
                if next_step and next_step.assigned_to:
                    recipients.add(next_step.assigned_to)

            elif recipient_type == "all_stakeholders":
                # Include requester and all approvers
                recipients.add(step_execution.workflow_instance.initiated_by)
                all_steps = step_execution.workflow_instance.step_executions.all()
                for step in all_steps:
                    if step.assigned_to:
                        recipients.add(step.assigned_to)

            elif recipient_type.startswith("role_"):
                # Dynamic role-based recipient (e.g., 'role_123')
                role_id = recipient_type.replace("role_", "")
                try:
                    from accounts.models import Role

                    role = Role.objects.get(id=role_id)
                    users = User.objects.filter(role=role, status="Active")
                    recipients.update(users)
                except Exception as e:
                    logger.warning(f" Failed to resolve role {role_id}: {str(e)}")

        # Handle custom email addresses
        if custom_recipients:
            for email in custom_recipients:
                try:
                    user = User.objects.filter(email=email, status="Active").first()
                    if user:
                        recipients.add(user)
                except Exception as e:
                    logger.warning(
                        f" Failed to resolve custom recipient {email}: {str(e)}"
                    )

        return list(recipients)

    @staticmethod
    def _build_notification_context(step_execution):
        """Build context dictionary for template rendering"""
        from django.utils import timezone

        workflow_instance = step_execution.workflow_instance

        # Get processor/approver info
        processor_name = (
            step_execution.actioned_by.get_full_name()
            if step_execution.actioned_by
            else "The approval team"
        )
        approver_name = (
            step_execution.assigned_to.get_full_name()
            if step_execution.assigned_to
            else "Unassigned"
        )

        # Get completion date
        completion_date = timezone.now().strftime("%B %d, %Y at %I:%M %p")

        # Get formatted request number from the actual entity (e.g., "VISA-2024-0013")
        # Falls back to object_id if request_number is not available
        entity = workflow_instance.content_object
        request_number = getattr(entity, "request_number", None) if entity else None
        entity_id = request_number or str(workflow_instance.object_id)

        return {
            # Workflow information
            "workflow_name": workflow_instance.workflow_template.name,
            "workflowName": workflow_instance.workflow_template.name,
            # Entity information (both snake_case and camelCase for compatibility)
            "entity_type": workflow_instance.workflow_template.entity_type,
            "entityType": workflow_instance.workflow_template.entity_type,
            "request_type": _get_display_request_type(
                workflow_instance.workflow_template.entity_type
            ),
            "requestType": _get_display_request_type(
                workflow_instance.workflow_template.entity_type
            ),
            "entity_id": entity_id,
            "entityId": entity_id,
            # Step information
            "step_name": step_execution.workflow_step.step_name,
            "stepName": step_execution.workflow_step.step_name,
            # People - for improved templates
            "requestorName": workflow_instance.initiated_by.get_full_name(),
            "approverName": approver_name,
            "processorName": processor_name,
            "userName": workflow_instance.initiated_by.get_full_name(),  # For comment notifications
            # People - legacy compatibility
            "assigned_to": approver_name,
            "assignedTo": approver_name,
            "requester": workflow_instance.initiated_by.get_full_name(),
            "requesterName": workflow_instance.initiated_by.get_full_name(),
            # Dates
            "completionDate": completion_date,
            # Status
            "status": step_execution.status,
            "urgencyHint": (
                "High priority"
                if getattr(step_execution.workflow_step, "is_urgent", False)
                else "Normal priority"
            ),
            "processorHint": f"Please review and approve {step_execution.workflow_step.step_name}",
            "completionDetails": "All approval steps have been successfully completed.",
            "rejectionReason": step_execution.comments or "No reason provided",
            # Action URL
            "actionUrl": _get_action_url(
                workflow_instance.workflow_template.entity_type,
                workflow_instance.object_id,
            ),
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
            result = re.sub(r"\{\{\s*" + key + r"\s*\}\}", str(value), result)
        return result
