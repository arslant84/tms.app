"""
Unit tests for accommodation/services.py - the request-number generation
and workflow-start logic extracted from AccommodationRequestViewSet
(see docs/CODEBASE_REFACTOR_ROADMAP.md item 6, Phase 3). No Angular/DRF
request cycle needed - these are the cheapest place to add real
coverage for logic that was previously only reachable through the full
view stack.
"""

from unittest.mock import MagicMock, patch

from accommodation.services import (
    generate_accommodation_request_number,
    generate_accommodation_request_number_with_fallback,
    start_accommodation_workflow,
)


class TestGenerateAccommodationRequestNumber:
    def test_generates_with_location_context(self):
        result = generate_accommodation_request_number({"location": "Ashgabat"})
        assert result is not None
        assert result.startswith("ACCOM-")

    def test_defaults_to_accom_context_when_no_location(self):
        result = generate_accommodation_request_number({})
        assert result is not None
        assert result.startswith("ACCOM-")

    def test_returns_none_for_non_dict_additional_data(self):
        # isinstance(additional_data, dict) is False -> location stays ""
        # -> falls into the "ACCOM" default context, still succeeds
        result = generate_accommodation_request_number(None)
        assert result is not None

    def test_returns_none_on_generation_failure(self):
        with patch(
            "accommodation.services.generate_request_id",
            side_effect=Exception("boom"),
        ):
            result = generate_accommodation_request_number({"location": "Ashgabat"})
        assert result is None


class TestGenerateAccommodationRequestNumberWithFallback:
    def test_generates_with_raw_location_as_context(self):
        request = MagicMock(id=42, additional_data={"location": "Kiyanly"})
        result = generate_accommodation_request_number_with_fallback(request)
        assert result.startswith("ACCOM-")

    def test_defaults_to_accom_when_no_additional_data(self):
        request = MagicMock(id=42, additional_data=None)
        result = generate_accommodation_request_number_with_fallback(request)
        assert result.startswith("ACCOM-")

    def test_falls_back_to_timestamp_format_on_failure(self):
        request = MagicMock(id=42, additional_data={"location": "Ashgabat"})
        with patch(
            "accommodation.services.generate_request_id",
            side_effect=Exception("boom"),
        ):
            result = generate_accommodation_request_number_with_fallback(request)
        assert result.startswith("ACCOM-")
        assert result.endswith("-ACCOM-42")


class TestStartAccommodationWorkflow:
    def test_starts_workflow_and_refreshes_on_success(self):
        accommodation_request = MagicMock(id=1, status="Pending")
        workflow_instance = MagicMock(id=99)
        with patch("accommodation.services.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = workflow_instance
            start_accommodation_workflow(accommodation_request, {}, MagicMock())

        accommodation_request.refresh_from_db.assert_called_once()
        mock_router.start_workflow_for_request.assert_called_once()
        call_kwargs = mock_router.start_workflow_for_request.call_args.kwargs
        assert call_kwargs["entity"] is accommodation_request
        assert call_kwargs["entity_type"] == "accommodation"

    def test_parses_selected_approvers_and_skipped_steps_to_int_keys(self):
        accommodation_request = MagicMock(id=1, status="Pending")
        request_data = {
            "selected_approvers": {"5": "user-a"},
            "skipped_steps": {"7": True},
        }
        with patch("accommodation.services.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = None
            start_accommodation_workflow(
                accommodation_request, request_data, MagicMock()
            )

        call_kwargs = mock_router.start_workflow_for_request.call_args.kwargs
        assert call_kwargs["selected_approvers"] == {5: "user-a"}
        assert call_kwargs["skipped_steps"] == {7: True}

    def test_does_not_raise_when_workflow_router_fails(self):
        accommodation_request = MagicMock(id=1, status="Pending")
        with patch("accommodation.services.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.side_effect = Exception("boom")
            # Should not raise - errors are logged and swallowed
            start_accommodation_workflow(accommodation_request, {}, MagicMock())

    def test_no_refresh_when_no_workflow_instance_returned(self):
        accommodation_request = MagicMock(id=1, status="Pending")
        with patch("accommodation.services.WorkflowRouter") as mock_router:
            mock_router.start_workflow_for_request.return_value = None
            start_accommodation_workflow(accommodation_request, {}, MagicMock())

        accommodation_request.refresh_from_db.assert_not_called()
