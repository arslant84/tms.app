"""
Regression tests for the send_step_reminders management command (Fix 19 of
docs/APP_WIDE_GAPS_FIX_ROADMAP.md): the 'reminder' notification event type
existed in the schema and admin UI but nothing ever fired it - there was no
periodic check anywhere in the codebase.
"""

from datetime import timedelta

import pytest
from django.core import management
from django.utils import timezone
from notifications.models import NotificationTemplate, UserNotification
from trf.models import TravelRequest
from workflows.models import (
    WorkflowStep,
    WorkflowStepNotificationConfig,
    WorkflowTemplate,
)
from workflows.router import WorkflowRouter


@pytest.fixture
def single_step_trf_workflow(db, admin_user):
    """A minimal, active one-step workflow template for TravelRequest with an SLA."""
    template = WorkflowTemplate.objects.create(
        name="Test TRF Reminder Workflow",
        entity_type="travelrequest",
        is_active=True,
        created_by=admin_user,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=1,
        step_name="Manager Approval",
        is_required=True,
        can_skip=True,
        sla_hours=48,
        approver_user=admin_user,
    )
    return template


@pytest.fixture
def pending_step_execution(single_step_trf_workflow, regular_user):
    trf = TravelRequest.objects.create(
        requestor_name=regular_user.name,
        travel_type="Domestic",
        status="Pending",
        created_by=regular_user,
    )
    workflow_instance = WorkflowRouter.start_workflow_for_request(
        entity=trf,
        entity_type="travelrequest",
        initiated_by=regular_user,
    )
    step_execution = workflow_instance.step_executions.filter(status="pending").first()
    assert step_execution is not None
    return step_execution


@pytest.mark.django_db
class TestSendStepReminders:
    def test_reminder_sent_for_step_due_within_24h(self, pending_step_execution):
        pending_step_execution.sla_due_date = timezone.now() + timedelta(hours=5)
        pending_step_execution.save(update_fields=["sla_due_date"])

        management.call_command("send_step_reminders")

        pending_step_execution.refresh_from_db()
        assert pending_step_execution.reminder_sent_at is not None
        assert UserNotification.objects.filter(
            user=pending_step_execution.assigned_to,
            title__icontains="Reminder",
        ).exists()

    def test_reminder_sent_for_already_overdue_step(self, pending_step_execution):
        pending_step_execution.sla_due_date = timezone.now() - timedelta(hours=2)
        pending_step_execution.save(update_fields=["sla_due_date"])

        management.call_command("send_step_reminders")

        pending_step_execution.refresh_from_db()
        assert pending_step_execution.reminder_sent_at is not None

    def test_reminder_skipped_if_not_due_soon(self, pending_step_execution):
        pending_step_execution.sla_due_date = timezone.now() + timedelta(hours=48)
        pending_step_execution.save(update_fields=["sla_due_date"])

        management.call_command("send_step_reminders")

        pending_step_execution.refresh_from_db()
        assert pending_step_execution.reminder_sent_at is None

    def test_reminder_skipped_if_already_sent(self, pending_step_execution):
        already_sent = timezone.now() - timedelta(hours=1)
        pending_step_execution.sla_due_date = timezone.now() + timedelta(hours=1)
        pending_step_execution.reminder_sent_at = already_sent
        pending_step_execution.save(update_fields=["sla_due_date", "reminder_sent_at"])

        management.call_command("send_step_reminders")

        pending_step_execution.refresh_from_db()
        assert pending_step_execution.reminder_sent_at == already_sent

    def test_dry_run_makes_no_changes(self, pending_step_execution):
        pending_step_execution.sla_due_date = timezone.now() + timedelta(hours=5)
        pending_step_execution.save(update_fields=["sla_due_date"])

        management.call_command("send_step_reminders", "--dry-run")

        pending_step_execution.refresh_from_db()
        assert pending_step_execution.reminder_sent_at is None
        assert not UserNotification.objects.filter(
            user=pending_step_execution.assigned_to,
            title__icontains="Reminder",
        ).exists()

    def test_uses_configured_template_when_config_exists(self, pending_step_execution):
        """If a WorkflowStepNotificationConfig exists for 'reminder', the
        configured template is used instead of the hardcoded default."""
        template = NotificationTemplate.objects.filter(name="approval_reminder").first()
        assert template is not None

        WorkflowStepNotificationConfig.objects.create(
            workflow_step=pending_step_execution.workflow_step,
            event_type="reminder",
            notification_template=template,
            recipient_types=["current_approver"],
            is_active=True,
            send_email=True,
            send_system_notification=True,
            priority="high",
        )

        pending_step_execution.sla_due_date = timezone.now() + timedelta(hours=5)
        pending_step_execution.save(update_fields=["sla_due_date"])

        management.call_command("send_step_reminders")

        pending_step_execution.refresh_from_db()
        assert pending_step_execution.reminder_sent_at is not None
        notification = UserNotification.objects.filter(
            user=pending_step_execution.assigned_to
        ).latest("created_at")
        assert (
            notification.title
            == "Reminder: Action Required for Travelrequest Request #{}".format(
                pending_step_execution.workflow_instance.object_id
            )
        )
        assert "{{" not in notification.message  # no unresolved template placeholders
