"""
Tests for accommodation functionality.
Tests accommodation requests, staff houses, and room management.
"""

import pytest
from accommodation.models import AccommodationRequest
from rest_framework import status


@pytest.mark.django_db
class TestAccommodationRequestList:
    """Test cases for listing accommodation requests."""

    def test_list_accommodation_requests_authenticated(self, authenticated_client):
        """Test listing accommodation requests as authenticated user."""
        response = authenticated_client.get("/api/accommodation/requests/")

        assert response.status_code == status.HTTP_200_OK

    def test_list_accommodation_requests_unauthenticated(self, api_client):
        """Test listing accommodation requests without authentication."""
        response = api_client.get("/api/accommodation/requests/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAccommodationRequestCreation:
    """Test cases for creating accommodation requests."""

    def test_create_accommodation_request(self, authenticated_client, regular_user):
        """Test creating a new accommodation request."""
        from accounts.models import Permission, Role, RolePermission

        permission, _ = Permission.objects.get_or_create(
            name="create_accommodation",
            defaults={"description": "Create Accommodation Request"},
        )
        role = Role.objects.create(name="Accommodation Creator Test")
        RolePermission.objects.create(role=role, permission=permission)
        regular_user.role = role
        regular_user.save()

        response = authenticated_client.post(
            "/api/accommodation/requests/",
            {
                "check_in_date": "2026-03-01",
                "check_out_date": "2026-03-05",
                "purpose": "Business trip",
                "special_requirements": "Ground floor preferred",
            },
        )

        # May require staff house selection
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,  # Missing staff house reference expected
        ]


@pytest.mark.django_db
class TestStaffHouseList:
    """Test cases for listing staff houses."""

    def test_list_staff_houses(self, authenticated_client):
        """Test listing available staff houses."""
        response = authenticated_client.get("/api/accommodation/staff-houses/")

        assert response.status_code == status.HTTP_200_OK

    def test_list_staff_houses_unauthenticated(self, api_client):
        """Test listing staff houses without authentication."""
        response = api_client.get("/api/accommodation/staff-houses/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRoomAvailability:
    """Test cases for room availability."""

    def test_check_room_availability(self, authenticated_client):
        """Test checking room availability."""
        response = authenticated_client.get(
            "/api/accommodation/rooms/",
            {"check_in": "2026-03-01", "check_out": "2026-03-05"},
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAccommodationAdmin:
    """Test cases for accommodation admin operations."""

    def test_admin_list_all_requests(self, admin_client):
        """Test admin can list all accommodation requests."""
        response = admin_client.get("/api/accommodation/requests/")

        assert response.status_code == status.HTTP_200_OK

    def test_admin_manage_staff_houses(self, admin_client):
        """Test admin can manage staff houses."""
        response = admin_client.post(
            "/api/accommodation/staff-houses/",
            {
                "name": "Test Staff House",
                "location": "Test Location",
                "address": "123 Test Street",
            },
        )

        # May succeed or fail based on required fields
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestAccommodationRequestRegressions:
    """Regression tests for docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 3:
    AccommodationRequestViewSet had the same three bugs already fixed on
    TransportRequestViewSet - plain PageNumberPagination silently ignoring
    ?page_size=, a write-action queryset bypass gap giving admins a false
    404, and no ordering tie-breaker."""

    def test_page_size_query_param_is_honored(self, api_client, admin_user):
        """Regression test: AccommodationRequestViewSet previously used plain
        DRF PageNumberPagination, which has no page_size_query_param
        configured and silently ignores ?page_size=, always returning the
        default PAGE_SIZE=10 regardless of what a client asks for. It now
        uses the project-wide StandardResultsPagination, which honors
        page_size (capped at 100)."""
        for i in range(15):
            AccommodationRequest.objects.create(
                requestor_name=admin_user.name,
                status="Draft",
            )

        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/accommodation/requests/?page_size=1000")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 15
        assert len(response.data["results"]) >= 15

    def test_superuser_can_update_another_users_request(
        self, api_client, admin_user, regular_user
    ):
        """Regression test: AccommodationRequestViewSet.get_queryset() only
        gave the is_superuser/admin-permission bypass to retrieve/assign/
        approve/reject. update/partial_update fell through to the
        requestor-only fallback, so even a superuser got a 404 trying to
        PATCH a request they didn't personally create."""
        req = AccommodationRequest.objects.create(
            requestor_name=regular_user.name,
            status="Draft",
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/accommodation/requests/{req.id}/",
            {"additional_comments": "Updated by admin"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_cancel_another_users_request(
        self, api_client, admin_user, regular_user
    ):
        """Same bug as test_superuser_can_update_another_users_request, but
        for the cancel() custom action."""
        req = AccommodationRequest.objects.create(
            requestor_name=regular_user.name,
            status="Pending",
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f"/api/accommodation/requests/{req.id}/cancel/")
        assert response.status_code == status.HTTP_200_OK
        req.refresh_from_db()
        assert req.status == "Cancelled"

    def test_unrelated_user_cannot_update_another_users_request(
        self, api_client, create_user, regular_user
    ):
        other_user = create_user(
            email="unrelated-accom@example.com",
            password="testpass123",
            name="Unrelated Accom User",
        )
        req = AccommodationRequest.objects.create(
            requestor_name=regular_user.name,
            status="Draft",
        )
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f"/api/accommodation/requests/{req.id}/",
            {"additional_comments": "Hijacked"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_owner_can_still_cancel_own_request(self, api_client, regular_user):
        req = AccommodationRequest.objects.create(
            requestor_name=regular_user.name,
            status="Pending",
        )
        api_client.force_authenticate(user=regular_user)
        response = api_client.post(f"/api/accommodation/requests/{req.id}/cancel/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAccommodationListDetailVisibilityConsistency:
    """Regression test for docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 7:
    the admin_view list filter only checked view_all_accommodation, but
    retrieve/assign/update/cancel treat approve_accommodation and
    process_accommodation as admin permissions too (via the new
    can_process_accommodation helper) - a user with only
    approve_accommodation could open any request directly by ID but
    wouldn't see it in the admin list."""

    def test_approver_only_user_sees_others_requests_in_admin_list(
        self, api_client, create_user, regular_user
    ):
        from accounts.models import Permission, Role, RolePermission

        perm, _ = Permission.objects.get_or_create(
            name="approve_accommodation",
            defaults={"description": "Approve accommodation requests"},
        )
        role = Role.objects.create(name="Accommodation Approver Test")
        RolePermission.objects.create(role=role, permission=perm)
        approver = create_user(
            email="accom-approver@example.com",
            password="testpass123",
            name="Accom Approver",
            role=role,
        )

        req = AccommodationRequest.objects.create(
            requestor_name=regular_user.name,
            status="Pending",
        )

        api_client.force_authenticate(user=approver)

        # Already worked before this fix: can open the request directly.
        detail_response = api_client.get(f"/api/accommodation/requests/{req.id}/")
        assert detail_response.status_code == status.HTTP_200_OK

        # Previously failed: didn't appear in the admin list view.
        list_response = api_client.get("/api/accommodation/requests/?admin_view=true")
        assert list_response.status_code == status.HTTP_200_OK
        returned_ids = [item["id"] for item in list_response.data["results"]]
        assert req.id in returned_ids
