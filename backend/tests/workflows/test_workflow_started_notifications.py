"""
Regression coverage for two "Workflow Started" notification fixes:

1. notify_workflow_started() (workflows/notifications.py) is now config-driven,
   matching notify_workflow_completed/notify_workflow_cancelled - it checks for
   a WorkflowStepNotificationConfig(event_type='workflow_started') on the
   workflow's first step before falling back to the old hardcoded text. See
   workflows/migrations/0023_add_workflow_started_event_type.py and
   0024_seed_workflow_started_notifications.py, plus
   notifications/migrations/0010_add_workflow_started_template.py.

2. WorkflowEngine.start_workflow() locks the entity row and returns the
   existing active WorkflowInstance instead of creating a second one when
   called twice for the same entity (double-click submit, retry) - so
   "Workflow Started" notifications can no longer be sent twice for one
   submission. This used to duplicate: notify_workflow_started() also used to
   send a second, redundant notification to the first approver on top of the
   real 'assignment' notification _start_step() already sends them - both
   bugs are fixed in the current code, this file locks that in.
"""

import pytest
from notifications.models import NotificationTemplate, UserNotification
from trf.models import TravelRequest
from workflows.engine import WorkflowEngine
from workflows.models import (
    WorkflowStep,
    WorkflowStepNotificationConfig,
    WorkflowTemplate,
)
from workflows.router import WorkflowRouter


@pytest.fixture
def single_step_trf_workflow(db, admin_user):
    """A minimal, active one-step workflow template for TravelRequest."""
    template = WorkflowTemplate.objects.create(
        name="Test TRF Single-Step Workflow",
        entity_type="travelrequest",
        is_active=True,
        created_by=admin_user,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=1,
        step_name="Manager Approval",
        is_required=True,
        can_skip=False,
    )
    return template


@pytest.fixture
def workflow_started_template(db):
    return NotificationTemplate.objects.create(
        name="test_workflow_started",
        subject="Custom Started Subject #{{entityId}}",
        body="Custom started body for {{requestorName}}, action: {{actionUrl}}",
        notification_type="both",
        recipient_type="requestor",
        variables_available=["requestorName", "entityId", "actionUrl"],
        is_active=True,
    )


def _new_trf(regular_user):
    return TravelRequest.objects.create(
        requestor_name=regular_user.name,
        travel_type="Domestic",
        status="Pending",
        created_by=regular_user,
    )


@pytest.mark.django_db
class TestWorkflowStartedConfigDriven:
    def test_uses_configured_template_when_config_exists(
        self, single_step_trf_workflow, regular_user, workflow_started_template
    ):
        first_step = single_step_trf_workflow.steps.get(step_order=1)
        WorkflowStepNotificationConfig.objects.create(
            workflow_step=first_step,
            event_type="workflow_started",
            notification_template=workflow_started_template,
            recipient_types=["requester"],
            is_active=True,
            send_email=True,
            send_system_notification=True,
            priority="normal",
        )

        trf = _new_trf(regular_user)
        before_ids = set(
            UserNotification.objects.filter(user=regular_user).values_list(
                "id", flat=True
            )
        )

        instance = WorkflowRouter.start_workflow_for_request(
            entity=trf, entity_type="travelrequest", initiated_by=regular_user
        )
        assert instance is not None

        new_notifications = UserNotification.objects.filter(user=regular_user).exclude(
            id__in=before_ids
        )
        assert new_notifications.count() == 1
        notification = new_notifications.first()
        assert notification.title == f"Custom Started Subject #{trf.id}"
        assert "Custom started body" in notification.message
        assert regular_user.get_full_name() in notification.message

    def test_falls_back_to_default_when_no_config(
        self, single_step_trf_workflow, regular_user
    ):
        # No WorkflowStepNotificationConfig for 'workflow_started' on this
        # template - the fallback branch (hardcoded text) must still fire.
        trf = _new_trf(regular_user)
        before_ids = set(
            UserNotification.objects.filter(user=regular_user).values_list(
                "id", flat=True
            )
        )

        instance = WorkflowRouter.start_workflow_for_request(
            entity=trf, entity_type="travelrequest", initiated_by=regular_user
        )
        assert instance is not None

        new_notifications = UserNotification.objects.filter(user=regular_user).exclude(
            id__in=before_ids
        )
        assert new_notifications.count() == 1
        notification = new_notifications.first()
        assert notification.title.startswith("Workflow Started:")


@pytest.mark.django_db
class TestWorkflowStartedNoDuplication:
    def test_double_submit_does_not_duplicate_workflow_or_notification(
        self, single_step_trf_workflow, regular_user
    ):
        """A retry/double-click that calls start_workflow twice for the same
        entity must reuse the existing WorkflowInstance and must not send a
        second 'Workflow Started' notification."""
        trf = _new_trf(regular_user)
        before_ids = set(
            UserNotification.objects.filter(user=regular_user).values_list(
                "id", flat=True
            )
        )

        first = WorkflowEngine.start_workflow(
            entity=trf, initiated_by=regular_user, module_name="travelrequest"
        )
        second = WorkflowEngine.start_workflow(
            entity=trf, initiated_by=regular_user, module_name="travelrequest"
        )

        assert first.id == second.id

        new_notifications = UserNotification.objects.filter(
            user=regular_user, title__startswith="Workflow Started:"
        ).exclude(id__in=before_ids)
        assert new_notifications.count() == 1

    def test_started_notification_not_duplicated_to_approver(
        self, single_step_trf_workflow, regular_user
    ):
        """notify_workflow_started() must not also notify the first approver -
        that notification already comes from the config-driven 'assignment'
        event fired by WorkflowEngine._start_step()."""
        first_step = single_step_trf_workflow.steps.get(step_order=1)
        first_step.approver_user = regular_user
        first_step.save()

        trf = _new_trf(regular_user)

        WorkflowRouter.start_workflow_for_request(
            entity=trf, entity_type="travelrequest", initiated_by=regular_user
        )

        started_count = UserNotification.objects.filter(
            user=regular_user, title__startswith="Workflow Started:"
        ).count()
        assert started_count == 1
