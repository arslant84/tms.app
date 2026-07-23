"""
Regression tests for the "no active WorkflowTemplate" legacy-fallback
authorization gap found while expanding docs/ARCHITECTURE.md's data flow
coverage (2026-07-22).

Before this fix, when trf/visa/transport/accommodation/combined_request had
no active WorkflowInstance for a request (e.g. no WorkflowTemplate configured
for that entity_type), their approve()/reject() actions fell back to legacy
status-mutation logic that only required IsAuthenticated at the ViewSet
class level — any authenticated user, regardless of role, could approve or
reject a request. The main WorkflowEngine.process_action path already
enforces role-based authorization (_is_user_authorized); these tests assert
the fallback path now enforces the equivalent accounts.utils.can_approve()
check for every app.
"""

import pytest
from accounts.models import Permission, Role, RolePermission
from rest_framework import status


@pytest.fixture
def make_approver(db):
    """Factory fixture: create a user whose role has the given approve_* permission."""

    def _make_approver(permission_name, email):
        from accounts.models import User

        permission, _ = Permission.objects.get_or_create(
            name=permission_name, defaults={"description": permission_name}
        )
        role = Role.objects.create(name=f"Approver ({permission_name})")
        RolePermission.objects.create(role=role, permission=permission)
        user = User.objects.create_user(
            email=email, password="testpass123", name="Approver User", role=role
        )
        return user

    return _make_approver


