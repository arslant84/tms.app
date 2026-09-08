"""
Tests for trf/services.py's start_trf_workflow - the workflow-start logic
extracted from TravelRequestViewSet (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 9). Only two call sites existed
here (perform_create, submit - TravelRequestViewSet has no perform_update
override, unlike accommodation/transport/visa), both already exercised at
the API level via tests/trf/test_travel_requests.py and
tests/workflows/test_legacy_fallback_authorization.py - this adds direct,
mocked unit coverage of the shared function itself, same pattern as
tests/transport/test_services.py and tests/visa/test_services.py.
"""

from unittest.mock import MagicMock, patch

import pytest
from trf.services import start_trf_workflow


@pytest.mark.django_db
class TestStartTrfWorkflow:
    def test_starts_workflow_and_refreshes_on_success(self):
        trf = MagicMock(id=1, status="Pending", workflow_entity_type="travelrequest")
        workflow_instance = MagicMock(id=99)
        with patch("workflows.router.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = workflow_instance
            result = start_trf_workflow(trf, {}, MagicMock())

        assert result is workflow_instance
        trf.refresh_from_db.assert_called_once()
        call_kwargs = mock_router.start_workflow_for_request.call_args.kwargs
        assert call_kwargs["entity"] is trf
        assert call_kwargs["entity_type"] == "travelrequest"
        assert call_kwargs["fallback_entity_type"] == "travelrequest"

    def test_parses_selected_approvers_and_skipped_steps_to_int_keys(self):
        trf = MagicMock(id=1, status="Pending", workflow_entity_type="travelrequest")
        request_data = {
            "selected_approvers": {"5": "user-a"},
            "skipped_steps": {"7": True},
        }
        with patch("workflows.router.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = None
            start_trf_workflow(trf, request_data, MagicMock())

        call_kwargs = mock_router.start_workflow_for_request.call_args.kwargs
        assert call_kwargs["selected_approvers"] == {5: "user-a"}
        assert call_kwargs["skipped_steps"] == {7: True}

    def test_no_refresh_when_no_workflow_instance_returned(self):
        trf = MagicMock(id=1, status="Pending", workflow_entity_type="travelrequest")
        with patch("workflows.router.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = None
            result = start_trf_workflow(trf, {}, MagicMock())

        assert result is None
        trf.refresh_from_db.assert_not_called()
