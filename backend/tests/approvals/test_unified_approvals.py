"""
Regression coverage for the unified approvals queue (backend/approvals/views.py).

Bug: a TSR-embedded transport request (trf is set) never gets its own
WorkflowInstance - it rides entirely on its linked TSR's approval and stays
at a generic "Pending" status until the TSR resolves (see
WorkflowEngine._cascade_status_to_linked_transport). But
_batch_approvable_ids's superuser bypass returned every "Pending*" entity
as approvable without checking for an active WorkflowInstance, so these
embedded requests showed up in a superuser's Pending Approvals queue
looking actionable. Clicking Approve then always failed with "No pending
approval step found", surfaced to the user as the confusing "This item has
already been processed or is not awaiting your approval."

Fix: the transport query in unified_approvals now excludes TSR-embedded
requests (trf__isnull=True) - they were never independently approvable
regardless of who's asking.
"""

import pytest
from django.contrib.contenttypes.models import ContentType
from transport.models import TransportRequest
from trf.models import TravelRequest
from workflows.models import WorkflowInstance, WorkflowStep, WorkflowTemplate


@pytest.fixture
def transport_workflow(db, admin_user):
    template = WorkflowTemplate.objects.create(
        name="Test Unified-Approvals Transport Workflow",
        entity_type="transportrequest",
        is_active=True,
        created_by=admin_user,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=1,
        step_name="HOD",
        is_required=True,
        can_skip=True,
        approver_user=admin_user,
    )
    return template


@pytest.mark.django_db
class TestUnifiedApprovalsExcludesTsrEmbeddedTransport:
    def test_standalone_transport_request_is_listed(
        self, api_client, admin_user, regular_user, transport_workflow
    ):
        from workflows.router import WorkflowRouter

        tr = TransportRequest.objects.create(
            requestor=regular_user,
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            position="Dev",
            purpose="Standalone request",
            status="Pending",
            transport_details=[
                {
                    "date": "2026-09-01",
                    "day": "Tuesday",
                    "from": "A",
                    "to": "B",
                    "departureTime": "09:00",
                    "numberOfPassengers": 1,
                }
            ],
        )
        WorkflowRouter.start_workflow_for_request(
            entity=tr, entity_type="transportrequest", initiated_by=regular_user
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.get(
            "/api/admin/approvals/?page=1&limit=100&type=transport"
        )

        assert response.status_code == 200
        ids = [item["id"] for item in response.data["data"]]
        assert str(tr.id) in ids

    def test_tsr_embedded_transport_request_is_excluded(
        self, api_client, admin_user, regular_user
    ):
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending Department Focal",
            created_by=regular_user,
        )
        tr = TransportRequest.objects.create(
            requestor=regular_user,
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            position="Dev",
            purpose="TSR-embedded request",
            status="Pending",
            trf=trf,
            transport_details=[
                {
                    "date": "2026-09-01",
                    "day": "Tuesday",
                    "from": "A",
                    "to": "B",
                    "departureTime": "09:00",
                    "numberOfPassengers": 1,
                }
            ],
        )
        # No WorkflowInstance is ever created for this one - matches the
        # real perform_create/submit guard (`if not transport_request.trf_id`)
        # that skips starting a workflow for TSR-embedded requests.
        content_type = ContentType.objects.get_for_model(tr)
        assert not WorkflowInstance.objects.filter(
            content_type=content_type, object_id=tr.id
        ).exists()

        api_client.force_authenticate(user=admin_user)
        response = api_client.get(
            "/api/admin/approvals/?page=1&limit=100&type=transport"
        )

        assert response.status_code == 200
        ids = [item["id"] for item in response.data["data"]]
        assert str(tr.id) not in ids

    def test_approving_tsr_embedded_transport_request_fails_cleanly(
        self, api_client, admin_user, regular_user
    ):
        """Confirms the underlying transport approve() view still 400s for
        one of these (by design - it must be approved via the TSR, not
        directly) even though it's now hidden from the queue, so directly
        hitting the endpoint (e.g. a stale bookmark) fails predictably
        rather than silently succeeding."""
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending Department Focal",
            created_by=regular_user,
        )
        tr = TransportRequest.objects.create(
            requestor=regular_user,
            requestor_name=regular_user.name,
            staff_id="S1",
            department="IT",
            position="Dev",
            purpose="TSR-embedded request",
            status="Pending",
            trf=trf,
            transport_details=[
                {
                    "date": "2026-09-01",
                    "day": "Tuesday",
                    "from": "A",
                    "to": "B",
                    "departureTime": "09:00",
                    "numberOfPassengers": 1,
                }
            ],
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/transport/requests/{tr.id}/approve/",
            {"step_role": "Department Focal", "comments": "test"},
            format="json",
        )

        assert response.status_code == 400
        assert "No pending approval step found" in response.data["error"]
