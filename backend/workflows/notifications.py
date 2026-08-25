"""
Notification triggers for workflow events.
Sends notifications when workflow instances change state.

Shared dispatch machinery (WorkflowStepNotificationConfig resolution,
template rendering, default-notification fallback) lives in
workflows/notification_dispatch.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 2) - this module keeps the
notify_* triggers that call into it.
"""

import logging

from notifications.services import NotificationService

from .notification_dispatch import (
    _get_action_url,
    _get_display_request_type,
    _get_entity_id,
    _get_event_type,
    trigger_configured_notifications,
)

logger = logging.getLogger(__name__)


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
        return _get_entity_id(workflow_instance)

    @staticmethod
    def trigger_configured_notifications(
        step_execution, event_type, context_overrides=None
    ):
        """
        Trigger notifications based on WorkflowStepNotificationConfig. See
        workflows/notification_dispatch.py for the implementation - kept as
        a staticmethod here so existing callers (workflows/engine.py) don't
        need to change.
        """
        return trigger_configured_notifications(
            step_execution, event_type, context_overrides
        )

    @staticmethod
    def notify_workflow_started(workflow_instance):
        """
        Send notification when a new workflow is started.
        Checks for configured 'workflow_started' notifications, same pattern
        as notify_workflow_completed/notify_workflow_cancelled.

        Args:
            workflow_instance: WorkflowInstance that was started
        """
        try:
            from .models import WorkflowStepNotificationConfig

            first_step_execution = workflow_instance.step_executions.filter(
                workflow_step__step_order=1
            ).first()

            workflow_steps = workflow_instance.workflow_template.steps.all()
            configs = WorkflowStepNotificationConfig.objects.filter(
                workflow_step__in=workflow_steps,
                event_type="workflow_started",
                is_active=True,
            )

            if configs.exists() and first_step_execution:
                logger.info(
                    f" Found {configs.count()} workflow_started notification config(s)"
                )
                # recipient_types on this event's configs is expected to be
                # ['requester'] (see populate_default_notification_configs /
                # DEFAULT_NOTIFICATION_CONFIGS) - the first approver is
                # notified separately, by the config-driven 'assignment'
                # event fired from WorkflowEngine._start_step() when their
                # step execution is created, not duplicated here.
                trigger_configured_notifications(
                    first_step_execution, "workflow_started"
                )
            else:
                logger.info(
                    " No workflow_started configs found, using default notification"
                )
                entity_id = _get_entity_id(workflow_instance)

                first_approver_name = "the approval team"
                if first_step_execution and first_step_execution.assigned_to:
                    first_approver_name = (
                        first_step_execution.assigned_to.get_full_name()
                    )

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
                    trigger_configured_notifications(
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
                    entity_id = _get_entity_id(workflow_instance)

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
    def notify_processing_completed(workflow_instance, completed_by=None):
        """
        Send notification when a request has been processed and marked
        completed by an admin, after the approval workflow already finished
        (e.g. Transport Admin assigning a vehicle, Visa Clerk finishing visa
        processing). Distinct from notify_workflow_completed, which fires
        when the *approval chain itself* finishes - this fires for that
        separate, later admin action, which previously had no notification
        at all in Transport/Visa's complete() actions.

        Checks for configured 'processing_completed' notifications; falls
        back to a default notification to the requester if none exist.
        """
        try:
            from .models import WorkflowStepNotificationConfig

            workflow_steps = workflow_instance.workflow_template.steps.all()
            configs = WorkflowStepNotificationConfig.objects.filter(
                workflow_step__in=workflow_steps,
                event_type="processing_completed",
                is_active=True,
            )

            last_step_execution = workflow_instance.step_executions.order_by(
                "-workflow_step__step_order"
            ).first()

            if not last_step_execution:
                logger.warning(
                    f" No step executions found for workflow {workflow_instance.id}"
                )
                return

            processor_name = (
                completed_by.get_full_name() if completed_by else "The processing team"
            )
            completion_details = "Your request has been fully processed and completed."

            if configs.exists():
                logger.info(
                    f" Found {configs.count()} processing_completed notification config(s)"
                )
                trigger_configured_notifications(
                    last_step_execution,
                    "processing_completed",
                    context_overrides={
                        "processorName": processor_name,
                        "completionDetails": completion_details,
                    },
                )
            else:
                logger.info(
                    " No processing_completed configs found, using default notification"
                )
                entity_id = _get_entity_id(workflow_instance)

                from django.utils import timezone

                completion_date = timezone.now().strftime("%B %d, %Y at %I:%M %p")

                NotificationService.create_notification(
                    user=workflow_instance.initiated_by,
                    title=f"Request Completed: {workflow_instance.workflow_template.name}",
                    message=f"Your {workflow_instance.workflow_template.entity_type} request has been fully processed and marked completed.",
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
                        "processorName": processor_name,
                        "completionDate": completion_date,
                        "completionDetails": completion_details,
                        "actionUrl": _get_action_url(
                            workflow_instance.workflow_template.entity_type,
                            workflow_instance.object_id,
                        ),
                    },
                    send_email=True,
                )

            logger.info(
                f" Processing completion notifications sent for: {workflow_instance.id}"
            )
        except Exception as e:
            logger.error(
                f" Failed to send processing completion notification: {str(e)}"
            )

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
                    trigger_configured_notifications(current_step, "workflow_cancelled")
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
