"""
Tests for transport/services.py - the request-number generation,
workflow-start, and approve/reject dispatch logic extracted from
TransportRequestViewSet (see docs/CODEBASE_REFACTOR_ROADMAP.md item 7).

The approve/reject legacy-fallback path (process_transport_approval_action)
had zero test coverage anywhere before this - not even at the API level -
so these are exercised through the real /approve//reject/ endpoints rather
than mocked, to prove the extraction preserved the original inline
behavior end to end. No WorkflowTemplate is configured in the test DB, so
every case here exercises the legacy-fallback branch (no WorkflowInstance
exists) - the ContentType/WorkflowInstance-found branch is covered by
transport/services.py's own docstring reasoning, not re-tested here.
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from transport.services import (
    generate_unique_transport_request_number,
    start_transport_workflow,
)


@pytest.fixture
def transport_approver_client(db, api_client, create_user):
    """Authenticated client whose user holds approve_transport."""
    from accounts.models import Permission, Role, RolePermission

    perm, _ = Permission.objects.get_or_create(
        name="approve_transport", defaults={"description": "Approve transport requests"}
    )
    role = Role.objects.create(name="Transport Approver Test")
    RolePermission.objects.create(role=role, permission=perm)
    user = create_user(
        email="transport-approver@example.com",
        password="testpass123",
        name="Transport Approver",
        role=role,
    )
    api_client.force_authenticate(user=user)
    return api_client


def _make_transport_request(requestor, status="Pending", **extra):
    from transport.models import TransportRequest

    defaults = dict(
        requestor=requestor,
        requestor_name=requestor.name,
        staff_id="S1",
        department="IT",
        position="Dev",
        purpose="Services test",
        status=status,
        transport_details=[
            {
                "date": "2026-09-01",
                "day": "Tuesday",
                "from": "A",
                "to": "B",
                "departure_time": "09:00",
                "number_of_passengers": 1,
            }
        ],
    )
    defaults.update(extra)
    return TransportRequest.objects.create(**defaults)


@pytest.mark.django_db
class TestGenerateUniqueTransportRequestNumber:
    def test_generates_with_transport_details(self):
        result = generate_unique_transport_request_number(
            transport_details=[{"date": "2026-09-01", "to": "Ashgabat"}],
            applicant_name="Jane Doe",
        )
        assert result is not None
        assert result.startswith("TRN-")

    def test_generates_with_no_transport_details(self):
        result = generate_unique_transport_request_number(
            transport_details=[], applicant_name="Jane Doe"
        )
        assert result is not None
        assert result.startswith("TRN-")


@pytest.mark.django_db
class TestStartTransportWorkflow:
    def test_starts_workflow_and_refreshes_on_success(self):
        transport_request = MagicMock(id=1, status="Pending")
        workflow_instance = MagicMock(id=99)
        with patch("workflows.router.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = workflow_instance
            result = start_transport_workflow(transport_request, {}, MagicMock())

        assert result is workflow_instance
        transport_request.refresh_from_db.assert_called_once()
        mock_router.start_workflow_for_request.assert_called_once()
        call_kwargs = mock_router.start_workflow_for_request.call_args.kwargs
        assert call_kwargs["entity"] is transport_request
        assert call_kwargs["entity_type"] == "transportrequest"

    def test_parses_selected_approvers_and_skipped_steps_to_int_keys(self):
        transport_request = MagicMock(id=1, status="Pending")
        request_data = {
            "selected_approvers": {"5": "user-a"},
            "skipped_steps": {"7": True},
        }
        with patch("workflows.router.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = None
            start_transport_workflow(transport_request, request_data, MagicMock())

        call_kwargs = mock_router.start_workflow_for_request.call_args.kwargs
        assert call_kwargs["selected_approvers"] == {5: "user-a"}
        assert call_kwargs["skipped_steps"] == {7: True}

    def test_no_refresh_when_no_workflow_instance_returned(self):
        transport_request = MagicMock(id=1, status="Pending")
        with patch("workflows.router.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = None
            result = start_transport_workflow(transport_request, {}, MagicMock())

        assert result is None
        transport_request.refresh_from_db.assert_not_called()


@pytest.mark.django_db
class TestProcessTransportApprovalActionLegacyFallback:
    """No WorkflowInstance exists in these cases (no WorkflowTemplate
    configured), so every call here exercises the legacy fallback branch
    of process_transport_approval_action via the real API endpoints."""

    def test_approve_without_permission_is_forbidden(
        self, authenticated_client, regular_user
    ):
        tr = _make_transport_request(regular_user)
        response = authenticated_client.post(
            f"/api/transport/requests/{tr.id}/approve/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_approve_with_no_pending_step_returns_400(
        self, transport_approver_client, regular_user
    ):
        tr = _make_transport_request(regular_user)  # no TransportApprovalStep created
        response = transport_approver_client.post(
            f"/api/transport/requests/{tr.id}/approve/"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No pending approval step" in response.data["error"]

    def test_approve_advances_status_via_progression_map(
        self, transport_approver_client, regular_user
    ):
        from transport.models import TransportApprovalStep

        tr = _make_transport_request(regular_user, status="Pending Department Focal")
        TransportApprovalStep.objects.create(
            transport_request=tr,
            step_role="Department Focal",
            step_name="Department Focal Approval",
            status="Pending",
        )

        response = transport_approver_client.post(
            f"/api/transport/requests/{tr.id}/approve/", {"comments": "looks good"}
        )

        assert response.status_code == status.HTTP_200_OK
        tr.refresh_from_db()
        assert tr.status == "Pending HOD"
        step = tr.approval_steps.get()
        assert step.status == "Approved"
        assert step.comments == "looks good"

    def test_approve_at_hod_step_marks_request_approved(
        self, transport_approver_client, regular_user
    ):
        from transport.models import TransportApprovalStep

        tr = _make_transport_request(regular_user, status="Pending HOD")
        TransportApprovalStep.objects.create(
            transport_request=tr,
            step_role="HOD",
            step_name="HOD Approval",
            status="Pending",
        )

        response = transport_approver_client.post(
            f"/api/transport/requests/{tr.id}/approve/"
        )

        assert response.status_code == status.HTTP_200_OK
        tr.refresh_from_db()
        assert tr.status == "Approved"

    def test_reject_without_permission_is_forbidden(
        self, authenticated_client, regular_user
    ):
        tr = _make_transport_request(regular_user)
        response = authenticated_client.post(f"/api/transport/requests/{tr.id}/reject/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reject_sets_status_unconditionally_even_with_no_pending_step(
        self, transport_approver_client, regular_user
    ):
        # Unlike approve, the original reject legacy fallback has no guard
        # for a missing pending step - it still marks the request Rejected.
        # This asymmetry is preserved deliberately (see services.py
        # docstring), not fixed, so this test locks in that exact behavior.
        tr = _make_transport_request(regular_user)  # no TransportApprovalStep
        response = transport_approver_client.post(
            f"/api/transport/requests/{tr.id}/reject/", {"comments": "no"}
        )

        assert response.status_code == status.HTTP_200_OK
        tr.refresh_from_db()
        assert tr.status == "Rejected"

    def test_reject_updates_pending_step_when_present(
        self, transport_approver_client, regular_user
    ):
        from transport.models import TransportApprovalStep

        tr = _make_transport_request(regular_user, status="Pending Department Focal")
        TransportApprovalStep.objects.create(
            transport_request=tr,
            step_role="Department Focal",
            step_name="Department Focal Approval",
            status="Pending",
        )

        response = transport_approver_client.post(
            f"/api/transport/requests/{tr.id}/reject/", {"comments": "declined"}
        )

        assert response.status_code == status.HTTP_200_OK
        tr.refresh_from_db()
        assert tr.status == "Rejected"
        step = tr.approval_steps.get()
        assert step.status == "Rejected"
        assert step.comments == "declined"
