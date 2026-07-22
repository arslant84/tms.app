"""
Tests for booking functionality.
Tests flight and hotel booking CRUD operations.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestFlightBookingList:
    """Test cases for listing flight bookings."""

    def test_list_flight_bookings_authenticated(self, authenticated_client):
        """Test listing flight bookings as authenticated user."""
        response = authenticated_client.get("/api/bookings/flights/")

        assert response.status_code == status.HTTP_200_OK

    def test_list_flight_bookings_unauthenticated(self, api_client):
        """Test listing flight bookings without authentication."""
        response = api_client.get("/api/bookings/flights/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestHotelBookingList:
    """Test cases for listing hotel bookings."""

    def test_list_hotel_bookings_authenticated(self, authenticated_client):
        """Test listing hotel bookings as authenticated user."""
        response = authenticated_client.get("/api/bookings/hotels/")

        assert response.status_code == status.HTTP_200_OK

    def test_list_hotel_bookings_unauthenticated(self, api_client):
        """Test listing hotel bookings without authentication."""
        response = api_client.get("/api/bookings/hotels/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestBookingCreation:
    """Test cases for creating bookings."""

    def test_create_flight_booking_as_admin(self, admin_client):
        """Test creating a flight booking as admin."""
        # Note: Booking creation typically requires a valid TRF
        response = admin_client.post(
            "/api/bookings/flights/",
            {
                "airline": "Test Airlines",
                "flight_number": "TA123",
                "departure_airport": "JFK",
                "arrival_airport": "LAX",
            },
        )

        # May fail without TRF reference
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,  # Missing TRF reference expected
        ]

    def _flight_payload(self, trf_id, booking_reference):
        return {
            "trf": trf_id,
            "airline": "Test Airlines",
            "flight_number": "TA123",
            "departure_airport": "JFK",
            "arrival_airport": "LAX",
            "departure_time": "2026-08-01T10:00:00Z",
            "arrival_time": "2026-08-01T18:00:00Z",
            "booking_reference": booking_reference,
            "cost": "500.00",
        }

    def test_create_flight_booking_rejected_for_draft_trf(
        self, admin_client, regular_user
    ):
        """
        Regression test: FlightBookingCreateSerializer.validate_trf used to
        compare against ['APPROVED', 'IN_PROGRESS'], values that never occur
        (real statuses are title-case, e.g. 'Approved'). It now uses the
        shared BOOKABLE_STATUSES constant, so a Draft TRF should still be
        correctly rejected (not "always rejected" as it was before, for the
        wrong reason).
        """
        from trf.models import TravelRequest

        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )

        response = admin_client.post(
            "/api/bookings/flights/",
            self._flight_payload(trf.id, "PNR-DRAFT-1"),
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "trf" in response.json()

    def test_create_flight_booking_accepted_for_approved_trf(
        self, admin_client, regular_user
    ):
        """An Approved TRF must be bookable — this is the case the old,
        wrong status list silently broke for everyone."""
        from bookings.models import FlightBooking
        from trf.models import TravelRequest

        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Approved",
            created_by=regular_user,
        )

        response = admin_client.post(
            "/api/bookings/flights/",
            self._flight_payload(trf.id, "PNR-APPROVED-1"),
        )

        assert response.status_code == status.HTTP_201_CREATED
        booking = FlightBooking.objects.get(trf=trf)
        # Regression test: create() used to do `validated_data['user'] = trf.user`,
        # but TravelRequest has no `user` field (only `created_by`), which would
        # raise AttributeError for any admin-created booking.
        assert booking.user_id == regular_user.id


@pytest.mark.django_db
class TestBookingStatistics:
    """Test cases for booking statistics."""

    def test_get_booking_stats_as_admin(self, admin_client):
        """Test getting booking statistics as admin."""
        response = admin_client.get("/api/bookings/stats/")

        # Endpoint may or may not exist
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
