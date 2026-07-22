"""
Regression tests for RBAC bypasses found during the permission audit
(2026-07-23): trf/views.py and combined_request/views.py both let any
user with the Django is_staff flag skip real permission checks entirely.
Both were changed to rely solely on the existing permission system
(accounts.utils permissions / is_superuser), matching the project's
documented "no hardcoded is_staff checks" RBAC design.
"""

import pytest
from accounts.models import Permission, Role, RolePermission
from rest_framework import status


@pytest.fixture
def staff_user_without_permission(db):
    """is_staff=True but no role/permissions at all - the exact case that
    used to bypass RBAC via `if user.is_staff`."""
    from accounts.models import User

    return User.objects.create_user(
        email="staff-no-perm@example.com",
        password="testpass123",
        name="Staff No Perm",
        is_staff=True,
    )


@pytest.mark.django_db
class TestTrfBookFlightBypassRemoved:
    def test_staff_without_booking_permission_cannot_see_bookable_trf(
        self, api_client, staff_user_without_permission, regular_user
    ):
        """Previously: `if user.is_staff: return queryset.filter(...)` let
        any is_staff user access the bookable-TRF queryset regardless of
        role/permissions. Now only manage_bookings/view_all_trf-holding
        users (or matching role-name keywords) can."""
        from trf.models import TravelRequest

        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Approved",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=staff_user_without_permission)

        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/admin/book-flight/",
            {
                "pnr": "ABC123",
                "airline": "Test Air",
                "flightNumber": "TA1",
                "departureAirport": "KUL",
                "arrivalAirport": "LHR",
                "departureDateTime": "2026-08-01T10:00:00",
                "arrivalDateTime": "2026-08-01T18:00:00",
            },
        )

        # get_queryset filters the TRF out entirely for this user, so
        # get_object() 404s rather than returning a 403 - either way, the
        # is_staff bypass that used to grant access is gone.
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_manage_bookings_permission_still_grants_access(
        self, api_client, regular_user
    ):
        from accounts.models import User
        from trf.models import TravelRequest

        permission, _ = Permission.objects.get_or_create(
            name="manage_bookings",
            defaults={"description": "Manage Flight and Hotel Bookings"},
        )
        role = Role.objects.create(name="Booking Admin")
        RolePermission.objects.create(role=role, permission=permission)
        booking_admin = User.objects.create_user(
            email="booking-admin@example.com",
            password="testpass123",
            name="Booking Admin",
            role=role,
        )

        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Approved",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=booking_admin)

        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/admin/book-flight/",
            {
                "pnr": "ABC123",
                "airline": "Test Air",
                "flightNumber": "TA1",
                "departureAirport": "KUL",
                "arrivalAirport": "LHR",
                "departureDateTime": "2026-08-01T10:00:00",
                "arrivalDateTime": "2026-08-01T18:00:00",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestCombinedRequestProcessModuleBypassRemoved:
    def test_staff_without_module_permission_is_forbidden(
        self, api_client, staff_user_without_permission
    ):
        """Previously: `if not (request.user.is_admin or request.user.is_staff)`
        skipped the permission check entirely for any is_staff user."""
        from combined_request.models import CombinedRequest

        combined_request = CombinedRequest.objects.create(
            requestor_name=staff_user_without_permission.name,
            travel_type="Domestic",
            status="Approved",
            requestor=staff_user_without_permission,
        )
        api_client.force_authenticate(user=staff_user_without_permission)

        response = api_client.post(
            f"/api/combined/combined-requests/{combined_request.id}/process-module/",
            {"module": "travel", "processing_data": {}},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_module_permission_grants_access(self, api_client):
        from accounts.models import User
        from combined_request.models import CombinedRequest

        permission, _ = Permission.objects.get_or_create(
            name="view_admin_flights",
            defaults={"description": "Can access the Flight Admin module interface"},
        )
        role = Role.objects.create(name="Flight Admin")
        RolePermission.objects.create(role=role, permission=permission)
        flight_admin = User.objects.create_user(
            email="flight-admin@example.com",
            password="testpass123",
            name="Flight Admin",
            role=role,
        )

        combined_request = CombinedRequest.objects.create(
            requestor_name=flight_admin.name,
            travel_type="Domestic",
            status="Approved",
            requestor=flight_admin,
        )
        api_client.force_authenticate(user=flight_admin)

        response = api_client.post(
            f"/api/combined/combined-requests/{combined_request.id}/process-module/",
            {"module": "travel", "processing_data": {}},
            format="json",
        )

        # Permission check passes; whatever happens downstream is not what
        # this test is verifying, but it must not be a 403.
        assert response.status_code != status.HTTP_403_FORBIDDEN
