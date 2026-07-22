"""
Regression tests for the reports app permission audit (2026-07-23).

reports/views.py previously only required IsAuthenticated for all five
endpoints, despite a 'generate_admin_reports' permission existing
specifically for this purpose. Any authenticated user could hit every
reports endpoint. These tests assert the new gate.
"""

import pytest
from accounts.models import Permission, Role, RolePermission
from rest_framework import status


@pytest.fixture
def report_viewer(db):
    """A user whose role has the generate_admin_reports permission."""
    from accounts.models import User

    permission, _ = Permission.objects.get_or_create(
        name="generate_admin_reports",
        defaults={
            "description": "Can generate comprehensive admin reports and analytics."
        },
    )
    role = Role.objects.create(name="Report Viewer")
    RolePermission.objects.create(role=role, permission=permission)
    return User.objects.create_user(
        email="report-viewer@example.com",
        password="testpass123",
        name="Report Viewer",
        role=role,
    )


@pytest.mark.django_db
class TestReportsPermissionGate:
    @pytest.mark.parametrize(
        "url",
        [
            "/api/reports/analytics/",
            "/api/reports/departmental/",
            "/api/reports/user-activity/",
            "/api/reports/financial/",
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
            "/api/reports/analytics/",
            "/api/reports/departmental/",
            "/api/reports/user-activity/",
        ],
    )
    def test_user_with_permission_succeeds(self, api_client, report_viewer, url):
        api_client.force_authenticate(user=report_viewer)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_superuser_bypasses_permission_check(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/reports/analytics/")

        assert response.status_code == status.HTTP_200_OK
