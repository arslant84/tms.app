"""
Regression coverage for WorkflowEngine.process_action's audit trail (Fix 1
of docs/APPROVAL_WORKFLOW_FIX_ROADMAP.md) and, longer-term, a place to assert
that the three approval code paths (WorkflowEngine.process_action,
approvals.bulk_approve, WorkflowStepExecutionViewSet.take_action) leave the
entity/workflow state consistent (Fix 2).
"""

import pytest
from accounts.models import AdminActionLog
from trf.models import TravelRequest
from workflows.engine import WorkflowEngine
from workflows.models import WorkflowStep, WorkflowTemplate
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


@pytest.mark.django_db
class TestProcessActionAuditLog:
    def test_approve_writes_admin_action_log(
        self, single_step_trf_workflow, admin_user, regular_user
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

        step_execution = workflow_instance.step_executions.filter(
            status="pending"
        ).first()
        assert step_execution is not None

        WorkflowEngine.process_action(
            step_execution_id=step_execution.id,
            action="approve",
            actioned_by=admin_user,
            comments="Approved in test",
        )

        trf.refresh_from_db()
        workflow_instance.refresh_from_db()
        assert workflow_instance.status == "approved"
        assert trf.status == "Approved"

        log_entry = AdminActionLog.objects.filter(
            action_type="workflow_step_approved",
            entity_type="travelrequest",
            entity_id=str(trf.id),
        ).first()
        assert log_entry is not None
        assert log_entry.user_id == admin_user.id

    def test_reject_writes_admin_action_log(
        self, single_step_trf_workflow, admin_user, regular_user
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
        step_execution = workflow_instance.step_executions.filter(
            status="pending"
        ).first()

        WorkflowEngine.process_action(
            step_execution_id=step_execution.id,
            action="reject",
            actioned_by=admin_user,
            comments="Rejected in test",
        )

        trf.refresh_from_db()
        assert trf.status == "Rejected"

        log_entry = AdminActionLog.objects.filter(
            action_type="workflow_step_rejected",
            entity_type="travelrequest",
            entity_id=str(trf.id),
        ).first()
        assert log_entry is not None


@pytest.mark.django_db
class TestTakeActionUpdatesEntityStatus:
    """
    Regression test for Fix 2a: WorkflowStepExecutionViewSet.take_action used
    to update only WorkflowInstance/WorkflowStepExecution and never touch the
    underlying entity's `status` field. It now delegates to
    WorkflowEngine.process_action, which does update entity status.
    """

    def test_approve_via_take_action_endpoint_updates_trf_status(
        self, single_step_trf_workflow, admin_client, admin_user, regular_user
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
        step_execution = workflow_instance.step_executions.filter(
            status="pending"
        ).first()

        response = admin_client.post(
            f"/api/workflows/executions/{step_execution.id}/take_action/",
            {"action": "approve", "comments": "Approved via take_action"},
        )

        assert response.status_code == 200

        trf.refresh_from_db()
        workflow_instance.refresh_from_db()
        assert workflow_instance.status == "approved"
        assert trf.status == "Approved"

        assert AdminActionLog.objects.filter(
            action_type="workflow_step_approved",
            entity_type="travelrequest",
            entity_id=str(trf.id),
        ).exists()


@pytest.mark.django_db
class TestBulkApproveConsolidation:
    """
    Regression test for Fix 2b: approvals.bulk_approve used to hand-roll its
    own step advancement and entity status transitions. It now delegates to
    WorkflowEngine.process_action, matching the behavior of the other two
    approval entry points, while still writing its own bulk-specific audit
    entry in addition to the engine's per-step entry.
    """

    def test_bulk_approve_updates_trf_status_and_logs_both_entries(
        self, single_step_trf_workflow, admin_client, admin_user, regular_user
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

        response = admin_client.post(
            "/api/admin/approvals/bulk/",
            {
                "items": [{"id": trf.id, "type": "trf"}],
                "action": "approve",
                "comments": "Bulk approved in test",
            },
            format="json",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["success"] == [
            {"id": trf.id, "type": "trf", "new_status": "Approved"}
        ]
        assert body["data"]["failed"] == []

        trf.refresh_from_db()
        workflow_instance.refresh_from_db()
        assert trf.status == "Approved"
        assert workflow_instance.status == "approved"

        # One entry from WorkflowEngine.process_action, one from bulk_approve itself.
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_approved",
            entity_type="travelrequest",
            entity_id=str(trf.id),
        ).exists()
        assert AdminActionLog.objects.filter(
            action_type="workflow_bulk_approve",
            entity_type="trf",
            entity_id=str(trf.id),
        ).exists()
