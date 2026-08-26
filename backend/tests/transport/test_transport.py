"""
Tests for transport request functionality.
Tests transport request CRUD operations and workflow.
"""

import pytest
from rest_framework import status


@pytest.fixture
def transport_creator_client(db, api_client, create_user):
    """Authenticated client whose user holds the create_transport permission."""
    from accounts.models import Permission, Role, RolePermission

    perm, _ = Permission.objects.get_or_create(
        name="create_transport", defaults={"description": "Create transport request"}
    )
    role = Role.objects.create(name="Transport Creator Test")
    RolePermission.objects.create(role=role, permission=perm)
    user = create_user(
        email="transport-creator@example.com",
        password="testpass123",
        name="Transport Creator",
        role=role,
    )
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestTransportRequestList:
    """Test cases for listing transport requests."""

    def test_list_transport_requests_authenticated(self, authenticated_client):
        """Test listing transport requests as authenticated user."""
        response = authenticated_client.get("/api/transport/requests/")

        assert response.status_code == status.HTTP_200_OK

    def test_list_transport_requests_unauthenticated(self, api_client):
        """Test listing transport requests without authentication."""
        response = api_client.get("/api/transport/requests/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_page_size_query_param_is_honored(
        self, api_client, admin_user, transport_creator_client
    ):
        """Regression test: TransportRequestViewSet previously used plain
        DRF PageNumberPagination, which has no page_size_query_param
        configured and silently ignores ?page_size=, always returning the
        default PAGE_SIZE=10 regardless of what a client asks for. Pages
        like the Transport Processing admin dashboard request page_size=1000
        expecting "all requests" and silently only got the first 10,
        hiding most approved requests. It now uses the project-wide
        StandardResultsPagination, which honors page_size (capped at 100)."""
        from transport.models import TransportRequest

        for i in range(15):
            TransportRequest.objects.create(
                requestor=admin_user,
                requestor_name=admin_user.name,
                staff_id="S1",
                department="IT",
                position="Dev",
                purpose=f"Pagination test {i}",
                status="Draft",
                transport_details=[
                    {
                        "date": "2026-09-01",
                        "day": "Tuesday",
                        "from": "A",
                        "to": "B",
                        "departure_time": "09:00",
                        "number_of_passengers": 1,
                    }
                ],
            )

        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/transport/requests/?page_size=1000")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 15
        assert len(response.data["results"]) >= 15


