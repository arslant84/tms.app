"""
Regression tests for the 2026-07-23 "paper permissions" audit
(docs/APP_WIDE_GAPS_FIX_ROADMAP.md Fix 9).

Covers:
- create_trf / create_visa / create_transport / create_accommodation /
  create_combined now actually gate the corresponding create endpoints.
- manage_own_profile now gates the self-service profile update endpoint.
- export_data now grants access to ReportExportView alongside
  generate_admin_reports.
- The 5 duplicate permissions (manage_flights, process_flights,
  process_visa_applications, manage_transport_requests,
  manage_accommodation_bookings) were deleted and Ticketing Clerk was
  folded into manage_bookings/process_bookings instead.
- access_debug_endpoints and manage_document_templates were deleted as
  dead permissions with no corresponding feature.
- create_combined is no longer inverted (assigned to the same 10 roles as
  create_trf, not to Registered User).
"""

import pytest
from rest_framework import status


def _grant_permission(user, permission_name, role_name):
    from accounts.models import Permission, Role, RolePermission

    permission, _ = Permission.objects.get_or_create(
        name=permission_name, defaults={"description": permission_name}
    )
    role = Role.objects.create(name=role_name)
    RolePermission.objects.create(role=role, permission=permission)
    user.role = role
    user.save()
    return role


@pytest.mark.django_db
class TestCreatePermissionsEnforced:
    def test_create_trf_forbidden_without_permission(
        self, authenticated_client, regular_user
    ):
        response = authenticated_client.post(
            "/api/trf/travel-requests/",
            {"travel_type": "Domestic"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_trf_allowed_with_permission(
        self, authenticated_client, regular_user
    ):
        _grant_permission(regular_user, "create_trf", "TRF Creator Test")

        response = authenticated_client.post(
            "/api/trf/travel-requests/",
            {"travel_type": "Domestic"},
        )
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_create_visa_forbidden_without_permission(
        self, authenticated_client, regular_user
    ):
        response = authenticated_client.post(
            "/api/visa/applications/",
            {"destination_country": "United States"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_visa_allowed_with_permission(
        self, authenticated_client, regular_user
    ):
        _grant_permission(regular_user, "create_visa", "Visa Creator Test")

        response = authenticated_client.post(
            "/api/visa/applications/",
            {"destination_country": "United States"},
        )
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_create_transport_forbidden_without_permission(
        self, authenticated_client, regular_user
    ):
        response = authenticated_client.post(
            "/api/transport/requests/",
            {"purpose": "Site visit"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_transport_allowed_with_permission(
        self, authenticated_client, regular_user
    ):
        _grant_permission(regular_user, "create_transport", "Transport Creator Test")

        response = authenticated_client.post(
            "/api/transport/requests/",
            {"purpose": "Site visit"},
        )
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_create_accommodation_forbidden_without_permission(
        self, authenticated_client, regular_user
    ):
        response = authenticated_client.post(
            "/api/accommodation/requests/",
            {"purpose": "Business trip"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_combined_forbidden_without_permission(
        self, authenticated_client, regular_user
    ):
        response = authenticated_client.post(
            "/api/combined/combined-requests/",
            {},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_combined_allowed_with_permission(
        self, authenticated_client, regular_user
    ):
        _grant_permission(regular_user, "create_combined", "Combined Creator Test")

        response = authenticated_client.post(
            "/api/combined/combined-requests/",
            {},
        )
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_superuser_bypasses_create_checks(self, admin_client):
        """Superusers must still be able to create TRFs without any
        explicit create_trf permission assignment."""
        response = admin_client.post(
            "/api/trf/travel-requests/",
            {"travel_type": "Domestic"},
        )
        assert response.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestManageOwnProfileEnforced:
    def test_update_profile_forbidden_without_permission(
        self, authenticated_client, regular_user
    ):
        response = authenticated_client.patch(
            "/api/users/update_profile/", {"name": "New Name"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_profile_allowed_with_permission(
        self, authenticated_client, regular_user
    ):
        _grant_permission(regular_user, "manage_own_profile", "Profile Manager Test")

        response = authenticated_client.patch(
            "/api/users/update_profile/", {"name": "New Name"}
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestExportDataEnforced:
    def test_export_forbidden_without_permission(
        self, authenticated_client, regular_user
    ):
        response = authenticated_client.get(
            "/api/reports/export/", {"report_type": "admin"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_export_allowed_with_export_data_permission(
        self, authenticated_client, regular_user
    ):
        """export_data alone (without generate_admin_reports) must now grant
        export access - this is the real capability grant flagged when this
        fix was scoped."""
        _grant_permission(regular_user, "export_data", "Export Data Test")

        response = authenticated_client.get(
            "/api/reports/export/", {"report_type": "admin"}
        )
        assert response.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDuplicatePermissionsConsolidated:
    def test_duplicate_permissions_deleted(self):
        from accounts.models import Permission

        for name in (
            "manage_flights",
            "process_flights",
            "process_visa_applications",
            "manage_transport_requests",
            "manage_accommodation_bookings",
            "access_debug_endpoints",
            "manage_document_templates",
        ):
            assert not Permission.objects.filter(name=name).exists()

    def test_ticketing_clerk_has_booking_permissions(self):
        from accounts.models import Role

        role = Role.objects.get(name="Ticketing Clerk")
        perm_names = set(role.permissions.values_list("name", flat=True))
        assert "manage_bookings" in perm_names
        assert "process_bookings" in perm_names

    def test_create_combined_assigned_to_real_roles_not_registered_user(self):
        from accounts.models import Role

        registered_user_role = Role.objects.get(name="Registered User")
        registered_user_perms = set(
            registered_user_role.permissions.values_list("name", flat=True)
        )
        assert "create_combined" not in registered_user_perms

        employee_role = Role.objects.get(name="Employee")
        employee_perms = set(employee_role.permissions.values_list("name", flat=True))
        assert "create_combined" in employee_perms
