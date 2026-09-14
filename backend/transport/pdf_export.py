"""
Transport Request PDF export - extracted from TransportRequestViewSet.export_pdf
(see docs/CODEBASE_REFACTOR_ROADMAP.md item 7). Pure presentational logic,
no business rules - a plain function, not a ViewSet action, so it needs no
DRF request/response wiring beyond the HttpResponse it returns.
"""

import io

from django.http import HttpResponse
from reportlab.lib.units import inch
from utils import pdf_export


def build_request_pdf(transport_request) -> HttpResponse:
    """
    Export Transport Request to PDF

    Returns a PDF document containing all transport request details including:
    - Requestor information
    - Transport details (pickup, dropoff, vehicle type)
    - Journey segments
    - Vehicle assignment details
    - Approval history and workflow status
    """
    buffer = io.BytesIO()
    doc = pdf_export.new_document(buffer)
    styles = pdf_export.get_styles()

    elements = pdf_export.build_header(
        title="Transport Request",
        request_number=transport_request.request_number or f"TR-{transport_request.id}",
        status=transport_request.status,
        styles=styles,
    )

    # Requestor Information
    elements.extend(pdf_export.section_heading("Requestor Information", styles))
    requestor_data = [
        ["Field", "Value"],
        ["Name", transport_request.requestor_name or "Not provided"],
        ["Staff ID", transport_request.staff_id or "Not provided"],
        ["Department", transport_request.department or "Not provided"],
        ["Position", transport_request.position or "Not provided"],
        [
            "Email",
            (
                transport_request.requestor.email
                if transport_request.requestor
                else "Not provided"
            ),
        ],
    ]
    elements.append(pdf_export.make_table(requestor_data, [2 * inch, 5 * inch]))

    # Status & Tracking
    elements.extend(pdf_export.section_heading("Status &amp; Tracking", styles))
    tracking_data = [
        ["Field", "Value"],
        [
            "Request Number",
            transport_request.request_number or f"TR-{transport_request.id}",
        ],
        ["Current Status", transport_request.status],
        [
            "TSR Reference",
            (
                transport_request.trf.request_number
                if transport_request.trf_id and transport_request.trf
                else "Ad-Hoc Transport Request"
            ),
        ],
        [
            "Created",
            (
                transport_request.created_at.strftime("%Y-%m-%d %H:%M")
                if transport_request.created_at
                else "Not available"
            ),
        ],
        [
            "Submitted",
            (
                transport_request.submitted_at.strftime("%Y-%m-%d %H:%M")
                if transport_request.submitted_at
                else "Not submitted"
            ),
        ],
        [
            "Last Updated",
            (
                transport_request.updated_at.strftime("%Y-%m-%d %H:%M")
                if transport_request.updated_at
                else "Not available"
            ),
        ],
    ]
    elements.append(pdf_export.make_table(tracking_data, [2 * inch, 5 * inch]))

    # Transport Details
    elements.extend(pdf_export.section_heading("Transport Details", styles))
    transport_data = [
        ["Field", "Value"],
        ["Purpose", (transport_request.purpose or "Not provided")[:100]],
        [
            "Additional Comments",
            (transport_request.additional_comments or "None")[:100],
        ],
    ]
    elements.append(pdf_export.make_table(transport_data, [2 * inch, 5 * inch]))

    # Journey Details from transport_details JSON field
    if transport_request.transport_details:
        # transport_details is a list of journey objects
        journeys = (
            transport_request.transport_details
            if isinstance(transport_request.transport_details, list)
            else []
        )
        if journeys:
            elements.extend(pdf_export.section_heading("Journey Details", styles))
            journey_data = [["#", "Date", "From", "To", "Time", "Passengers"]]
            for i, journey in enumerate(journeys, 1):
                journey_data.append(
                    [
                        str(i),
                        str(journey.get("date", "-"))[:10],
                        str(journey.get("from", journey.get("from_location", "-")))[
                            :20
                        ],
                        str(journey.get("to", journey.get("to_location", "-")))[:20],
                        str(
                            journey.get(
                                "departureTime", journey.get("departure_time", "-")
                            )
                        )[:8],
                        str(
                            journey.get(
                                "numberOfPassengers",
                                journey.get("number_of_passengers", "-"),
                            )
                        ),
                    ]
                )
            elements.append(
                pdf_export.make_table(
                    journey_data,
                    [
                        0.3 * inch,
                        0.9 * inch,
                        1.5 * inch,
                        1.5 * inch,
                        0.9 * inch,
                        1 * inch,
                    ],
                )
            )

    # Vehicle Assignment
    vehicle_assignments = transport_request.vehicle_assignments.all()
    if vehicle_assignments.exists():
        elements.extend(pdf_export.section_heading("Vehicle Assignment", styles))
        for assignment in vehicle_assignments:
            # Vehicle Type, Vehicle Capacity, and Driver License are
            # omitted: no admin processing UI (transport-processing or
            # transport-admin components) ever collects them as real
            # per-assignment data - they're hardcoded constants
            # ("COMPANY_VEHICLE", 4, "") on every assignment ever created.
            assignment_data = [
                ["Field", "Value"],
                ["Vehicle Number", assignment.vehicle_number or "-"],
                ["Driver Name", assignment.driver_name or "-"],
                ["Driver Contact", assignment.driver_contact or "-"],
                ["Assignment Status", assignment.status or "-"],
                [
                    "Assigned Date",
                    (
                        assignment.assignment_date.strftime("%Y-%m-%d %H:%M")
                        if assignment.assignment_date
                        else "-"
                    ),
                ],
                [
                    "Assigned By",
                    assignment.assigned_by.name if assignment.assigned_by else "-",
                ],
            ]
            elements.append(
                pdf_export.make_table(assignment_data, [2 * inch, 5 * inch])
            )

    # Approval History - try workflow first, then fall back to legacy approval steps
    approval_found = False

    step_executions = pdf_export.get_latest_step_executions(transport_request)
    if step_executions:
        elements.extend(pdf_export.section_heading("Approval History", styles))
        elements.append(
            pdf_export.make_table(
                pdf_export.approval_history_rows(step_executions),
                pdf_export.APPROVAL_HISTORY_COL_WIDTHS,
            )
        )
        approval_found = True

    # Fall back to legacy approval steps if no workflow found
    if not approval_found:
        approval_steps = transport_request.approval_steps.all().order_by("created_at")
        if approval_steps.exists():
            elements.extend(pdf_export.section_heading("Approval History", styles))
            elements.append(
                pdf_export.make_table(
                    pdf_export.legacy_approval_history_rows(approval_steps),
                    pdf_export.APPROVAL_HISTORY_COL_WIDTHS,
                )
            )

    # Build PDF
    pdf_export.build(doc, elements)
    buffer.seek(0)

    # Create response
    filename = (
        f"Transport-{transport_request.request_number or transport_request.id}.pdf"
    )
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