@pytest.mark.django_db
class TestTransportRequestCreation:
    """Test cases for creating transport requests."""

    def test_create_transport_request(self, transport_creator_client):
        """Test creating a new transport request."""
        response = transport_creator_client.post(
            "/api/transport/requests/",
            {
                "requestor_name": "Transport Creator",
                "staff_id": "EMP001",
                "department": "Engineering",
                "position": "Engineer",
                "purpose": "Business travel",
                "transport_details": [
                    {
                        "date": "2026-03-01",
                        "from": "Office",
                        "to": "Airport",
                        "departure_time": "08:00",
                        "number_of_passengers": 1,
                    }
                ],
            },
            format="json",
        )

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_create_transport_request_missing_fields(self, transport_creator_client):
        """Test creating a transport request with missing fields."""
        response = transport_creator_client.post("/api/transport/requests/", {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTransportRequestUpdate:
    """Test cases for updating transport requests."""

    def test_update_transport_request(self, authenticated_client, regular_user):
        """Test updating a transport request."""
        # First create a request
        create_response = authenticated_client.post(
            "/api/transport/requests/",
            {
                "pickup_location": "Office",
                "dropoff_location": "Airport",
                "pickup_date": "2026-03-01",
                "pickup_time": "08:00:00",
                "number_of_passengers": 1,
                "purpose": "Business travel",
            },
        )

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            transport_id = create_response.json().get("data", {}).get(
                "id"
            ) or create_response.json().get("id")
            if transport_id:
                response = authenticated_client.patch(
                    f"/api/transport/requests/{transport_id}/",
                    {"number_of_passengers": 2},
                )
                assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_update_another_users_request(
        self, api_client, admin_user, regular_user
    ):
        """Regression test: TransportRequestViewSet.get_queryset only gave
        the is_superuser/view_all_transport bypass to the retrieve and
        approve/reject actions. update/partial_update fell through to a
        fallback that filtered to requestor=user, so even a superuser got a
        404 trying to PATCH a request they didn't personally create - e.g.
        the Transport Processing admin page's "assign vehicle" /
        booking-details save, which never passes admin_view=true (that
        param only ever existed for the list endpoint)."""
        from transport.models import TransportRequest

        tr = TransportRequest.objects.create(
            requestor=regular_user,
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            position="Dev",
            purpose="Owned by someone else",
            status="Approved",
            transport_details=[
                {
                    "date": "2026-09-01",
                    "day": "Tuesday",
                    "from": "A",
                    "to": "B",
                    "departure_time": "09:00",
                    "number_of_passengers": 1,
                }
            ],
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/transport/requests/{tr.id}/",
            {"booking_details": {"vehicle_number": "ABC-123"}},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

    def test_superuser_can_complete_another_users_request(
        self, api_client, admin_user, regular_user
    ):
        """Same bug as test_superuser_can_update_another_users_request, but
        for the complete() custom action (used by the Transport Processing
        admin page's "Mark as Completed" button) - it also only checked
        get_queryset()'s personal-view fallback, 404ing for a superuser
        completing a request they didn't create even though complete()'s
        own internal check (transport admin only) would have allowed it."""
        from transport.models import TransportRequest, VehicleAssignment

        tr = TransportRequest.objects.create(
            requestor=regular_user,
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            position="Dev",
            purpose="Owned by someone else",
            status="Approved",
            transport_details=[
                {
                    "date": "2026-09-01",
                    "day": "Tuesday",
                    "from": "A",
                    "to": "B",
                    "departure_time": "09:00",
                    "number_of_passengers": 1,
                }
            ],
        )
        VehicleAssignment.objects.create(
            transport_request=tr,
            vehicle_number="ABC-1",
            driver_name="Driver",
            assigned_by=admin_user,
            status="Assigned",
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f"/api/transport/requests/{tr.id}/complete/", {})

        assert response.status_code == status.HTTP_200_OK
        tr.refresh_from_db()
        assert tr.status == "Completed"


@pytest.mark.django_db
class TestVehicleAssignmentDriverContact:
    """Regression test: VehicleAssignment.driver_contact has no blank=True
    on the model, but the Transport Processing admin page's "Driver
    Contact" input has no required marker (unlike Vehicle Number/Driver
    Name) and always sends '' when left empty - every "process this
    request" attempt without a driver contact 400'd with "This field may
    not be blank." VehicleAssignmentSerializer now explicitly allows blank."""

    def test_vehicle_assignment_accepts_blank_driver_contact(
        self, api_client, admin_user
    ):
        from transport.models import TransportRequest

        tr = TransportRequest.objects.create(
            requestor=admin_user,
            requestor_name=admin_user.name,
            staff_id="S1",
            department="IT",
            position="Dev",
            purpose="Blank driver contact test",
            status="Approved",
            transport_details=[
                {
                    "date": "2026-09-01",
                    "day": "Tuesday",
                    "from": "A",
                    "to": "B",
                    "departure_time": "09:00",
                    "number_of_passengers": 1,
                }
            ],
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/transport/vehicle-assignments/",
            {
                "transport_request": tr.id,
                "vehicle_number": "ABC-1",
                "driver_name": "Driver",
                "driver_contact": "",
                "driver_license": "",
                "vehicle_capacity": 4,
                "status": "Assigned",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestTransportProcessingOneShotComplete:
    """Regression coverage for the simplified Transport Processing flow:
    filling in booking details now completes the request in one action -
    there is no separate "Processing" intermediate stage/status to action
    afterwards (see transport-processing.component.ts's
    handleCompleteProcessing)."""

    def test_assign_vehicle_then_update_then_complete_succeeds_end_to_end(
        self, api_client, admin_user
    ):
        from transport.models import TransportRequest

        tr = TransportRequest.objects.create(
            requestor=admin_user,
            requestor_name=admin_user.name,
            staff_id="S1",
            department="IT",
            position="Dev",
            purpose="One-shot complete flow test",
            status="Approved",
            transport_details=[
                {
                    "date": "2026-09-01",
                    "day": "Tuesday",
                    "from": "A",
                    "to": "B",
                    "departure_time": "09:00",
                    "number_of_passengers": 1,
                }
            ],
        )

        api_client.force_authenticate(user=admin_user)

        assign_response = api_client.post(
            "/api/transport/vehicle-assignments/",
            {
                "transport_request": tr.id,
                "vehicle_number": "XYZ-1",
                "driver_name": "Driver",
                "driver_contact": "",
                "driver_license": "",
                "vehicle_capacity": 4,
                "status": "Assigned",
            },
            format="json",
        )
        assert assign_response.status_code == status.HTTP_201_CREATED

        update_response = api_client.patch(
            f"/api/transport/requests/{tr.id}/",
            {"booking_details": {"vehicle_number": "XYZ-1", "driver_name": "Driver"}},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK

        complete_response = api_client.post(
            f"/api/transport/requests/{tr.id}/complete/", {}
        )
        assert complete_response.status_code == status.HTTP_200_OK
        tr.refresh_from_db()
        assert tr.status == "Completed"
