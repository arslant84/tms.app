"""
Integration tests for API endpoints.
Tests approvals, reports, and other core API functionality.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestApprovalsEndpoint:
    """Test cases for the unified approvals endpoint."""

    def test_get_approvals_authenticated(self, authenticated_client):
        """Test getting approvals list as authenticated user."""
        response = authenticated_client.get("/api/admin/approvals/")

        assert response.status_code == status.HTTP_200_OK

    def test_get_approvals_unauthenticated(self, api_client):
        """Test getting approvals without authentication."""
        response = api_client.get("/api/admin/approvals/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_approvals_with_pagination(self, authenticated_client):
        """Test approvals endpoint with pagination parameters."""
        response = authenticated_client.get(
            "/api/admin/approvals/", {"page": 1, "limit": 10}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_approvals_filter_by_type(self, authenticated_client):
        """Test filtering approvals by type."""
        response = authenticated_client.get("/api/admin/approvals/", {"type": "trf"})

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestApprovalHistoryEndpoint:
    """Test cases for the approval history endpoint."""

    def test_get_approval_history(self, authenticated_client):
        """Test getting approval history."""
        response = authenticated_client.get("/api/admin/approvals/history/")

        assert response.status_code == status.HTTP_200_OK

    def test_get_approval_history_with_pagination(self, authenticated_client):
        """Test approval history with pagination."""
        response = authenticated_client.get(
            "/api/admin/approvals/history/", {"page": 1, "limit": 20}
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestBulkApprovalEndpoint:
    """Test cases for the bulk approval endpoint."""

    def test_bulk_approve_no_items(self, authenticated_client):
        """Test bulk approve with no items."""
        response = authenticated_client.post(
            "/api/admin/approvals/bulk/",
            {"items": [], "action": "approve"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_approve_invalid_action(self, authenticated_client):
        """Test bulk approve with invalid action."""
        response = authenticated_client.post(
            "/api/admin/approvals/bulk/",
            {"items": [{"id": "1", "type": "trf"}], "action": "invalid_action"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_approve_unauthenticated(self, api_client):
        """Test bulk approve without authentication."""
        response = api_client.post(
            "/api/admin/approvals/bulk/",
            {"items": [{"id": "1", "type": "trf"}], "action": "approve"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestReportsEndpoints:
    """Test cases for the reports endpoints."""

    def test_admin_reports(self, admin_client):
        """Test admin reports endpoint."""
        response = admin_client.get("/api/reports/analytics/")

        assert response.status_code == status.HTTP_200_OK

    def test_departmental_reports(self, admin_client):
        """Test departmental reports endpoint."""
        response = admin_client.get("/api/reports/departmental/")

        assert response.status_code == status.HTTP_200_OK

    def test_user_activity_reports(self, admin_client):
        """Test user activity reports endpoint."""
        response = admin_client.get("/api/reports/user-activity/")

        assert response.status_code == status.HTTP_200_OK

    def test_reports_unauthenticated(self, api_client):
        """Test reports without authentication."""
        response = api_client.get("/api/reports/analytics/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAPIDocumentation:
    """Test cases for API documentation endpoints."""

    def test_schema_endpoint(self, api_client):
        """Test OpenAPI schema endpoint."""
        response = api_client.get("/api/schema/")

        assert response.status_code == status.HTTP_200_OK

    def test_swagger_ui(self, api_client):
        """Test Swagger UI endpoint."""
        response = api_client.get("/api/docs/")

        assert response.status_code == status.HTTP_200_OK

    def test_redoc_ui(self, api_client):
        """Test ReDoc UI endpoint."""
        response = api_client.get("/api/redoc/")

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestNotificationsEndpoint:
    """Test cases for the notifications endpoint."""

    def test_get_notifications(self, authenticated_client):
        """Test getting notifications list."""
        response = authenticated_client.get("/api/notifications/")

        assert response.status_code == status.HTTP_200_OK

    def test_get_notification_stats(self, authenticated_client):
        """Test getting notification statistics."""
        response = authenticated_client.get("/api/notifications/stats/")

        assert response.status_code == status.HTTP_200_OK

    def test_notifications_unauthenticated(self, api_client):
        """Test notifications without authentication."""
        response = api_client.get("/api/notifications/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestInsightsEndpoint:
    """Test cases for the insights/dashboard endpoints."""

    def test_dashboard_summary(self, authenticated_client):
        """Test dashboard summary endpoint."""
        response = authenticated_client.get("/api/insights/dashboard/summary/")

        assert response.status_code == status.HTTP_200_OK

    def test_dashboard_unauthenticated(self, api_client):
        """Test dashboard without authentication."""
        response = api_client.get("/api/insights/dashboard/summary/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSecurityEndpoints:
    """Test cases for security-related endpoints."""

    def test_security_txt(self, api_client):
        """Test security.txt endpoint."""
        response = api_client.get("/.well-known/security.txt")

        assert response.status_code == status.HTTP_200_OK
        assert b"Contact:" in response.content
