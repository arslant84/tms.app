"""
Regression coverage for skip-during-submission behavior: when a requester
marks a step's approver selection as "skip" (approver not available), the
step is auto-skipped and the workflow advances to the next step (or
completes, if it was the last one) - it does not wait for a real approval
decision, regardless of whether a fallback approver could be resolved for
that step's role/permission.

This was a deliberate product decision made after an earlier, narrower
version of this logic left a step permanently stuck "pending" with no
assignee whenever skip was requested and no fallback approver existed
(nobody could ever act on it). An even earlier version had the opposite
problem: it never auto-advanced skip at all, requiring a fallback approver
to explicitly review a step the requester had already tried to skip. The
current behavior always auto-advances on skip.

Note this is unrelated to WorkflowStepExecution's "skip" *action* (an
approver explicitly clicking "Skip" on their own pending step via
take_action/process_action) - that has always advanced the workflow
correctly and is covered elsewhere.
"""

import pytest
from transport.models import TransportRequest
from trf.models import TravelRequest
from visa.models import VisaApplication
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


@pytest.fixture
def two_step_transport_workflow(db, admin_user):
    """Same shape as two_step_no_approver_workflow but for transportrequest,
    proving the skip-auto-advance fix is entity-agnostic (it lives in the
    shared WorkflowEngine, not TRF-specific code)."""
    template = WorkflowTemplate.objects.create(
        name="Test Skip Transport Two-Step Workflow",
        entity_type="transportrequest",
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
def two_step_visa_workflow(db, admin_user):
    """Same shape as two_step_no_approver_workflow but for visaapplication."""
    template = WorkflowTemplate.objects.create(
        name="Test Skip Visa Two-Step Workflow",
        entity_type="visaapplication",
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
class TestSkipAlwaysAutoAdvances:
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

    def test_skip_advances_even_when_fallback_approver_exists(
        self, two_step_trf_workflow, regular_user, admin_user
    ):
        """Product decision: skip always bypasses the step and advances the
        workflow, even when a real fallback approver exists for that
        step's role - the fallback approver is never assigned or notified
        for a step the requester explicitly skipped."""
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )

        step_1 = two_step_trf_workflow.steps.get(step_order=1)
        step_1.approver_user = admin_user
        step_1.save(update_fields=["approver_user"])

        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type="travelrequest",
            initiated_by=regular_user,
            skipped_steps={
                1: "Requester skipped selection despite a fallback existing"
            },
        )

        trf.refresh_from_db()
        assert workflow_instance.status == "in_progress"
        assert trf.status == "Pending HOD"

        step_1_execution = workflow_instance.step_executions.get(
            workflow_step__step_order=1
        )
        assert step_1_execution.status == "skipped"
        assert step_1_execution.assigned_to is None

        step_2_execution = workflow_instance.step_executions.get(
            workflow_step__step_order=2
        )
        assert step_2_execution.status == "pending"


@pytest.mark.django_db
class TestSkipAlwaysAutoAdvancesTransport:
    """Proves the skip-auto-advance fix works for TransportRequest too -
    it lives in the shared WorkflowEngine, not TRF-specific code."""

    def test_skip_advances_even_when_fallback_approver_exists(
        self, two_step_transport_workflow, regular_user, admin_user
    ):
        tr = TransportRequest.objects.create(
            requestor=regular_user,
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            position="Dev",
            purpose="Skip auto-advance test",
            status="Pending",
            transport_details=[
                {
                    "date": "2026-09-01",
                    "day": "Tuesday",
                    "from": "A",
                    "to": "B",
                    "departureTime": "09:00",
                    "numberOfPassengers": 1,
                }
            ],
        )

        step_1 = two_step_transport_workflow.steps.get(step_order=1)
        step_1.approver_user = admin_user
        step_1.save(update_fields=["approver_user"])

        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=tr,
            entity_type="transportrequest",
            initiated_by=regular_user,
            skipped_steps={
                1: "Requester skipped selection despite a fallback existing"
            },
        )

        tr.refresh_from_db()
        assert workflow_instance.status == "in_progress"
        assert tr.status == "Pending HOD"

        step_1_execution = workflow_instance.step_executions.get(
            workflow_step__step_order=1
        )
        assert step_1_execution.status == "skipped"
        assert step_1_execution.assigned_to is None

    def test_skip_completes_workflow_when_no_fallback_and_last_step(
        self, two_step_transport_workflow, regular_user
    ):
        tr = TransportRequest.objects.create(
            requestor=regular_user,
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            position="Dev",
            purpose="Skip both steps test",
            status="Pending",
            transport_details=[
                {
                    "date": "2026-09-01",
                    "day": "Tuesday",
                    "from": "A",
                    "to": "B",
                    "departureTime": "09:00",
                    "numberOfPassengers": 1,
                }
            ],
        )

        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=tr,
            entity_type="transportrequest",
            initiated_by=regular_user,
            skipped_steps={1: "No one available", 2: "No one available"},
        )

        tr.refresh_from_db()
        assert workflow_instance.status == "approved"
        assert tr.status == "Approved"


@pytest.mark.django_db
class TestSkipAlwaysAutoAdvancesVisa:
    """Proves the skip-auto-advance fix works for VisaApplication too -
    it lives in the shared WorkflowEngine, not TRF-specific code."""

    def test_skip_advances_even_when_fallback_approver_exists(
        self, two_step_visa_workflow, regular_user, admin_user
    ):
        visa = VisaApplication.objects.create(
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            destination="Some Country",
            travel_purpose="Business",
            visa_type="Business",
            status="Pending",
        )

        step_1 = two_step_visa_workflow.steps.get(step_order=1)
        step_1.approver_user = admin_user
        step_1.save(update_fields=["approver_user"])

        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=visa,
            entity_type="visaapplication",
            initiated_by=regular_user,
            skipped_steps={
                1: "Requester skipped selection despite a fallback existing"
            },
        )

        visa.refresh_from_db()
        assert workflow_instance.status == "in_progress"
        assert visa.status == "Pending HOD"

        step_1_execution = workflow_instance.step_executions.get(
            workflow_step__step_order=1
        )
        assert step_1_execution.status == "skipped"
        assert step_1_execution.assigned_to is None

    def test_skip_completes_workflow_when_no_fallback_and_last_step(
        self, two_step_visa_workflow, regular_user
    ):
        visa = VisaApplication.objects.create(
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            destination="Some Country",
            travel_purpose="Business",
            visa_type="Business",
            status="Pending",
        )

        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=visa,
            entity_type="visaapplication",
            initiated_by=regular_user,
            skipped_steps={1: "No one available", 2: "No one available"},
        )

        visa.refresh_from_db()
        assert workflow_instance.status == "approved"
        assert visa.status == "Approved"
