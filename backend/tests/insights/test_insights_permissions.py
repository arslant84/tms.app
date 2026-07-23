"""
Regression tests for insights' admin-analytics RBAC consistency fix
(2026-07-23, follow-up to the HotelBooking removal audit).

department_analytics and user_activity_report previously required
IsAdminUser (Django is_staff) instead of the granular generate_admin_reports
permission that reports/views.py's equivalent admin endpoints use - a real
divergence, since generate_admin_reports is also granted to HOD, not just
System Administrator/is_staff. These tests assert the two apps are now
consistent. The other four insights endpoints (dashboard_summary,
travel_spend_analytics, travel_pattern_analytics, booking_analytics) are
deliberately NOT covered here - they're personal, self-scoped dashboards
(IsAuthenticated + per-user filtering via can_view_all), a different class
of endpoint that should not get this gate.
"""

import pytest
from accounts.models import Permission, Role, RolePermission
from rest_framework import status


@pytest.fixture
def report_viewer(db):
    """A user whose role has generate_admin_reports but is NOT is_staff."""
    from accounts.models import User

    permission, _ = Permission.objects.get_or_create(
        name="generate_admin_reports",
        defaults={
            "description": "Can generate comprehensive admin reports and analytics."
        },
    )
    role = Role.objects.create(name="Insights Report Viewer")
    RolePermission.objects.create(role=role, permission=permission)
    return User.objects.create_user(
        email="insights-report-viewer@example.com",
        password="testpass123",
        name="Insights Report Viewer",
        role=role,
        is_staff=False,
    )


@pytest.mark.django_db
class TestInsightsAdminAnalyticsPermissionGate:
    @pytest.mark.parametrize(
        "url",
        [
            "/api/insights/analytics/departments/",
            "/api/insights/reports/user-activity/",
        ],
    )
    def test_regular_user_without_permission_is_forbidden(
        self, api_client, regular_user, url
    ):
        api_client.force_authenticate(user=regular_user)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "url",
        [
            "/api/insights/analytics/departments/",
            "/api/insights/reports/user-activity/",
        ],
    )
    def test_user_with_generate_admin_reports_succeeds_without_is_staff(
        self, api_client, report_viewer, url
    ):
        """The key regression: a non-is_staff user with the real RBAC
        permission (e.g. HOD in production) must be able to reach these
        endpoints, matching what they can already do on reports/views.py."""
        api_client.force_authenticate(user=report_viewer)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_superuser_bypasses_permission_check(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/insights/analytics/departments/")

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUserActivityReportNoLongerReferencesHotelBooking:
    def test_user_activity_report_succeeds_with_flight_bookings_only(
        self, api_client, admin_user, regular_user
    ):
        """Regression test: user_activity_report used to compute
        total_bookings as user.flight_bookings.count() + user.hotel_bookings.count().
        hotel_bookings was the reverse relation from the now-deleted
        HotelBooking model (Fix 10) - this endpoint was broken (AttributeError)
        until the dead term was removed."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/insights/reports/user-activity/")

        assert response.status_code == status.HTTP_200_OK
