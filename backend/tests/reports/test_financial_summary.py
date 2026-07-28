"""
Regression test for Fix 19 (docs/APP_WIDE_GAPS_FIX_ROADMAP.md): financial_summary
crashed with an AttributeError whenever any AccommodationRequest row existed in
the query range - it iterated acc.check_in_date/check_out_date, fields that
don't exist anywhere on the model. Per the real business rule (accommodation
is company-provided, not billed per booking), the fix removes the
accommodation cost estimate entirely rather than inventing one.
"""

import pytest
from accommodation.models import AccommodationRequest
from accounts.models import Permission, Role, RolePermission
from rest_framework import status


@pytest.fixture
def report_viewer(db):
    from accounts.models import User

    permission, _ = Permission.objects.get_or_create(
        name="generate_admin_reports",
        defaults={
            "description": "Can generate comprehensive admin reports and analytics."
        },
    )
    role = Role.objects.create(name="Financial Report Viewer")
    RolePermission.objects.create(role=role, permission=permission)
    return User.objects.create_user(
        email="financial-report-viewer@example.com",
        password="testpass123",
        name="Financial Report Viewer",
        role=role,
    )


@pytest.mark.django_db
class TestFinancialSummaryReports:
    def test_does_not_crash_with_accommodation_requests_in_range(
        self, api_client, report_viewer, regular_user
    ):
        AccommodationRequest.objects.create(
            requestor_name=regular_user.name,
            status="Pending",
        )

        api_client.force_authenticate(user=report_viewer)
        response = api_client.get("/api/reports/financial/")

        assert response.status_code == status.HTTP_200_OK

    def test_breakdown_has_no_accommodation_cost_line(self, api_client, report_viewer):
        api_client.force_authenticate(user=report_viewer)
        response = api_client.get("/api/reports/financial/")

        assert response.status_code == status.HTTP_200_OK
        breakdown = response.json()["data"]["summary"]["breakdown"]
        assert "accommodation" not in breakdown
        assert set(breakdown.keys()) == {"flights", "transport", "visa"}
