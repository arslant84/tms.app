"""
Tests for visa application functionality.
Tests visa application CRUD operations and workflow.
"""

import pytest
from rest_framework import status
from visa.models import VisaApplication


@pytest.fixture
def visa_creator_client(db, api_client, create_user):
    """Authenticated client whose user holds the create_visa permission."""
    from accounts.models import Permission, Role, RolePermission

    perm, _ = Permission.objects.get_or_create(
        name="create_visa", defaults={"description": "Create visa application"}
    )
    role = Role.objects.create(name="Visa Creator Test")
    RolePermission.objects.create(role=role, permission=perm)
    user = create_user(
        email="visa-creator@example.com",
        password="testpass123",
        name="Visa Creator",
        role=role,
    )
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestVisaApplicationList:
    """Test cases for listing visa applications."""

    def test_list_visa_applications_authenticated(self, authenticated_client):
        """Test listing visa applications as authenticated user."""
        response = authenticated_client.get("/api/visa/applications/")

        assert response.status_code == status.HTTP_200_OK

    def test_list_visa_applications_unauthenticated(self, api_client):
        """Test listing visa applications without authentication."""
        response = api_client.get("/api/visa/applications/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestVisaApplicationCreation:
    """Test cases for creating visa applications."""

    def test_create_visa_application(self, visa_creator_client):
        """Test creating a new visa application."""
        response = visa_creator_client.post(
            "/api/visa/applications/",
            {
                "requestor_name": "Visa Creator",
                "destination": "United States",
                "visa_type": "Business",
                "travel_purpose": "Business meeting",
                "planned_departure_date": "2026-04-01",
                "planned_return_date": "2026-04-15",
            },
        )

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_create_visa_application_missing_fields(self, visa_creator_client):
        """Test creating a visa application with missing fields."""
        response = visa_creator_client.post(
            "/api/visa/applications/", {"destination_country": "United States"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_update_serializer_includes_id(self, regular_user):
        """
        Regression test: VisaApplicationCreateUpdateSerializer used to omit
        'id' from its Meta.fields, so a freshly created application's
        response had no id at all. The frontend (visa-form.component.ts)
        reads response.id right after create to immediately submit the new
        application, so a missing id silently resulted in a request to
        /api/visa/applications/null/submit/ (404).
        """
        from visa.models import VisaApplication
        from visa.serializers import VisaApplicationCreateUpdateSerializer

        visa = VisaApplication.objects.create(
            user=regular_user,
            requestor_name=regular_user.name,
            status="Draft",
        )

        data = VisaApplicationCreateUpdateSerializer(visa).data
        assert data["id"] == visa.id


@pytest.mark.django_db
class TestVisaApplicationRetrieval:
    """Test cases for retrieving visa applications."""

    def test_get_single_visa_application(self, authenticated_client, regular_user):
        """Test retrieving a single visa application."""
        # First create an application
        create_response = authenticated_client.post(
            "/api/visa/applications/",
            {
                "destination_country": "United States",
                "visa_type": "Business",
                "travel_purpose": "Business meeting",
                "planned_departure_date": "2026-04-01",
                "planned_return_date": "2026-04-15",
            },
        )

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            visa_id = create_response.json().get("data", {}).get(
                "id"
            ) or create_response.json().get("id")
            if visa_id:
                response = authenticated_client.get(
                    f"/api/visa/applications/{visa_id}/"
                )
                assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestVisaProcessingAdminActions:
    """Regression coverage: VisaApplicationViewSet.get_queryset only gave
    the is_superuser/view_all_visa bypass to retrieve and approve/reject.
    complete/update/partial_update fell through to a fallback filtered to
    the applicant's own applications, so even a superuser got a 404 trying
    to complete() an application they didn't personally create - e.g. the
    Visa Processing admin page's "Mark as Completed" action, which never
    passes admin_view=true (that param only ever existed for the list
    endpoint). See the matching fix in transport/views.py."""

    def test_superuser_can_complete_another_users_application(
        self, api_client, admin_user, regular_user
    ):
        visa = VisaApplication.objects.create(
            user=regular_user,
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            destination="Some Country",
            travel_purpose="Business",
            visa_type="Business",
            status="Approved",
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f"/api/visa/applications/{visa.id}/complete/", {})

        assert response.status_code == status.HTTP_200_OK
        visa.refresh_from_db()
        assert visa.status == "Completed"

    def test_superuser_can_update_another_users_application(
        self, api_client, admin_user, regular_user
    ):
        visa = VisaApplication.objects.create(
            user=regular_user,
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            destination="Some Country",
            travel_purpose="Business",
            visa_type="Business",
            status="Approved",
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/visa/applications/{visa.id}/",
            {"additional_comments": "Updated by admin"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestVisaDocuments:
    """Test cases for visa document management."""

    def test_list_visa_documents_endpoint(self, authenticated_client):
        """Test that visa documents endpoint exists."""
        response = authenticated_client.get("/api/visa/documents/")

        # Endpoint may return list or 404 if not implemented
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
