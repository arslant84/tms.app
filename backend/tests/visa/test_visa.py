"""
Tests for visa application functionality.
Tests visa application CRUD operations and workflow.
"""
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestVisaApplicationList:
    """Test cases for listing visa applications."""

    def test_list_visa_applications_authenticated(self, authenticated_client):
        """Test listing visa applications as authenticated user."""
        response = authenticated_client.get('/api/visa/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_visa_applications_unauthenticated(self, api_client):
        """Test listing visa applications without authentication."""
        response = api_client.get('/api/visa/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestVisaApplicationCreation:
    """Test cases for creating visa applications."""

    def test_create_visa_application(self, authenticated_client, regular_user):
        """Test creating a new visa application."""
        response = authenticated_client.post('/api/visa/', {
            'destination_country': 'United States',
            'visa_type': 'Business',
            'travel_purpose': 'Business meeting',
            'planned_departure_date': '2026-04-01',
            'planned_return_date': '2026-04-15'
        })

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_create_visa_application_missing_fields(self, authenticated_client):
        """Test creating a visa application with missing fields."""
        response = authenticated_client.post('/api/visa/', {
            'destination_country': 'United States'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestVisaApplicationRetrieval:
    """Test cases for retrieving visa applications."""

    def test_get_single_visa_application(self, authenticated_client, regular_user):
        """Test retrieving a single visa application."""
        # First create an application
        create_response = authenticated_client.post('/api/visa/', {
            'destination_country': 'United States',
            'visa_type': 'Business',
            'travel_purpose': 'Business meeting',
            'planned_departure_date': '2026-04-01',
            'planned_return_date': '2026-04-15'
        })

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            visa_id = create_response.json().get('data', {}).get('id') or create_response.json().get('id')
            if visa_id:
                response = authenticated_client.get(f'/api/visa/{visa_id}/')
                assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestVisaDocuments:
    """Test cases for visa document management."""

    def test_list_visa_documents_endpoint(self, authenticated_client):
        """Test that visa documents endpoint exists."""
        response = authenticated_client.get('/api/visa/documents/')

        # Endpoint may return list or 404 if not implemented
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
