"""
PDF export for a single AccommodationRequest.

Split out of AccommodationRequestViewSet.export_pdf (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 6, Phase 2) - a pure move, no
logic changed. Self-contained formatting only: takes the request
object, touches no other state, returns an HttpResponse.
"""

import io

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer
from utils import pdf_export
from workflows.models import WorkflowInstance


def build_request_pdf(accommodation_request):
    """
    Export Accommodation Request to PDF

    Returns a PDF document containing all accommodation request details including:
    - Requestor information
    - Status & Tracking
    - Booking details
    - Approval history and workflow status
    """
    buffer = io.BytesIO()
    doc = pdf_export.new_document(buffer)
    styles = pdf_export.get_styles()
    normal_style = styles["normal"]

    elements = pdf_export.build_header(
        title="Accommodation Request",
        request_number=accommodation_request.request_number
        or f"ACC-{accommodation_request.id}",
        status=accommodation_request.status,
        styles=styles,
    )

    # Requestor Information - Position, Cost Center, Tel/Email, and Email
    # are omitted: the live creation path (embedded in the Domestic TSR
    # wizard) never sends them, so they're always blank.
    elements.extend(pdf_export.section_heading("Requestor Information", styles))
    requestor_data = [
        ["Field", "Value"],
        ["Name", accommodation_request.requestor_name or "Not provided"],
        ["Staff ID", accommodation_request.staff_id or "Not provided"],
        ["Department", accommodation_request.department or "Not provided"],
    ]
    elements.append(pdf_export.make_table(requestor_data, [2 * inch, 5 * inch]))

    # Status & Tracking
    elements.extend(pdf_export.section_heading("Status &amp; Tracking", styles))
    trf = accommodation_request.trf
    tsr_reference = "Not linked"
    if trf:
        tsr_reference = trf.request_number or f"TSR-{trf.id}"

    tracking_data = [
        ["Field", "Value"],
        [
            "Request Number",
            accommodation_request.request_number or f"ACC-{accommodation_request.id}",
        ],
        ["Current Status", accommodation_request.status],
        ["TSR Reference", tsr_reference],
        [
            "Created",
            (
                accommodation_request.created_at.strftime("%Y-%m-%d %H:%M")
                if accommodation_request.created_at
                else "Not available"
            ),
        ],
        [
            "Submitted",
            (
                accommodation_request.submitted_at.strftime("%Y-%m-%d %H:%M")
                if accommodation_request.submitted_at
                else "Not submitted"
            ),
        ],
        [
            "Last Updated",
            (
                accommodation_request.updated_at.strftime("%Y-%m-%d %H:%M")
                if accommodation_request.updated_at
                else "Not available"
            ),
        ],
    ]
    elements.append(pdf_export.make_table(tracking_data, [2 * inch, 5 * inch]))

    # Booking Details
    bookings = (
        accommodation_request.bookings.all()
        .select_related("staff_house", "room")
        .order_by("date")
    )
    elements.extend(pdf_export.section_heading("Booking Details", styles))

    if bookings.exists():
        # Get unique staff house and room info
        first_booking = bookings.first()
        last_booking = bookings.last()

        # Booking summary info
        booking_summary = [
            ["Field", "Value"],
            [
                "Staff House",
                (
                    first_booking.staff_house.name
                    if first_booking.staff_house
                    else "Not assigned"
                ),
            ],
            [
                "Location",
                (
                    first_booking.staff_house.location
                    if first_booking.staff_house
                    else "Not available"
                ),
            ],
            [
                "Room",
                first_booking.room.name if first_booking.room else "Not assigned",
            ],
            [
                "Room Type",
                (
                    first_booking.room.room_type
                    if first_booking.room and first_booking.room.room_type
                    else "Standard"
                ),
            ],
            [
                "Room Capacity",
                (
                    str(first_booking.room.capacity)
                    if first_booking.room
                    else "Not available"
                ),
            ],
            [
                "Check-in Date",
                (
                    first_booking.date.strftime("%Y-%m-%d")
                    if first_booking.date
                    else "Not set"
                ),
            ],
            [
                "Check-out Date",
                (
                    last_booking.date.strftime("%Y-%m-%d")
                    if last_booking.date
                    else "Not set"
                ),
            ],
            ["Total Nights", str(bookings.count())],
            ["Booking Status", first_booking.status or "Pending"],
        ]
        elements.append(pdf_export.make_table(booking_summary, [2 * inch, 5 * inch]))

        # Daily booking breakdown if multiple nights
        if bookings.count() > 1:
            elements.append(Spacer(1, 10))
            elements.extend(pdf_export.section_heading("Daily Breakdown", styles))
            daily_data = [["Date", "Staff House", "Room", "Status"]]
            for booking in bookings:
                daily_data.append(
                    [
                        booking.date.strftime("%Y-%m-%d") if booking.date else "-",
                        booking.staff_house.name if booking.staff_house else "-",
                        booking.room.name if booking.room else "-",
                        booking.status or "-",
                    ]
                )
            elements.append(
                pdf_export.make_table(
                    daily_data, [1.5 * inch, 2 * inch, 2 * inch, 1.5 * inch]
                )
            )
    else:
        # No bookings yet
        no_booking_data = [
            ["Field", "Value"],
            ["Status", "No accommodation assigned yet"],
            ["Note", "Booking will be assigned after approval"],
        ]
        elements.append(pdf_export.make_table(no_booking_data, [2 * inch, 5 * inch]))

    # Approval History from Workflow
    try:
        content_type = ContentType.objects.get_for_model(accommodation_request)
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type, object_id=accommodation_request.id
        ).first()

        if workflow_instance and workflow_instance.step_executions.exists():
            # Build table first, then add heading only if we have data
            approval_data = [
                ["Step", "Role", "Status", "Actioned By", "Date", "Comments"]
            ]
            for step in workflow_instance.step_executions.select_related(
                "workflow_step", "actioned_by"
            ).order_by("workflow_step__step_order"):
                approval_data.append(
                    [
                        str(step.workflow_step.step_order),
                        (step.workflow_step.step_name or "-")[:14],
                        step.status or "-",
                        step.actioned_by.name if step.actioned_by else "-",
                        (
                            step.action_date.strftime("%Y-%m-%d %H:%M")
                            if step.action_date
                            else "-"
                        ),
                        (step.comments or "-")[:30],
                    ]
                )
            # Only add if we have actual data rows (more than just header)
            if len(approval_data) > 1:
                elements.extend(pdf_export.section_heading("Approval History", styles))
                elements.append(
                    pdf_export.make_table(
                        approval_data,
                        [
                            0.4 * inch,
                            1.2 * inch,
                            0.9 * inch,
                            1.2 * inch,
                            1.3 * inch,
                            2 * inch,
                        ],
                    )
                )
    except Exception:
        pass  # No workflow found, skip approval history

    # Additional Comments
    if accommodation_request.additional_comments:
        elements.extend(pdf_export.section_heading("Additional Comments", styles))
        elements.append(
            Paragraph(accommodation_request.additional_comments, normal_style)
        )

    # Additional Data (Request Details) - format as table if available
    if accommodation_request.additional_data and isinstance(
        accommodation_request.additional_data, dict
    ):
        elements.extend(pdf_export.section_heading("Request Details", styles))
        request_details_data = [["Field", "Value"]]
        # Map field names to readable labels
        field_labels = {
            "location": "Location",
            "requestor_gender": "Gender",
            "special_requests": "Special Requests",
            "flight_arrival_time": "Flight Arrival Time",
            "flight_departure_time": "Flight Departure Time",
            "requested_room_type": "Requested Room Type",
            "requested_check_in_date": "Requested Check-in",
            "requested_check_out_date": "Requested Check-out",
        }
        for key, value in accommodation_request.additional_data.items():
            label = field_labels.get(key, key.replace("_", " ").title())
            # Format boolean values
            if isinstance(value, bool):
                value = "Yes" if value else "No"
            if value:  # Only show non-empty values
                request_details_data.append([label, str(value)[:80]])
        # Only add if we have data rows
        if len(request_details_data) > 1:
            elements.append(
                pdf_export.make_table(request_details_data, [2 * inch, 5 * inch])
            )

    # Build PDF
    pdf_export.build(doc, elements)
    buffer.seek(0)

    # Create response
    filename = f"Accommodation-{accommodation_request.request_number or accommodation_request.id}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
