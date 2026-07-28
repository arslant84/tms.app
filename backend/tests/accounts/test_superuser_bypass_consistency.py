"""
Regression tests for the 2026-07-24 superuser-bypass consistency audit.

Triggered by a real bug: notifications.views.CanManageNotifications checked
has_permission(user, 'manage_notifications' or 'view_system_settings') with
no is_superuser bypass at all - unlike every other permission check in this
codebase. Auditing the rest of the app for the same "missing is_superuser
or ..." pattern found the same class of gap in trf/visa/transport/
combined_request's get_queryset() (the retrieve and admin_view can_view_all
checks) and in accommodation/views.py, which used a separate is_admin flag
instead of is_superuser (the same anti-pattern Fix 5 already removed
elsewhere - accounts/utils.py's own docstring says these functions
"replace hardcoded is_staff checks").

All tests here use the admin_client/admin_user fixture (is_superuser=True,
role=None - conftest.py never assigns admin_user a role) specifically
because that's the sharpest version of the bug: a superuser with no role
at all has zero permissions via has_permission()/can_view_all(), so any
check that doesn't special-case is_superuser will incorrectly restrict them.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestNotificationsSuperuserBypass:
    def test_superuser_without_role_can_list_templates(self, admin_client):
        response = admin_client.get("/api/notifications/templates/")
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_without_role_can_list_event_types(self, admin_client):
        response = admin_client.get("/api/notifications/event-types/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTrfSuperuserBypass:
    def test_superuser_without_role_can_retrieve_others_trf(
        self, admin_client, regular_user
    ):
        from trf.models import TravelRequest

        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        response = admin_client.get(f"/api/trf/travel-requests/{trf.id}/")
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_without_role_sees_others_trf_in_admin_view(
        self, admin_client, regular_user
    ):
        from trf.models import TravelRequest

        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        response = admin_client.get("/api/trf/travel-requests/", {"admin_view": "true"})
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        results = body.get("results", body if isinstance(body, list) else [])
        ids = [item["id"] for item in results]
        assert trf.id in ids


@pytest.mark.django_db
class TestVisaSuperuserBypass:
    def test_superuser_without_role_can_retrieve_others_visa(
        self, admin_client, regular_user
    ):
        from visa.models import VisaApplication

        visa = VisaApplication.objects.create(
            requestor_name=regular_user.name,
            destination="Test",
            travel_purpose="Business",
            visa_type="Business",
            status="Pending",
            user=regular_user,
        )
        response = admin_client.get(f"/api/visa/applications/{visa.id}/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTransportSuperuserBypass:
    def test_superuser_without_role_can_retrieve_others_request(
        self, admin_client, regular_user
    ):
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
        response = admin_client.get(f"/api/transport/requests/{transport_request.id}/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCombinedRequestSuperuserBypass:
    def test_superuser_without_role_can_retrieve_others_request(
        self, admin_client, regular_user
    ):
        from combined_request.models import CombinedRequest

        combined_request = CombinedRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            requestor=regular_user,
        )
        response = admin_client.get(
            f"/api/combined/combined-requests/{combined_request.id}/"
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAccommodationSuperuserBypass:
    def test_superuser_without_role_can_retrieve_others_request(
        self, admin_client, regular_user
    ):
        from accommodation.models import AccommodationRequest

        accommodation_request = AccommodationRequest.objects.create(
            requestor_name=regular_user.name,
            status="Pending",
        )
        response = admin_client.get(
            f"/api/accommodation/requests/{accommodation_request.id}/"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_without_role_sees_others_request_in_admin_view(
        self, admin_client, regular_user
    ):
        from accommodation.models import AccommodationRequest

        accommodation_request = AccommodationRequest.objects.create(
            requestor_name=regular_user.name,
            status="Pending",
        )
        response = admin_client.get(
            "/api/accommodation/requests/", {"admin_view": "true"}
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        results = body.get("results", body if isinstance(body, list) else [])
        ids = [item["id"] for item in results]
        assert accommodation_request.id in ids
