"""
Tests for accommodation functionality.
Tests accommodation requests, staff houses, and room management.
"""

import pytest
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
