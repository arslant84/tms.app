"""
Tests for workflow functionality.
Tests workflow templates, instances, and approval flows.
"""
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestWorkflowTemplateList:
    """Test cases for listing workflow templates."""

    def test_list_workflow_templates_as_admin(self, admin_client):
        """Test listing workflow templates as admin."""
        response = admin_client.get('/api/workflows/templates/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_workflow_templates_unauthenticated(self, api_client):
        """Test listing workflow templates without authentication."""
        response = api_client.get('/api/workflows/templates/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWorkflowInstanceList:
    """Test cases for listing workflow instances."""

    def test_list_workflow_instances_authenticated(self, authenticated_client):
        """Test listing workflow instances as authenticated user."""
        response = authenticated_client.get('/api/workflows/instances/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_workflow_instances_unauthenticated(self, api_client):
        """Test listing workflow instances without authentication."""
        response = api_client.get('/api/workflows/instances/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPendingApprovals:
    """Test cases for pending approvals."""

    def test_list_pending_approvals(self, authenticated_client):
        """Test listing pending approvals for current user."""
        response = authenticated_client.get('/api/admin/approvals/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_pending_approvals_unauthenticated(self, api_client):
        """Test listing pending approvals without authentication."""
        response = api_client.get('/api/admin/approvals/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWorkflowApproval:
    """Test cases for workflow approval actions."""

    def test_approve_action_requires_auth(self, api_client):
        """Test that approval actions require authentication."""
        response = api_client.post('/api/workflows/executions/test-id/take_action/', {
            'action': 'approve',
            'comments': 'Approved'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWorkflowTemplateManagement:
    """Test cases for workflow template management."""

    def test_create_workflow_template_as_admin(self, admin_client):
        """Test creating a workflow template as admin."""
        response = admin_client.post('/api/workflows/templates/', {
            'name': 'Test Workflow',
            'description': 'Test workflow template',
            'entity_type': 'travelrequest',
            'is_active': True
        })

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_create_workflow_template_as_regular_user(self, authenticated_client):
        """Test that regular users cannot create workflow templates."""
        response = authenticated_client.post('/api/workflows/templates/', {
            'name': 'Test Workflow',
            'description': 'Test workflow template',
            'entity_type': 'travelrequest',
            'is_active': True
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestNotificationConfigs:
    """Test cases for workflow notification configurations."""

    def test_list_notification_configs(self, admin_client):
        """Test listing notification configs as admin."""
        response = admin_client.get('/api/workflows/notification-configs/')

        assert response.status_code == status.HTTP_200_OK

    def test_notification_config_options(self, admin_client):
        """Test getting notification config options."""
        response = admin_client.get('/api/workflows/notification-configs/options/')

        assert response.status_code == status.HTTP_200_OK
