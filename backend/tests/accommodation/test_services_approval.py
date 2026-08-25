"""
Unit tests for accommodation/services.py's Phase 4 extraction:
process_accommodation_approval_action and assign_accommodation (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 6, Phase 4). DB-backed since
these functions query WorkflowInstance/ContentType and create real
AccommodationBooking rows.
"""

from types import SimpleNamespace

import pytest
from accommodation.models import (
    AccommodationBooking,
    AccommodationRequest,
    AccommodationRoom,
    AccommodationStaffHouse,
)
from accommodation.services import (
    assign_accommodation,
    process_accommodation_approval_action,
)


def fake_request(user):
    return SimpleNamespace(user=user, META={})


@pytest.fixture
def accommodation_request(regular_user):
    return AccommodationRequest.objects.create(
        requestor_name=regular_user.name,
        staff_id="S001",
        department="IT",
        status="Pending",
    )


@pytest.mark.django_db
class TestProcessAccommodationApprovalActionLegacyFallback:
    """No active WorkflowInstance exists for these requests, so every
    call exercises the legacy fallback branch."""

    def test_approve_denied_without_permission(
        self, regular_user, accommodation_request
    ):
        result = process_accommodation_approval_action(
            accommodation_request, fake_request(regular_user), "approve", ""
        )
        assert result is not None
        data, http_status = result
        assert http_status == 403
        assert "permission" in data["error"]

    def test_approve_succeeds_for_superuser(self, admin_user, accommodation_request):
        result = process_accommodation_approval_action(
            accommodation_request, fake_request(admin_user), "approve", "looks good"
        )
        data, http_status = result
        assert http_status == 200
        accommodation_request.refresh_from_db()
        assert accommodation_request.status == "Approved"

    def test_approve_rejects_wrong_status(self, admin_user, accommodation_request):
        accommodation_request.status = "Approved"
        accommodation_request.save()
        result = process_accommodation_approval_action(
            accommodation_request, fake_request(admin_user), "approve", ""
        )
        data, http_status = result
        assert http_status == 400
        assert "current status" in data["error"]

    def test_reject_denied_without_permission(
        self, regular_user, accommodation_request
    ):
        result = process_accommodation_approval_action(
            accommodation_request, fake_request(regular_user), "reject", ""
        )
        data, http_status = result
        assert http_status == 403

    def test_reject_succeeds_for_superuser(self, admin_user, accommodation_request):
        result = process_accommodation_approval_action(
            accommodation_request, fake_request(admin_user), "reject", "not needed"
        )
        data, http_status = result
        assert http_status == 200
        accommodation_request.refresh_from_db()
        assert accommodation_request.status == "Rejected"


@pytest.mark.django_db
class TestAssignAccommodation:
    @pytest.fixture
    def staff_house(self):
        return AccommodationStaffHouse.objects.create(
            name="Test House", location="Ashgabat"
        )

    @pytest.fixture
    def room(self, staff_house):
        return AccommodationRoom.objects.create(
            staff_house=staff_house, name="Room 1", capacity=2, status="Available"
        )

    def test_requires_all_fields(self, accommodation_request, admin_user):
        data, http_status = assign_accommodation(
            accommodation_request,
            staff_house_id=None,
            room_id=None,
            start_date_str=None,
            end_date_str=None,
            notes="",
            assigned_room_info="",
            actioned_by=admin_user,
        )
        assert http_status == 400
        assert "required" in data["error"]

    def test_rejects_end_before_start(
        self, accommodation_request, staff_house, room, admin_user
    ):
        data, http_status = assign_accommodation(
            accommodation_request,
            staff_house_id=staff_house.id,
            room_id=room.id,
            start_date_str="2026-01-05",
            end_date_str="2026-01-01",
            notes="",
            assigned_room_info="",
            actioned_by=admin_user,
        )
        assert http_status == 400
        assert "end_date" in data["error"]

    def test_creates_one_booking_per_night(
        self, accommodation_request, staff_house, room, admin_user
    ):
        data, http_status = assign_accommodation(
            accommodation_request,
            staff_house_id=staff_house.id,
            room_id=room.id,
            start_date_str="2026-01-01",
            end_date_str="2026-01-03",
            notes="",
            assigned_room_info="Room 1 (Jan 1-3)",
            actioned_by=admin_user,
        )
        assert http_status == 200
        assert data["bookings_created"] == 3
        accommodation_request.refresh_from_db()
        assert accommodation_request.status == "Accommodation Assigned"
        assert (
            AccommodationBooking.objects.filter(
                accommodation_request=accommodation_request
            ).count()
            == 3
        )

    def test_detects_conflicting_bookings(
        self, accommodation_request, staff_house, room, admin_user
    ):
        AccommodationBooking.objects.create(
            staff_house=staff_house,
            room=room,
            accommodation_request=accommodation_request,
            date="2026-02-02",
            status="Confirmed",
        )
        data, http_status = assign_accommodation(
            accommodation_request,
            staff_house_id=staff_house.id,
            room_id=room.id,
            start_date_str="2026-02-01",
            end_date_str="2026-02-03",
            notes="",
            assigned_room_info="",
            actioned_by=admin_user,
        )
        assert http_status == 409
        assert "2026-02-02" in data["conflicting_dates"]

    def test_unknown_staff_house_returns_404(self, accommodation_request, admin_user):
        data, http_status = assign_accommodation(
            accommodation_request,
            staff_house_id=999999,
            room_id=1,
            start_date_str="2026-01-01",
            end_date_str="2026-01-02",
            notes="",
            assigned_room_info="",
            actioned_by=admin_user,
        )
        assert http_status == 404
