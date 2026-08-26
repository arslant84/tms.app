"""
Regression coverage for a bug reported on the Transport module: when a
requester marks a step's approver selection as "skip" (approver not
available) and no fallback approver can be resolved for that step either
(nobody holds the configured role/permission), the step was left
permanently "pending" with no assignee - nobody could ever act on it, so
the whole workflow (and the entity's status) got stuck forever.

WorkflowEngine._start_step now detects this specific case (skip requested
AND no fallback approver exists) and auto-skips the step, advancing to the
next step or completing the workflow - same as if a real approver had
approved it. This is narrower than the auto-advance-on-skip bug from the
past incident referenced in _start_step's comments: that bug fired on
skip alone, even when a real fallback approver existed; this only fires
when no approver exists at all.
"""

import pytest
from trf.models import TravelRequest
from workflows.models import WorkflowStep, WorkflowTemplate
from workflows.router import WorkflowRouter


@pytest.fixture
def two_step_no_approver_workflow(db, admin_user):
    """A two-step workflow template where neither step has any
    approver_role/approver_permission/approver_user configured, so
    _resolve_step_assignee can never find anyone for either step."""
    template = WorkflowTemplate.objects.create(
        name="Test Skip-No-Fallback Two-Step Workflow",
        entity_type="travelrequest",
        is_active=True,
        created_by=admin_user,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=1,
        step_name="Ghost Step 1",
        is_required=True,
        can_skip=True,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=2,
        step_name="Ghost Step 2",
        is_required=True,
        can_skip=True,
    )
    return template


@pytest.fixture
def two_step_trf_workflow(db, admin_user):
    """A minimal, active two-step workflow template for TravelRequest,
    mirroring tests/workflows/test_resubmit_status_resync.py's fixture of
    the same name (duplicated here since pytest fixtures aren't shared
    across test modules without a conftest.py entry)."""
    template = WorkflowTemplate.objects.create(
        name="Test TRF Two-Step Workflow (skip-fallback)",
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


@pytest.fixture
def single_step_no_approver_workflow(db, admin_user):
    """A single-step workflow template with no resolvable approver."""
    template = WorkflowTemplate.objects.create(
        name="Test Skip-No-Fallback Single-Step Workflow",
        entity_type="travelrequest",
        is_active=True,
        created_by=admin_user,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=1,
        step_name="Ghost Only Step",
        is_required=True,
        can_skip=True,
    )
    return template


@pytest.mark.django_db
class TestSkipWithNoFallbackApprover:
    def test_skip_advances_to_next_step_when_no_fallback_exists(
        self, two_step_no_approver_workflow, regular_user
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
            skipped_steps={1: "No one available for Ghost Step 1"},
        )

        trf.refresh_from_db()
        assert workflow_instance.status == "in_progress"
        assert trf.status == "Pending Ghost Step 2"

        executions = {
            se.workflow_step.step_order: se
            for se in workflow_instance.step_executions.select_related("workflow_step")
        }
        assert executions[1].status == "skipped"
        assert executions[1].assigned_to is None
        assert executions[2].status == "pending"

    def test_skip_completes_workflow_when_it_is_the_only_step(
        self, single_step_no_approver_workflow, regular_user
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
            skipped_steps={1: "No one available"},
        )

        trf.refresh_from_db()
        assert workflow_instance.status == "approved"
        assert trf.status == "Approved"

        execution = workflow_instance.step_executions.first()
        assert execution.status == "skipped"
        assert execution.assigned_to is None

    def test_skip_does_not_auto_advance_when_fallback_approver_exists(
        self, two_step_trf_workflow, regular_user, admin_user
    ):
        """Guards the past-incident regression this fix must not
        reintroduce: skip alone (with a real fallback approver available)
        must NOT auto-advance - a real person must still act."""
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )

        # two_step_trf_workflow's steps have no approver_role/permission/user
        # configured either, so this test needs its own fixture-independent
        # setup: give step 1 a real fallback via approver_user.
        step_1 = two_step_trf_workflow.steps.get(step_order=1)
        step_1.approver_user = admin_user
        step_1.save(update_fields=["approver_user"])

        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type="travelrequest",
            initiated_by=regular_user,
            skipped_steps={1: "Requester skipped selection, but a fallback exists"},
        )

        trf.refresh_from_db()
        assert workflow_instance.status == "in_progress"
        assert trf.status == "Pending Department Focal"

        execution = workflow_instance.step_executions.get(workflow_step__step_order=1)
        assert execution.status == "pending"
        assert execution.assigned_to_id == admin_user.id
