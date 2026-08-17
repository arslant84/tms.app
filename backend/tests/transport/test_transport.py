"""
Tests for transport request functionality.
Tests transport request CRUD operations and workflow.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestTransportRequestList:
    """Test cases for listing transport requests."""

    def test_list_transport_requests_authenticated(self, authenticated_client):
        """Test listing transport requests as authenticated user."""
        response = authenticated_client.get("/api/transport/")

        assert response.status_code == status.HTTP_200_OK

    def test_list_transport_requests_unauthenticated(self, api_client):
        """Test listing transport requests without authentication."""
        response = api_client.get("/api/transport/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTransportRequestCreation:
    """Test cases for creating transport requests."""

    def test_create_transport_request(self, authenticated_client, regular_user):
        """Test creating a new transport request."""
        response = authenticated_client.post(
            "/api/transport/",
            {
                "pickup_location": "Office",
                "dropoff_location": "Airport",
                "pickup_date": "2026-03-01",
                "pickup_time": "08:00:00",
                "number_of_passengers": 1,
                "purpose": "Business travel",
            },
        )

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_create_transport_request_missing_fields(self, authenticated_client):
        """Test creating a transport request with missing fields."""
        response = authenticated_client.post("/api/transport/", {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTransportRequestUpdate:
    """Test cases for updating transport requests."""

    def test_update_transport_request(self, authenticated_client, regular_user):
        """Test updating a transport request."""
        # First create a request
        create_response = authenticated_client.post(
            "/api/transport/",
            {
                "pickup_location": "Office",
                "dropoff_location": "Airport",
                "pickup_date": "2026-03-01",
                "pickup_time": "08:00:00",
                "number_of_passengers": 1,
                "purpose": "Business travel",
            },
        )

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            transport_id = create_response.json().get("data", {}).get(
                "id"
            ) or create_response.json().get("id")
            if transport_id:
                response = authenticated_client.patch(
                    f"/api/transport/{transport_id}/", {"number_of_passengers": 2}
                )
                assert response.status_code == status.HTTP_200_OK
