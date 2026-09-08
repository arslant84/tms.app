"""
Regression tests for docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 9.

CustomUser.is_admin used to be checked directly in permission.guard.ts,
accounts/settings_views.py's audit-log endpoints, entirely outside the
Role/Permission system - a second, non-RBAC authority channel. Per the
user's explicit direction (2026-09-08), access should be governed solely by
a role's actually-assigned permissions (the same Role Management UI used to
build "System Administrator"), not by a hardcoded is_admin bypass.

Before removing the bypass, "System Administrator" (the role held by every
current is_admin=True user) was granted the 2 permissions it was missing
(view_admin_department_focal, view_department_requests) so no existing user
loses access. These tests prove the new behavior: is_admin alone is no
longer sufficient - the user's actual Role permissions decide.
"""

import pytest
from rest_framework import status


@pytest.fixture
def is_admin_no_permissions_client(db, api_client, create_user):
    """A user with the legacy is_admin=True flag but no role/permissions at
    all - the exact case the old bypass used to let through everywhere."""
    user = create_user(
        email="is-admin-no-perms@example.com",
        password="testpass123",
        name="Is Admin No Perms",
    )
    user.is_admin = True
    user.save(update_fields=["is_admin"])
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def view_activity_logs_client(db, api_client, create_user):
    """A user with the real view_activity_logs permission (via a role) but
    is_admin=False - proves access now flows through RBAC, not the flag."""
    from accounts.models import Permission, Role, RolePermission

    perm, _ = Permission.objects.get_or_create(
        name="view_activity_logs",
        defaults={"description": "View audit/activity logs"},
    )
    role = Role.objects.create(name="Audit Viewer Test")
    RolePermission.objects.create(role=role, permission=perm)
    user = create_user(
        email="audit-viewer@example.com",
        password="testpass123",
        name="Audit Viewer",
        role=role,
    )
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestAuditLogAccessGovernedByRbacOnly:
    def test_is_admin_alone_can_no_longer_see_all_audit_logs(
        self, is_admin_no_permissions_client, regular_user
    ):
        from accounts.models import AdminActionLog

        AdminActionLog.objects.create(user=regular_user, action_type="login_success")

        response = is_admin_no_permissions_client.get("/api/audit-logs/")
        assert response.status_code == status.HTTP_200_OK
        # No permission and not the actor on any log -> sees nothing (own-
        # logs-only fallback, same as any ordinary user), not everything.
        assert response.data["count"] == 0

    def test_is_admin_alone_can_no_longer_see_audit_log_stats(
        self, is_admin_no_permissions_client
    ):
        response = is_admin_no_permissions_client.get("/api/audit-logs/stats/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_role_with_view_activity_logs_permission_sees_all_audit_logs(
        self, view_activity_logs_client, regular_user
    ):
        from accounts.models import AdminActionLog

        AdminActionLog.objects.create(user=regular_user, action_type="login_success")

        response = view_activity_logs_client.get("/api/audit-logs/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_role_with_view_activity_logs_permission_sees_audit_log_stats(
        self, view_activity_logs_client
    ):
        response = view_activity_logs_client.get("/api/audit-logs/stats/")
        assert response.status_code == status.HTTP_200_OK

    def test_system_administrator_role_still_sees_everything(
        self, api_client, create_user
    ):
        """The 5 real users who had is_admin=True all hold this role - this
        proves they lose nothing after the bypass removal, now that the
        role has been granted the 2 permissions it was missing."""
        from accounts.models import AdminActionLog, Role

        sysadmin_role = Role.objects.get(name="System Administrator")
        user = create_user(
            email="sysadmin-check@example.com",
            password="testpass123",
            name="Sysadmin Check",
            role=sysadmin_role,
        )
        other_user = create_user(
            email="sysadmin-check-other@example.com",
            password="testpass123",
            name="Someone Else",
        )
        AdminActionLog.objects.create(user=other_user, action_type="login_success")

        api_client.force_authenticate(user=user)
        list_response = api_client.get("/api/audit-logs/")
        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.data["count"] >= 1

        stats_response = api_client.get("/api/audit-logs/stats/")
        assert stats_response.status_code == status.HTTP_200_OK
