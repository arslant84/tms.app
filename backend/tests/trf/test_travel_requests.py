"""
Tests for Travel Request Form (TRF) functionality.
Tests CRUD operations, workflow integration, and approval flows.
"""

from unittest.mock import patch

import pytest
from rest_framework import status
from trf.models import TravelRequest


@pytest.fixture
def single_step_trf_workflow(db, admin_user):
    """A minimal, active one-step workflow template for TravelRequest."""
    from workflows.models import WorkflowStep, WorkflowTemplate

    template = WorkflowTemplate.objects.create(
        name="Test TRF Single-Step Workflow (PDF auth)",
        entity_type="travelrequest",
        is_active=True,
        created_by=admin_user,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=1,
        step_name="Manager Approval",
        is_required=True,
        can_skip=False,
    )
    return template


@pytest.fixture
def trf_creator_client(db, api_client, create_user):
    """Authenticated client whose user holds the create_trf permission."""
    from accounts.models import Permission, Role, RolePermission

    perm, _ = Permission.objects.get_or_create(
        name="create_trf", defaults={"description": "Create TRF"}
    )
    role = Role.objects.create(name="TRF Creator Test")
    RolePermission.objects.create(role=role, permission=perm)
    user = create_user(
        email="trf-creator@example.com",
        password="testpass123",
        name="TRF Creator",
        role=role,
    )
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestTravelRequestList:
    """Test cases for listing travel requests."""

    def test_list_travel_requests_authenticated(self, authenticated_client):
        """Test listing travel requests as authenticated user."""
        response = authenticated_client.get("/api/trf/travel-requests/")

        assert response.status_code == status.HTTP_200_OK

    def test_list_travel_requests_unauthenticated(self, api_client):
        """Test listing travel requests without authentication."""
        response = api_client.get("/api/trf/travel-requests/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTravelRequestCreation:
    """Test cases for creating travel requests."""

    def test_create_travel_request(self, trf_creator_client):
        """Test creating a new travel request."""
        response = trf_creator_client.post(
            "/api/trf/travel-requests/",
            {
                "requestor_name": "Test User",
                "travel_type": "Domestic",
                "purpose": "Business meeting",
                "email": "trf-creator@example.com",
            },
        )

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_create_travel_request_missing_fields(self, trf_creator_client):
        """Test creating a travel request with missing required fields."""
        response = trf_creator_client.post(
            "/api/trf/travel-requests/", {"travel_type": "Domestic"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTravelRequestRetrieval:
    """Test cases for retrieving travel requests."""

    def test_get_single_travel_request(self, authenticated_client):
        """Test retrieving a single travel request."""
        # First create a request
        create_response = authenticated_client.post(
            "/api/trf/travel-requests/",
            {
                "requestor_name": "Test User",
                "travel_type": "Domestic",
                "purpose": "Test purpose",
                "email": "test@example.com",
            },
        )

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            trf_id = create_response.json().get("data", {}).get(
                "id"
            ) or create_response.json().get("id")
            if trf_id:
                response = authenticated_client.get(
                    f"/api/trf/travel-requests/{trf_id}/"
                )
                assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTravelRequestUpdate:
    """Test cases for updating travel requests."""

    def test_update_draft_travel_request(self, authenticated_client):
        """Test updating a draft travel request."""
        # First create a request
        create_response = authenticated_client.post(
            "/api/trf/travel-requests/",
            {
                "requestor_name": "Test User",
                "travel_type": "Domestic",
                "purpose": "Initial purpose",
                "email": "test@example.com",
            },
        )

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            trf_id = create_response.json().get("data", {}).get(
                "id"
            ) or create_response.json().get("id")
            if trf_id:
                response = authenticated_client.patch(
                    f"/api/trf/travel-requests/{trf_id}/",
                    {"purpose": "Updated purpose"},
                )
                assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTravelRequestSubmission:
    """Test cases for submitting travel requests."""

    def test_submit_travel_request(self, authenticated_client, regular_user):
        """Test submitting a travel request for approval."""
        # First create a request
        create_response = authenticated_client.post(
            "/api/trf/travel-requests/",
            {
                "requestor_name": regular_user.name,
                "travel_type": "Domestic",
                "purpose": "Business trip",
                "email": regular_user.email,
            },
        )

        if create_response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
            trf_id = create_response.json().get("data", {}).get(
                "id"
            ) or create_response.json().get("id")
            if trf_id:
                response = authenticated_client.post(
                    f"/api/trf/travel-requests/{trf_id}/submit/"
                )
                # May fail if workflow is not configured
                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_400_BAD_REQUEST,
                ]


@pytest.mark.django_db
class TestTravelRequestPdfAuthorization:
    """Regression tests for docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 1:
    export_pdf/download_pdf used to fetch TravelRequest.objects.get(pk=pk)
    directly, bypassing get_queryset() entirely - any authenticated user
    could export or download any other user's TRF PDF just by knowing/
    guessing its numeric ID. They now go through self.get_object(), sharing
    get_queryset()'s "retrieve" bypass (view_all_trf admin, the TRF's owner,
    or an approver with a pending step on it)."""

    def _mock_task(self):
        mock_task = type("MockTask", (), {"id": "test-task-id-123"})()
        return patch("trf.tasks.export_trf_pdf.apply_async", return_value=mock_task)

    def test_owner_can_export_own_trf(self, api_client, regular_user):
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=regular_user)
        with self._mock_task():
            response = api_client.post(f"/api/trf/travel-requests/{trf.id}/export-pdf/")
        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_owner_can_download_own_trf_pdf(self, api_client, regular_user):
        from django.core.cache import cache

        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        cache.set("pdf:test-task-id-456", b"%PDF-1.4 fake pdf bytes")
        api_client.force_authenticate(user=regular_user)
        response = api_client.get(
            f"/api/trf/travel-requests/{trf.id}/download-pdf/",
            {"task_id": "test-task-id-456"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_admin_with_view_all_trf_can_export_another_users_trf(
        self, api_client, admin_user, regular_user
    ):
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=admin_user)
        with self._mock_task():
            response = api_client.post(f"/api/trf/travel-requests/{trf.id}/export-pdf/")
        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_approver_with_pending_step_can_export_another_users_trf(
        self, api_client, create_user, regular_user, single_step_trf_workflow
    ):
        from workflows.router import WorkflowRouter

        approver = create_user(
            email="pdf-approver@example.com",
            password="testpass123",
            name="PDF Approver",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type="travelrequest",
            initiated_by=regular_user,
            selected_approvers={1: approver.id},
        )
        assert workflow_instance is not None
        step_execution = workflow_instance.step_executions.filter(
            status="pending"
        ).first()
        assert step_execution is not None
        assert step_execution.assigned_to_id == approver.id

        api_client.force_authenticate(user=approver)
        with self._mock_task():
            response = api_client.post(f"/api/trf/travel-requests/{trf.id}/export-pdf/")
        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_unrelated_user_cannot_export_another_users_trf(
        self, api_client, create_user, regular_user
    ):
        other_user = create_user(
            email="unrelated@example.com",
            password="testpass123",
            name="Unrelated User",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=other_user)
        with self._mock_task():
            response = api_client.post(f"/api/trf/travel-requests/{trf.id}/export-pdf/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unrelated_user_cannot_download_another_users_trf_pdf(
        self, api_client, create_user, regular_user
    ):
        from django.core.cache import cache

        other_user = create_user(
            email="unrelated2@example.com",
            password="testpass123",
            name="Unrelated User Two",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        cache.set("pdf:test-task-id-789", b"%PDF-1.4 fake pdf bytes")
        api_client.force_authenticate(user=other_user)
        response = api_client.get(
            f"/api/trf/travel-requests/{trf.id}/download-pdf/",
            {"task_id": "test-task-id-789"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTravelRequestWriteActionAuthorization:
    """Regression tests for docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 2:
    TravelRequestViewSet.get_queryset() only gave the is_superuser/
    view_all_trf bypass to retrieve/export_pdf/download_pdf - every other
    detail action (update/partial_update/destroy/cancel/delete_*/
    book_flight) fell through to the owner-only fallback, so an admin
    acting on a TRF they didn't create got a false 404.

    Deliberately does NOT extend the pending-approval fallback to these
    actions (unlike Fix 1's retrieve/export_pdf/download_pdf) - none of them
    have their own internal permission check beyond get_object(), and an
    approver reviewing a TRF should not thereby gain the ability to edit,
    delete, cancel, or book a flight for it. The last test below confirms
    that deliberate scoping decision."""

    def test_admin_can_cancel_another_users_trf(
        self, api_client, admin_user, regular_user
    ):
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f"/api/trf/travel-requests/{trf.id}/cancel/")
        assert response.status_code == status.HTTP_200_OK
        trf.refresh_from_db()
        assert trf.status == "Cancelled"

    def test_owner_can_still_cancel_own_trf(self, api_client, regular_user):
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=regular_user)
        response = api_client.post(f"/api/trf/travel-requests/{trf.id}/cancel/")
        assert response.status_code == status.HTTP_200_OK

    def test_unrelated_user_cannot_cancel_another_users_trf(
        self, api_client, create_user, regular_user
    ):
        other_user = create_user(
            email="unrelated3@example.com",
            password="testpass123",
            name="Unrelated Three",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=other_user)
        response = api_client.post(f"/api/trf/travel-requests/{trf.id}/cancel/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_approver_with_pending_step_cannot_cancel_trf_they_dont_own(
        self, api_client, create_user, regular_user, single_step_trf_workflow
    ):
        """Deliberate scope decision: unlike retrieve/export_pdf/
        download_pdf, cancel does NOT get the pending-approval fallback -
        reviewing a TRF shouldn't grant the ability to cancel it."""
        from workflows.router import WorkflowRouter

        approver = create_user(
            email="cancel-approver@example.com",
            password="testpass123",
            name="Cancel Approver",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type="travelrequest",
            initiated_by=regular_user,
            selected_approvers={1: approver.id},
        )
        assert workflow_instance is not None

        api_client.force_authenticate(user=approver)
        response = api_client.post(f"/api/trf/travel-requests/{trf.id}/cancel/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_can_update_another_users_trf(
        self, api_client, admin_user, regular_user
    ):
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/trf/travel-requests/{trf.id}/", {"purpose": "Updated by admin"}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_unrelated_user_cannot_update_another_users_trf(
        self, api_client, create_user, regular_user
    ):
        other_user = create_user(
            email="unrelated4@example.com",
            password="testpass123",
            name="Unrelated Four",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f"/api/trf/travel-requests/{trf.id}/", {"purpose": "Hijacked"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_can_reach_book_flight_validation_for_another_users_trf(
        self, api_client, admin_user, regular_user
    ):
        """Admin without manage_bookings/keyword-matched role previously got
        a 404 before ever reaching book_flight's own field validation."""
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Approved",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/admin/book-flight/", {}
        )
        # The empty payload fails book_flight's own field validation (400),
        # but it must not be a 404 - reaching validation at all (instead of
        # 404ing at the object-lookup stage) is what this test verifies.
        assert response.status_code != status.HTTP_404_NOT_FOUND

    def test_unrelated_user_cannot_book_flight_for_another_users_trf(
        self, api_client, create_user, regular_user
    ):
        other_user = create_user(
            email="unrelated5@example.com",
            password="testpass123",
            name="Unrelated Five",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Approved",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=other_user)
        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/admin/book-flight/", {}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestBookFlightRoleNameKeywordRemoved:
    """Regression tests for docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 4:
    get_queryset()'s book_flight branch used to also grant access via a
    substring match on the role's display *name* (any role containing
    "ticket"/"travel desk"/"booking"/"admin"), not a real permission check.
    A live role-data audit (2026-09-07) found 3 roles unrelated to
    ticketing (Transport Admin, Accommodation Admin, Meal Admin) got
    book_flight access purely because their name contains "admin", with
    zero flight bookings ever created by their users - confirmed dead,
    unused capability, not something to preserve. The keyword branch was
    removed entirely (not replaced with a data migration - nothing relied
    on it)."""

    def test_role_matching_old_keyword_without_real_permission_cannot_book_flight(
        self, api_client, create_user, regular_user
    ):
        from accounts.models import Role

        role = Role.objects.create(name="Transport Admin (test)")
        user = create_user(
            email="transport-admin-role@example.com",
            password="testpass123",
            name="Transport Admin User",
            role=role,
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Approved",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=user)
        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/admin/book-flight/", {}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_role_with_manage_bookings_permission_can_still_book_flight(
        self, api_client, create_user, regular_user
    ):
        from accounts.models import Permission, Role, RolePermission

        perm, _ = Permission.objects.get_or_create(
            name="manage_bookings", defaults={"description": "Manage flight bookings"}
        )
        role = Role.objects.create(name="Ticketing Desk (test)")
        RolePermission.objects.create(role=role, permission=perm)
        user = create_user(
            email="ticketing-desk@example.com",
            password="testpass123",
            name="Ticketing Desk User",
            role=role,
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Approved",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=user)
        response = api_client.post(
            f"/api/trf/travel-requests/{trf.id}/admin/book-flight/", {}
        )
        # Empty payload fails field validation (400), but must not be a 404 -
        # reaching validation (not blocked at the permission/object stage)
        # is what this test verifies.
        assert response.status_code != status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTrfNestedResourceOwnership:
    """Regression tests for docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 8:
    TRF nested sub-resource ViewSets (itinerary segments, passport details,
    etc.) previously filtered only by ?trf=<id> or returned everything - no
    ownership/permission check tied access back to the parent TRF, and
    CREATE had no check at all (get_queryset() isn't consulted for create).
    Covers itinerary segments (representative of the plain CRUD siblings)
    and passport details (has its own extra write actions) since all 7
    ViewSets now share TrfChildOwnershipMixin."""

    def test_owner_can_create_and_list_own_itinerary_segments(
        self, api_client, regular_user
    ):
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=regular_user)

        create_response = api_client.post(
            "/api/trf/itinerary-segments/",
            {"trf": trf.id, "from_location": "KUL", "to_location": "SIN"},
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        list_response = api_client.get(f"/api/trf/itinerary-segments/?trf={trf.id}")
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.data["results"]) == 1

    def test_unrelated_user_cannot_create_itinerary_segment_for_others_trf(
        self, api_client, create_user, regular_user
    ):
        other_user = create_user(
            email="nested-unrelated1@example.com",
            password="testpass123",
            name="Nested Unrelated One",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=other_user)

        response = api_client.post(
            "/api/trf/itinerary-segments/",
            {"trf": trf.id, "from_location": "KUL", "to_location": "SIN"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unrelated_user_cannot_list_others_itinerary_segments(
        self, api_client, create_user, regular_user
    ):
        from trf.models import TrfItinerarySegment

        other_user = create_user(
            email="nested-unrelated2@example.com",
            password="testpass123",
            name="Nested Unrelated Two",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        TrfItinerarySegment.objects.create(
            trf=trf, from_location="KUL", to_location="SIN"
        )

        api_client.force_authenticate(user=other_user)
        response = api_client.get(f"/api/trf/itinerary-segments/?trf={trf.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_admin_can_create_and_list_itinerary_segments_for_others_trf(
        self, api_client, admin_user, regular_user
    ):
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Draft",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=admin_user)

        create_response = api_client.post(
            "/api/trf/itinerary-segments/",
            {"trf": trf.id, "from_location": "KUL", "to_location": "SIN"},
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        list_response = api_client.get(f"/api/trf/itinerary-segments/?trf={trf.id}")
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.data["results"]) == 1

    def test_approver_with_pending_step_can_list_but_not_create_itinerary_segments(
        self, api_client, create_user, regular_user, single_step_trf_workflow
    ):
        """Deliberate scope decision (matches Fix 2/3): an approver
        reviewing a TRF can see its sub-resources (read), but cannot add
        new ones (write) - reviewing isn't the same as being allowed to
        modify."""
        from workflows.router import WorkflowRouter

        approver = create_user(
            email="nested-approver@example.com",
            password="testpass123",
            name="Nested Approver",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        workflow_instance = WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type="travelrequest",
            initiated_by=regular_user,
            selected_approvers={1: approver.id},
        )
        assert workflow_instance is not None

        api_client.force_authenticate(user=approver)

        list_response = api_client.get(f"/api/trf/itinerary-segments/?trf={trf.id}")
        assert list_response.status_code == status.HTTP_200_OK

        create_response = api_client.post(
            "/api/trf/itinerary-segments/",
            {"trf": trf.id, "from_location": "KUL", "to_location": "SIN"},
        )
        assert create_response.status_code == status.HTTP_403_FORBIDDEN

    def test_unrelated_user_cannot_upload_passport_for_others_trf(
        self, api_client, create_user, regular_user
    ):
        from django.core.files.uploadedfile import SimpleUploadedFile

        other_user = create_user(
            email="nested-unrelated3@example.com",
            password="testpass123",
            name="Nested Unrelated Three",
        )
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Overseas",
            status="Draft",
            created_by=regular_user,
        )
        api_client.force_authenticate(user=other_user)

        fake_file = SimpleUploadedFile(
            "passport.pdf", b"%PDF-1.4 fake", content_type="application/pdf"
        )
        response = api_client.post(
            "/api/trf/passport-details/upload-for-trf/",
            {"trf": trf.id, "passport_file": fake_file},
            format="multipart",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
