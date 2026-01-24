"""
Pytest configuration for TMS integration tests.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

# Use the existing database for tests
pytestmark = pytest.mark.django_db(transaction=True)

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory fixture to create test users."""
    def _create_user(
        email='testuser@example.com',
        password='testpass123',
        name='Test User',
        is_staff=False,
        is_superuser=False,
        **kwargs
    ):
        user = User.objects.create_user(
            email=email,
            password=password,
            name=name,
            is_staff=is_staff,
            is_superuser=is_superuser,
            **kwargs
        )
        return user
    return _create_user


@pytest.fixture
def admin_user(create_user):
    """Create an admin user."""
    return create_user(
        email='admin@example.com',
        password='adminpass123',
        name='Admin User',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def regular_user(create_user):
    """Create a regular user."""
    return create_user(
        email='user@example.com',
        password='userpass123',
        name='Regular User'
    )


@pytest.fixture
def authenticated_client(api_client, regular_user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an admin-authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client
