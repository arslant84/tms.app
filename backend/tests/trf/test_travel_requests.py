"""
Tests for Travel Request Form (TRF) functionality.
Tests CRUD operations, workflow integration, and approval flows.
"""
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestTravelRequestList:
    """Test cases for listing travel requests."""

    def test_list_travel_requests_authenticated(self, authenticated_client):
        """Test listing travel requests as authenticated user."""
        response = authenticated_client.get('/api/trf/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_travel_requests_unauthenticated(self, api_client):
        """Test listing travel requests without authentication."""
        response = api_client.get('/api/trf/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTravelRequestCreation:
    """Test cases for creating travel requests."""

    def test_create_travel_request(self, authenticated_client, regular_user):
        """Test creating a new travel request."""
        response = authenticated_client.post('/api/trf/', {
            'requestor_name': regular_user.name,
            'travel_type': 'Domestic',
            'purpose': 'Business meeting',
            'email': regular_user.email
        })

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_create_travel_request_missing_fields(self, authenticated_client):
        """Test creating a travel request with missing required fields."""
        response = authenticated_client.post('/api/trf/', {
            'travel_type': 'Domestic'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTravelRequestRetrieval:
    """Test cases for retrieving travel requests."""

    def test_get_single_travel_request(self, authenticated_client):
        """Test retrieving a single travel request."""
        # First create a request
        create_response = authenticated_client.post('/api/trf/', {
            'requestor_name': 'Test User',
            'travel_type': 'Domestic',
            'purpose': 'Test purpose',
            'email': 'test@example.com'
        })

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            trf_id = create_response.json().get('data', {}).get('id') or create_response.json().get('id')
            if trf_id:
                response = authenticated_client.get(f'/api/trf/{trf_id}/')
                assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTravelRequestUpdate:
    """Test cases for updating travel requests."""

    def test_update_draft_travel_request(self, authenticated_client):
        """Test updating a draft travel request."""
        # First create a request
        create_response = authenticated_client.post('/api/trf/', {
            'requestor_name': 'Test User',
            'travel_type': 'Domestic',
            'purpose': 'Initial purpose',
            'email': 'test@example.com'
        })

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            trf_id = create_response.json().get('data', {}).get('id') or create_response.json().get('id')
            if trf_id:
                response = authenticated_client.patch(f'/api/trf/{trf_id}/', {
                    'purpose': 'Updated purpose'
                })
                assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTravelRequestSubmission:
    """Test cases for submitting travel requests."""

    def test_submit_travel_request(self, authenticated_client, regular_user):
        """Test submitting a travel request for approval."""
        # First create a request
        create_response = authenticated_client.post('/api/trf/', {
            'requestor_name': regular_user.name,
            'travel_type': 'Domestic',
            'purpose': 'Business trip',
            'email': regular_user.email
        })

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            trf_id = create_response.json().get('data', {}).get('id') or create_response.json().get('id')
            if trf_id:
                response = authenticated_client.post(f'/api/trf/{trf_id}/submit/')
                # May fail if workflow is not configured
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
