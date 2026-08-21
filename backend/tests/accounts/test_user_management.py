"""
Tests for user management functionality.
Tests user CRUD operations, role assignments, and permissions.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestUserCreation:
    """Test cases for user creation."""

    def test_create_user_as_admin(self, admin_client):
        """Test creating a user as admin."""
        response = admin_client.post('/api/users/', {
            'email': 'newuser@example.com',
            'name': 'New User',
            'password': 'SecurePass123456!',
            'password_confirm': 'SecurePass123456!',
        })

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_create_user_as_regular_user(self, authenticated_client):
        """Test that regular users cannot create users."""
        response = authenticated_client.post('/api/users/', {
            'email': 'anotheruser@example.com',
            'name': 'Another User',
            'password': 'SecurePass123!'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_user_unauthenticated(self, api_client):
        """Test creating a user without authentication."""
        response = api_client.post('/api/users/', {
            'email': 'testuser@example.com',
            'name': 'Test User',
            'password': 'SecurePass123!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserUpdate:
    """Test cases for user updates."""

    def test_update_own_profile(self, authenticated_client, regular_user):
        """Test user can update their own profile."""
        response = authenticated_client.patch(f'/api/users/{regular_user.id}/', {
            'name': 'Updated Name'
        })

        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_update_any_user(self, admin_client, regular_user):
        """Test admin can update any user."""
        response = admin_client.patch(f'/api/users/{regular_user.id}/', {
            'name': 'Admin Updated Name'
        })

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUserDeactivation:
    """Test cases for user deactivation."""

    def test_deactivate_user_as_admin(self, admin_client, regular_user):
        """Test deactivating a user as admin."""
        response = admin_client.patch(f'/api/users/{regular_user.id}/', {
            'is_active': False
        })

        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_cannot_deactivate(self, authenticated_client, create_user):
        """Test regular user cannot deactivate others."""
        other_user = create_user(
            email='other@example.com',
            password='otherpass123',
            name='Other User'
        )

        response = authenticated_client.patch(f'/api/users/{other_user.id}/', {
            'is_active': False
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestRoleManagement:
    """Test cases for role management."""

    def test_list_roles(self, admin_client):
        """Test listing available roles."""
        response = admin_client.get('/api/roles/')

        assert response.status_code == status.HTTP_200_OK

    def test_assign_role_to_user(self, admin_client, regular_user):
        """Test assigning a role to a user."""
        roles_response = admin_client.get('/api/roles/')
        if roles_response.status_code == status.HTTP_200_OK:
            roles = roles_response.json()
            # /api/roles/ returns a plain list, not a paginated dict
            role_list = roles if isinstance(roles, list) else roles.get('results', [])
            if role_list:
                role_id = role_list[0]['id']
                response = admin_client.patch(f'/api/users/{regular_user.id}/', {
                    'role': role_id
                })
                assert response.status_code == status.HTTP_200_OK