@pytest.mark.django_db
class TestTrfLegacyFallbackAuthorization:
    def test_approve_without_permission_is_forbidden(self, api_client, regular_user):
        from trf.models import TravelRequest

        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=regular_user)

        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/approve/",
            {"step_role": "Department Focal", "comments": ""},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_approve_with_permission_succeeds(self, api_client, make_approver):
        from trf.models import TravelRequest

        approver = make_approver("approve_trf", "trf-approver@example.com")
        trf = TravelRequest.objects.create(
            requestor_name="Someone",
            travel_type="Domestic",
            status="Pending",
            created_by=approver,
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/approve/",
            {"step_role": "Department Focal", "comments": ""},
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestVisaLegacyFallbackAuthorization:
    def test_approve_without_permission_is_forbidden(self, api_client, regular_user):
        from visa.models import VisaApplication

        visa = VisaApplication.objects.create(
            requestor_name=regular_user.name,
            destination="Test",
            travel_purpose="Business",
            visa_type="Business",
            status="Pending",
            user=regular_user,
        )
        api_client.force_authenticate(user=regular_user)

        response = api_client.post(
            f"/api/visa/applications/{visa.id}/approve/",
            {"step_role": "Department Focal", "comments": ""},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_approve_with_permission_succeeds(self, api_client, make_approver):
        from visa.models import VisaApplication

        approver = make_approver("approve_visa", "visa-approver@example.com")
        visa = VisaApplication.objects.create(
            requestor_name="Someone",
            destination="Test",
            travel_purpose="Business",
            visa_type="Business",
            status="Pending",
            user=approver,
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/visa/applications/{visa.id}/approve/",
            {"step_role": "Department Focal", "comments": ""},
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTransportLegacyFallbackAuthorization:
    def test_approve_without_permission_is_forbidden(self, api_client, regular_user):
        from transport.models import TransportRequest

        transport_request = TransportRequest.objects.create(
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            position="Engineer",
            purpose="Business",
            status="Pending",
            requestor=regular_user,
        )
        api_client.force_authenticate(user=regular_user)

        response = api_client.post(
            f"/api/transport/requests/{transport_request.id}/approve/",
            {"comments": ""},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_approve_with_permission_succeeds(self, api_client, make_approver):
        from transport.models import TransportApprovalStep, TransportRequest

        approver = make_approver("approve_transport", "transport-approver@example.com")
        transport_request = TransportRequest.objects.create(
            requestor_name="Someone",
            staff_id="S1",
            department="IT",
            position="Engineer",
            purpose="Business",
            status="Pending",
            requestor=approver,
        )
        TransportApprovalStep.objects.create(
            transport_request=transport_request,
            step_role="Department Focal",
            status="Pending",
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/transport/requests/{transport_request.id}/approve/",
            {"comments": ""},
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAccommodationLegacyFallbackAuthorization:
    def test_approve_without_permission_is_forbidden(self, api_client, regular_user):
        from accommodation.models import AccommodationRequest

        accommodation_request = AccommodationRequest.objects.create(
            requestor_name=regular_user.name,
            status="Pending",
        )
        api_client.force_authenticate(user=regular_user)

        response = api_client.post(
            f"/api/accommodation/requests/{accommodation_request.id}/approve/",
            {"comments": ""},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_approve_with_permission_succeeds(self, api_client, make_approver):
        from accommodation.models import AccommodationRequest

        approver = make_approver(
            "approve_accommodation", "accommodation-approver@example.com"
        )
        accommodation_request = AccommodationRequest.objects.create(
            requestor_name="Someone",
            status="Pending",
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/accommodation/requests/{accommodation_request.id}/approve/",
            {"comments": ""},
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCombinedRequestLegacyFallbackAuthorization:
    def test_approve_without_permission_is_forbidden(self, api_client, regular_user):
        from combined_request.models import CombinedRequest

        combined_request = CombinedRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            requestor=regular_user,
        )
        api_client.force_authenticate(user=regular_user)

        response = api_client.post(
            f"/api/combined/combined-requests/{combined_request.id}/approve/",
            {"step_role": "", "comments": ""},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_approve_with_permission_succeeds(self, api_client, make_approver):
        from combined_request.models import CombinedRequest

        approver = make_approver("approve_combined", "combined-approver@example.com")
        combined_request = CombinedRequest.objects.create(
            requestor_name="Someone",
            travel_type="Domestic",
            status="Pending",
            requestor=approver,
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/combined/combined-requests/{combined_request.id}/approve/",
            {"step_role": "", "comments": ""},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_reject_without_permission_is_forbidden(self, api_client, regular_user):
        """combined_request's legacy reject fallback previously had no
        status check OR permission check at all — the weakest of the five."""
        from combined_request.models import CombinedRequest

        combined_request = CombinedRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            requestor=regular_user,
        )
        api_client.force_authenticate(user=regular_user)

        response = api_client.post(
            f"/api/combined/combined-requests/{combined_request.id}/reject/",
            {"step_role": "", "comments": "not good"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestLegacyFallbackAuditLogging:
    """
    Regression tests for the 2026-07-23 follow-up: the legacy-fallback
    approve()/reject() branches enforced authorization (above) but wrote
    zero AdminActionLog entries anywhere - only the WorkflowEngine.process_action
    path (real WorkflowTemplate) logged. These tests assert every one of
    the 10 fallback branches (5 apps x approve/reject) now writes an entry.
    """

    def test_trf_approve_fallback_writes_audit_log(self, api_client, make_approver):
        from accounts.models import AdminActionLog
        from trf.models import TravelRequest

        approver = make_approver("approve_trf", "trf-audit-approver@example.com")
        trf = TravelRequest.objects.create(
            requestor_name="Someone",
            travel_type="Domestic",
            status="Pending",
            created_by=approver,
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/approve/",
            {"step_role": "Department Focal", "comments": "looks good"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_approved",
            entity_type="travelrequest",
            entity_id=str(trf.id),
        ).exists()

    def test_trf_reject_fallback_writes_audit_log(self, api_client, make_approver):
        from accounts.models import AdminActionLog
        from trf.models import TravelRequest

        approver = make_approver("approve_trf", "trf-audit-rejecter@example.com")
        trf = TravelRequest.objects.create(
            requestor_name="Someone",
            travel_type="Domestic",
            status="Pending",
            created_by=approver,
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/reject/",
            {"step_role": "Department Focal", "comments": "not eligible"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_rejected",
            entity_type="travelrequest",
            entity_id=str(trf.id),
        ).exists()

    def test_visa_approve_fallback_writes_audit_log(self, api_client, make_approver):
        from accounts.models import AdminActionLog
        from visa.models import VisaApplication

        approver = make_approver("approve_visa", "visa-audit-approver@example.com")
        visa = VisaApplication.objects.create(
            requestor_name="Someone",
            destination="Test",
            travel_purpose="Business",
            visa_type="Business",
            status="Pending",
            user=approver,
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/visa/applications/{visa.id}/approve/",
            {"step_role": "Department Focal", "comments": ""},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_approved",
            entity_type="visaapplication",
            entity_id=str(visa.id),
        ).exists()

    def test_visa_reject_fallback_writes_audit_log(self, api_client, make_approver):
        from accounts.models import AdminActionLog
        from visa.models import VisaApplication

        approver = make_approver("approve_visa", "visa-audit-rejecter@example.com")
        visa = VisaApplication.objects.create(
            requestor_name="Someone",
            destination="Test",
            travel_purpose="Business",
            visa_type="Business",
            status="Pending",
            user=approver,
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/visa/applications/{visa.id}/reject/",
            {"step_role": "Department Focal", "comments": "missing docs"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_rejected",
            entity_type="visaapplication",
            entity_id=str(visa.id),
        ).exists()

    def test_transport_approve_fallback_writes_audit_log(
        self, api_client, make_approver
    ):
        from accounts.models import AdminActionLog
        from transport.models import TransportApprovalStep, TransportRequest

        approver = make_approver(
            "approve_transport", "transport-audit-approver@example.com"
        )
        transport_request = TransportRequest.objects.create(
            requestor_name="Someone",
            staff_id="S1",
            department="IT",
            position="Engineer",
            purpose="Business",
            status="Pending",
            requestor=approver,
        )
        TransportApprovalStep.objects.create(
            transport_request=transport_request,
            step_role="Department Focal",
            status="Pending",
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/transport/requests/{transport_request.id}/approve/",
            {"comments": ""},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_approved",
            entity_type="transportrequest",
            entity_id=str(transport_request.id),
        ).exists()

    def test_transport_reject_fallback_writes_audit_log(
        self, api_client, make_approver
    ):
        from accounts.models import AdminActionLog
        from transport.models import TransportApprovalStep, TransportRequest

        approver = make_approver(
            "approve_transport", "transport-audit-rejecter@example.com"
        )
        transport_request = TransportRequest.objects.create(
            requestor_name="Someone",
            staff_id="S1",
            department="IT",
            position="Engineer",
            purpose="Business",
            status="Pending",
            requestor=approver,
        )
        TransportApprovalStep.objects.create(
            transport_request=transport_request,
            step_role="Department Focal",
            status="Pending",
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/transport/requests/{transport_request.id}/reject/",
            {"comments": "not needed"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_rejected",
            entity_type="transportrequest",
            entity_id=str(transport_request.id),
        ).exists()

    def test_accommodation_approve_fallback_writes_audit_log(
        self, api_client, make_approver
    ):
        from accommodation.models import AccommodationRequest
        from accounts.models import AdminActionLog

        approver = make_approver(
            "approve_accommodation", "accommodation-audit-approver@example.com"
        )
        accommodation_request = AccommodationRequest.objects.create(
            requestor_name="Someone",
            status="Pending",
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/accommodation/requests/{accommodation_request.id}/approve/",
            {"comments": ""},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_approved",
            entity_type="accommodation",
            entity_id=str(accommodation_request.id),
        ).exists()

    def test_accommodation_reject_fallback_writes_audit_log(
        self, api_client, make_approver
    ):
        from accommodation.models import AccommodationRequest
        from accounts.models import AdminActionLog

        approver = make_approver(
            "approve_accommodation", "accommodation-audit-rejecter@example.com"
        )
        accommodation_request = AccommodationRequest.objects.create(
            requestor_name="Someone",
            status="Pending",
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/accommodation/requests/{accommodation_request.id}/reject/",
            {"comments": "not needed"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_rejected",
            entity_type="accommodation",
            entity_id=str(accommodation_request.id),
        ).exists()

    def test_combined_request_approve_fallback_writes_audit_log(
        self, api_client, make_approver
    ):
        from accounts.models import AdminActionLog
        from combined_request.models import CombinedRequest

        approver = make_approver(
            "approve_combined", "combined-audit-approver@example.com"
        )
        combined_request = CombinedRequest.objects.create(
            requestor_name="Someone",
            travel_type="Domestic",
            status="Pending",
            requestor=approver,
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/combined/combined-requests/{combined_request.id}/approve/",
            {"step_role": "", "comments": ""},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_approved",
            entity_type="combinedrequest",
            entity_id=str(combined_request.id),
        ).exists()

    def test_combined_request_reject_fallback_writes_audit_log(
        self, api_client, make_approver
    ):
        from accounts.models import AdminActionLog
        from combined_request.models import CombinedRequest

        approver = make_approver(
            "approve_combined", "combined-audit-rejecter@example.com"
        )
        combined_request = CombinedRequest.objects.create(
            requestor_name="Someone",
            travel_type="Domestic",
            status="Pending",
            requestor=approver,
        )
        api_client.force_authenticate(user=approver)

        response = api_client.post(
            f"/api/combined/combined-requests/{combined_request.id}/reject/",
            {"step_role": "", "comments": "not viable"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert AdminActionLog.objects.filter(
            action_type="workflow_step_rejected",
            entity_type="combinedrequest",
            entity_id=str(combined_request.id),
        ).exists()
