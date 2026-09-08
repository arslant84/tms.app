"""
Tests for trf/flight_booking.py - the book_flight helper functions
extracted from TravelRequestViewSet (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 9). book_flight itself only had
validation-failure-path coverage before this (empty-payload 400s in
tests/trf/test_travel_requests.py) - these functions' actual parsing/
building logic had zero test coverage at any level.
"""

from datetime import datetime

import pytest
from trf.flight_booking import (
    parse_flight_datetime,
    parse_flight_segments,
    validate_book_flight_fields,
)


class TestParseFlightDatetime:
    def test_returns_none_for_falsy_value(self):
        assert parse_flight_datetime(None) is None
        assert parse_flight_datetime("") is None

    def test_parses_iso_string_with_z_suffix(self):
        result = parse_flight_datetime("2026-12-01T10:00:00Z")
        assert result is not None
        assert result.year == 2026
        assert result.tzinfo is not None

    def test_parses_naive_iso_string_and_makes_aware(self):
        result = parse_flight_datetime("2026-12-01T10:00:00")
        assert result is not None
        assert result.tzinfo is not None


class TestParseFlightSegments:
    def test_raises_on_invalid_json(self):
        with pytest.raises(ValueError, match="valid JSON"):
            parse_flight_segments("{not json")

    def test_raises_on_empty_segments(self):
        with pytest.raises(ValueError, match="At least one outbound"):
            parse_flight_segments("[]")

    def test_raises_on_missing_required_field(self):
        import json

        segments = json.dumps(
            [
                {
                    "direction": "OUTBOUND",
                    "flightNumber": "MH123",
                    "departureAirport": "KUL",
                    # arrivalAirport missing
                    "departureDateTime": "2026-12-01T10:00:00",
                    "arrivalDateTime": "2026-12-01T18:00:00",
                }
            ]
        )
        with pytest.raises(ValueError, match="missing"):
            parse_flight_segments(segments)

    def test_raises_on_invalid_direction(self):
        import json

        segments = json.dumps(
            [
                {
                    "direction": "SIDEWAYS",
                    "flightNumber": "MH123",
                    "departureAirport": "KUL",
                    "arrivalAirport": "LHR",
                    "departureDateTime": "2026-12-01T10:00:00",
                    "arrivalDateTime": "2026-12-01T18:00:00",
                }
            ]
        )
        with pytest.raises(ValueError, match="invalid direction"):
            parse_flight_segments(segments)

    def test_parses_outbound_and_return_legs(self):
        import json

        segments = json.dumps(
            [
                {
                    "direction": "OUTBOUND",
                    "flightNumber": "MH123",
                    "departureAirport": "KUL",
                    "arrivalAirport": "LHR",
                    "departureDateTime": "2026-12-01T10:00:00",
                    "arrivalDateTime": "2026-12-01T18:00:00",
                },
                {
                    "direction": "RETURN",
                    "flightNumber": "MH124",
                    "departureAirport": "LHR",
                    "arrivalAirport": "KUL",
                    "departureDateTime": "2026-12-10T10:00:00",
                    "arrivalDateTime": "2026-12-11T06:00:00",
                },
            ]
        )
        outbound, return_legs = parse_flight_segments(segments)
        assert len(outbound) == 1
        assert len(return_legs) == 1
        assert outbound[0]["flight_number"] == "MH123"
        assert return_legs[0]["flight_number"] == "MH124"

    def test_raises_when_only_return_legs_given(self):
        import json

        segments = json.dumps(
            [
                {
                    "direction": "RETURN",
                    "flightNumber": "MH124",
                    "departureAirport": "LHR",
                    "arrivalAirport": "KUL",
                    "departureDateTime": "2026-12-10T10:00:00",
                    "arrivalDateTime": "2026-12-11T06:00:00",
                }
            ]
        )
        with pytest.raises(ValueError, match="At least one outbound"):
            parse_flight_segments(segments)


class TestValidateBookFlightFields:
    def test_missing_pnr_and_eticket(self):
        trf = type("Trf", (), {"travel_type": "Domestic"})()
        missing = validate_book_flight_fields(trf, "", "", None, None)
        assert "pnr" in missing
        assert "eTicket" in missing
        assert "airline" not in missing

    def test_overseas_requires_airline(self):
        trf = type("Trf", (), {"travel_type": "Overseas"})()
        missing = validate_book_flight_fields(trf, "PNR1", "", None, None)
        assert "airline" in missing

    def test_no_eticket_required_if_existing_booking_has_one(self):
        trf = type("Trf", (), {"travel_type": "Domestic"})()
        existing_booking = type("Booking", (), {"e_ticket": "some-file.pdf"})()
        missing = validate_book_flight_fields(trf, "PNR1", "", None, existing_booking)
        assert "eTicket" not in missing

    def test_all_fields_present_returns_empty(self):
        trf = type("Trf", (), {"travel_type": "Domestic"})()
        missing = validate_book_flight_fields(trf, "PNR1", "", "file-obj", None)
        assert missing == []
