"""
Regression coverage for a bug found while investigating visa/transport
resubmission: every module's own submit/resubmit view sets the entity's
status to a generic placeholder (e.g. "Pending") before calling
WorkflowRouter.start_workflow_for_request, expecting the workflow engine
to correct it to the real "Pending <Role>" value. That correction
(_update_entity_status_from_step) only ran when a step first *activates*
(_start_step) - a resubmit against an already-active WorkflowInstance
never re-activates the already-pending step, so the entity was left
stuck on the generic placeholder status instead of the step's real one.

WorkflowEngine._apply_resubmit_selection now resyncs the entity's status
from its actual current pending step on every resubmit, regardless of
whether the approver selection itself changed.
"""

import pytest
from trf.models import TravelRequest
from workflows.models import WorkflowStep, WorkflowTemplate
from workflows.router import WorkflowRouter


@pytest.fixture
def two_step_trf_workflow(db, admin_user):
    """A minimal, active two-step workflow template for TravelRequest."""
    template = WorkflowTemplate.objects.create(
        name="Test TRF Two-Step Workflow",
        entity_type="travelrequest",
        is_active=True,
        created_by=admin_user,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=1,
        step_name="Department Focal",
        is_required=True,
        can_skip=True,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=2,
        step_name="HOD",
        is_required=True,
        can_skip=True,
    )
    return template


@pytest.mark.django_db
class TestResubmitStatusResync:
    def test_resubmit_resyncs_status_from_generic_placeholder(
        self, two_step_trf_workflow, regular_user
    ):
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
        assert workflow_instance is not None

        trf.refresh_from_db()
        assert trf.status == "Pending Department Focal"

        # Simulate what every module's own submit/resubmit view does before
        # calling start_workflow_for_request again: reset the entity's
        # status to the generic placeholder. The workflow itself is still
        # active (same in-progress WorkflowInstance, no new one created).
        trf.status = "Pending"
        trf.save(update_fields=["status"])

        second_instance = WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type="travelrequest",
            initiated_by=regular_user,
        )

        # No duplicate WorkflowInstance created.
        assert second_instance.id == workflow_instance.id

        trf.refresh_from_db()
        assert trf.status == "Pending Department Focal"

    def test_resubmit_resyncs_status_even_without_selection_change(
        self, two_step_trf_workflow, regular_user
    ):
        """The status bug reproduces even when the requester doesn't touch
        the approver selection at all on resubmit - the fix must not be
        gated on selected_approvers/skipped_steps being present."""
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )

        WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type="travelrequest",
            initiated_by=regular_user,
        )
        trf.refresh_from_db()
        assert trf.status == "Pending Department Focal"

        trf.status = "Pending"
        trf.save(update_fields=["status"])

        WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type="travelrequest",
            initiated_by=regular_user,
            selected_approvers=None,
            skipped_steps=None,
        )

        trf.refresh_from_db()
        assert trf.status == "Pending Department Focal"

    def test_resubmit_does_not_resync_status_once_step_is_approved(
        self, two_step_trf_workflow, admin_user, regular_user
    ):
        """Once the current step has actually been approved, a resubmit
        must not resurrect its "Pending <Role>" status - the workflow has
        moved on to the next step by then."""
        from workflows.engine import WorkflowEngine

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
        first_step = workflow_instance.step_executions.filter(status="pending").first()
        WorkflowEngine.process_action(
            step_execution_id=first_step.id,
            action="approve",
            actioned_by=admin_user,
            comments="Approved in test",
        )

        trf.refresh_from_db()
        assert trf.status == "Pending HOD"

        trf.status = "Pending"
        trf.save(update_fields=["status"])

        WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type="travelrequest",
            initiated_by=regular_user,
        )

        trf.refresh_from_db()
        assert trf.status == "Pending HOD"
