"""
Tests for visa/services.py - the request-number generation, workflow-start,
approve/reject dispatch, and processing-completion logic extracted from
VisaApplicationViewSet (see docs/CODEBASE_REFACTOR_ROADMAP.md item 8).

The approve/reject legacy-fallback path (process_visa_approval_action) and
the perform_update "Approved -> Completed" notification bug fix
(finalize_visa_workflow_completion) had zero test coverage anywhere before
this - exercised here through the real API endpoints where practical, same
approach as tests/transport/test_services.py.
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from visa.models import VisaApplication
from visa.services import generate_unique_visa_request_number, start_visa_workflow


@pytest.fixture
def visa_approver_client(db, api_client, create_user):
    """Authenticated client whose user holds approve_visa."""
    from accounts.models import Permission, Role, RolePermission

    perm, _ = Permission.objects.get_or_create(
        name="approve_visa", defaults={"description": "Approve visa applications"}
    )
    role = Role.objects.create(name="Visa Approver Test")
    RolePermission.objects.create(role=role, permission=perm)
    user = create_user(
        email="visa-approver@example.com",
        password="testpass123",
        name="Visa Approver",
        role=role,
    )
    api_client.force_authenticate(user=user)
    return api_client


def _make_visa(user, status="Pending", **extra):
    defaults = dict(
        user=user,
        requestor_name=user.name,
        staff_id="S1",
        department="IT",
        destination="Some Country",
        travel_purpose="Business",
        visa_type="Business",
        status=status,
    )
    defaults.update(extra)
    return VisaApplication.objects.create(**defaults)


@pytest.mark.django_db
class TestGenerateUniqueVisaRequestNumber:
    def test_generates_with_destination(self):
        result = generate_unique_visa_request_number(
            destination="Ashgabat", trip_start_date=None, applicant_name="Jane Doe"
        )
        assert result is not None
        assert result.startswith("VIS-")


@pytest.mark.django_db
class TestStartVisaWorkflow:
    def test_starts_workflow_and_refreshes_on_success(self):
        visa_application = MagicMock(id=1, status="Pending")
        workflow_instance = MagicMock(id=99)
        with patch("workflows.router.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = workflow_instance
            result = start_visa_workflow(visa_application, {}, MagicMock())

        assert result is workflow_instance
        visa_application.refresh_from_db.assert_called_once()
        call_kwargs = mock_router.start_workflow_for_request.call_args.kwargs
        assert call_kwargs["entity"] is visa_application
        assert call_kwargs["entity_type"] == "visaapplication"

    def test_no_refresh_when_no_workflow_instance_returned(self):
        visa_application = MagicMock(id=1, status="Pending")
        with patch("workflows.router.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = None
            result = start_visa_workflow(visa_application, {}, MagicMock())

        assert result is None
        visa_application.refresh_from_db.assert_not_called()


@pytest.mark.django_db
class TestProcessVisaApprovalActionLegacyFallback:
    """No WorkflowInstance exists in these cases (no WorkflowTemplate
    configured), so every call here exercises the legacy fallback branch
    via the real API endpoints."""

    def test_approve_without_permission_is_forbidden(
        self, authenticated_client, regular_user
    ):
        visa = _make_visa(regular_user)
        response = authenticated_client.post(
            f"/api/visa/applications/{visa.id}/approve/",
            {"step_role": "Department Focal"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_approve_advances_status_via_progression_map(
        self, visa_approver_client, regular_user
    ):
        visa = _make_visa(regular_user, status="Pending Department Focal")

        response = visa_approver_client.post(
            f"/api/visa/applications/{visa.id}/approve/",
            {"step_role": "Department Focal", "comments": "ok"},
        )

        assert response.status_code == status.HTTP_200_OK
        visa.refresh_from_db()
        assert visa.status == "Pending HOD"
        step = visa.visaapprovalstep_set.get(step_role="Department Focal")
        assert step.status == "Approved"
        assert step.comments == "ok"

    def test_approve_at_hod_step_marks_visa_approved(
        self, visa_approver_client, regular_user
    ):
        visa = _make_visa(regular_user, status="Pending HOD")

        response = visa_approver_client.post(
            f"/api/visa/applications/{visa.id}/approve/", {"step_role": "HOD"}
        )

        assert response.status_code == status.HTTP_200_OK
        visa.refresh_from_db()
        assert visa.status == "Approved"

    def test_reject_without_permission_is_forbidden(
        self, authenticated_client, regular_user
    ):
        visa = _make_visa(regular_user)
        response = authenticated_client.post(
            f"/api/visa/applications/{visa.id}/reject/",
            {"step_role": "Department Focal"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reject_sets_status_unconditionally(
        self, visa_approver_client, regular_user
    ):
        visa = _make_visa(regular_user, status="Pending Department Focal")

        response = visa_approver_client.post(
            f"/api/visa/applications/{visa.id}/reject/",
            {"step_role": "Department Focal", "comments": "no"},
        )

        assert response.status_code == status.HTTP_200_OK
        visa.refresh_from_db()
        assert visa.status == "Rejected"
        step = visa.visaapprovalstep_set.get(step_role="Department Focal")
        assert step.status == "Rejected"
        assert step.comments == "no"


@pytest.mark.django_db
class TestFinalizeVisaWorkflowCompletionNotificationFix:
    """Regression test for the bug flagged in
    docs/CODEBASE_REFACTOR_ROADMAP.md item 8: perform_update's own
    "Approved -> Completed" branch used to mark the WorkflowInstance
    completed inline WITHOUT calling notify_processing_completed - only
    the dedicated `complete` action did. A client PATCHing status straight
    to "Completed" silently skipped the notification. Both paths now call
    the same finalize_visa_workflow_completion, so both fire it."""

    def test_patching_status_to_completed_fires_notification(
        self, api_client, admin_user, regular_user
    ):
        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance, WorkflowTemplate

        visa = _make_visa(regular_user, status="Approved")
        content_type = ContentType.objects.get_for_model(visa)
        template = WorkflowTemplate.objects.create(
            name="Visa Completion Notification Test Template", entity_type="visa"
        )
        workflow_instance = WorkflowInstance.objects.create(
            workflow_template=template,
            content_type=content_type,
            object_id=visa.id,
            status="approved",
        )

        api_client.force_authenticate(user=admin_user)
        with patch(
            "workflows.notifications.WorkflowNotifications.notify_processing_completed"
        ) as mock_notify:
            response = api_client.patch(
                f"/api/visa/applications/{visa.id}/",
                {"status": "Completed"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        workflow_instance.refresh_from_db()
        assert workflow_instance.status == "completed"
        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs["completed_by"] == admin_user
