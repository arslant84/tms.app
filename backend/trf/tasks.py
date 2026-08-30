"""
Celery tasks for the TRF app.
"""

import io
import logging
import re

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger("trf")

# PDF bytes live in cache for 10 minutes — enough for a user to finish their
# download. After that the key expires automatically.
PDF_CACHE_TTL = 600


@shared_task(
    bind=True,
    max_retries=2,
    queue="pdfs",
    soft_time_limit=120,
    time_limit=180,
)
def export_trf_pdf(self, trf_id):
    """
    Generate a TRF PDF in a Celery worker and store the bytes in the
    Django cache (Redis) under key ``pdf:{task_id}``.

    Returns ``{"cache_key": ..., "filename": ...}`` on success so the
    download endpoint knows where to fetch the bytes.
    """
    from trf.models import TravelRequest

    try:
        trf = TravelRequest.objects.get(pk=trf_id)
    except TravelRequest.DoesNotExist:
        logger.error("export_trf_pdf: TravelRequest %s not found", trf_id)
        return {"error": "Travel Request not found"}

    try:
        pdf_bytes = _build_pdf_bytes(trf)
    except Exception as exc:
        countdown = 30 * (2**self.request.retries)
        logger.warning(
            "export_trf_pdf: PDF generation failed for TRF %s (attempt %d), "
            "retrying in %ds: %s",
            trf_id,
            self.request.retries + 1,
            countdown,
            exc,
        )
        raise self.retry(exc=exc, countdown=countdown)

    cache_key = f"pdf:{self.request.id}"
    cache.set(cache_key, pdf_bytes, timeout=PDF_CACHE_TTL)

    filename = f"TSR-{trf.request_number or trf.id}.pdf"
    logger.info("export_trf_pdf: cached %d bytes under %s", len(pdf_bytes), cache_key)
    return {"cache_key": cache_key, "filename": filename}


def _build_pdf_bytes(trf):
    """
    Generate and return PDF bytes for *trf*.

    This is the same logic as TravelRequestViewSet.export_pdf, extracted so
    it can run inside a Celery worker without an HTTP request context.
    """
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Spacer
    from trf.models import (
        TrfAdvanceAmountRequestedItem,
        TrfAdvanceBankDetail,
        TrfApprovalStep,
        TrfDailyMealSelection,
        TrfItinerarySegment,
    )
    from utils import pdf_export

    buffer = io.BytesIO()
    doc = pdf_export.new_document(buffer)
    styles = pdf_export.get_styles()
    normal_style = styles["normal"]

    elements = pdf_export.build_header(
        title="Travel Service Request",
        request_number=trf.request_number or f"TSR-{trf.id}",
        status=trf.status,
        styles=styles,
    )

    # Requestor Information
    is_external = trf.travel_type == "External Parties"
    if is_external:
        elements.extend(pdf_export.section_heading("External Party Details", styles))
        requestor_data = [
            ["Field", "Value"],
            ["Name", trf.requestor_name or trf.external_full_name or "-"],
            ["Organization", trf.external_organization or "-"],
            ["Ref. to Authority Letter", trf.external_ref_to_authority_letter or "-"],
            ["Cost Center", trf.external_cost_center or "-"],
            ["Email", trf.email or "-"],
            ["Phone/Email", trf.tel_email or "-"],
        ]
    else:
        elements.extend(pdf_export.section_heading("Requestor Information", styles))
        requestor_data = [
            ["Field", "Value"],
            ["Name", trf.requestor_name or "-"],
            ["Staff ID", trf.staff_id or "-"],
            ["Department", trf.department or "-"],
            ["Position", trf.position or "-"],
            ["Cost Center", trf.cost_center or "-"],
            ["Email", trf.email or "-"],
            ["Phone/Email", trf.tel_email or "-"],
        ]
    elements.append(pdf_export.make_table(requestor_data, [2 * inch, 5 * inch]))

    # Travel Details
    elements.extend(pdf_export.section_heading("Travel Details", styles))
    travel_data = [
        ["Field", "Value"],
        ["Travel Type", trf.travel_type or "-"],
        ["Purpose", (trf.purpose or "-")[:100]],
        [
            "Submitted At",
            trf.submitted_at.strftime("%Y-%m-%d %H:%M") if trf.submitted_at else "-",
        ],
        [
            "Created At",
            trf.created_at.strftime("%Y-%m-%d %H:%M") if trf.created_at else "-",
        ],
    ]
    if trf.travel_type in ("Overseas", "Home Leave"):
        travel_data.append(
            [
                "Advance T&C Accepted",
                (
                    f"Yes ({trf.advance_consent_accepted_at.strftime('%Y-%m-%d %H:%M')})"
                    if trf.advance_consent_accepted and trf.advance_consent_accepted_at
                    else ("Yes" if trf.advance_consent_accepted else "No")
                ),
            ]
        )
    elements.append(pdf_export.make_table(travel_data, [2 * inch, 5 * inch]))

    # Itinerary
    itinerary_segments = TrfItinerarySegment.objects.filter(trf=trf).order_by(
        "segment_date"
    )
    if itinerary_segments.exists():
        elements.extend(pdf_export.section_heading("Itinerary", styles))
        itinerary_data = [["Date", "From", "To", "Departure", "Arrival", "Remarks"]]
        for seg in itinerary_segments:
            itinerary_data.append(
                [
                    seg.segment_date.strftime("%Y-%m-%d") if seg.segment_date else "-",
                    seg.from_location or "-",
                    seg.to_location or "-",
                    seg.departure_time or "-",
                    seg.arrival_time or "-",
                    (seg.remarks or "-")[:30],
                ]
            )
        elements.append(
            pdf_export.make_table(
                itinerary_data,
                [1 * inch, 1.2 * inch, 1.2 * inch, 0.9 * inch, 0.9 * inch, 1.8 * inch],
            )
        )

    # Meal Provision
    meal_selections = TrfDailyMealSelection.objects.filter(trf=trf).order_by(
        "meal_date"
    )
    if meal_selections.exists():
        elements.extend(pdf_export.section_heading("Meal Provision", styles))
        meal_status = (trf.meal_processing_status or "Pending").title()
        elements.append(
            Paragraph(f"<b>Processing Status:</b> {meal_status}", normal_style)
        )
        elements.append(Spacer(1, 6))
        meal_data = [["Date", "Breakfast", "Lunch", "Dinner", "Supper", "Refreshment"]]
        for meal in meal_selections:
            meal_data.append(
                [
                    meal.meal_date.strftime("%Y-%m-%d") if meal.meal_date else "-",
                    "Yes" if meal.breakfast else "-",
                    "Yes" if meal.lunch else "-",
                    "Yes" if meal.dinner else "-",
                    "Yes" if meal.supper else "-",
                    "Yes" if meal.refreshment else "-",
                ]
            )
        elements.append(
            pdf_export.make_table(
                meal_data,
                [
                    1.2 * inch,
                    1.1 * inch,
                    1.1 * inch,
                    1.1 * inch,
                    1.1 * inch,
                    1.4 * inch,
                ],
            )
        )

    # Embedded Accommodation
    from accommodation.models import AccommodationBooking, AccommodationRequest

    accommodation_requests = AccommodationRequest.objects.filter(trf=trf)
    if accommodation_requests.exists():
        elements.extend(pdf_export.section_heading("Accommodation", styles))
        for accom in accommodation_requests:
            accom_data = [
                ["Field", "Value"],
                ["Request Number", accom.request_number or "-"],
                ["Status", accom.status or "-"],
            ]
            bookings = AccommodationBooking.objects.filter(
                accommodation_request=accom
            ).select_related("staff_house", "room")
            if bookings.exists():
                booking_summary = "; ".join(
                    f"{b.room} @ {b.staff_house} ({b.date})" for b in bookings
                )
                accom_data.append(["Assigned", booking_summary[:200]])
            elements.append(pdf_export.make_table(accom_data, [2 * inch, 5 * inch]))

    # Embedded Transport
    from transport.models import TransportRequest

    transport_requests = TransportRequest.objects.filter(trf=trf)
    if transport_requests.exists():
        elements.extend(pdf_export.section_heading("Transport", styles))
        for transport_req in transport_requests:
            elements.append(
                Paragraph(
                    f"<b>Request Number:</b> {transport_req.request_number or '-'} "
                    f"&nbsp;&nbsp; <b>Status:</b> {transport_req.status or '-'}",
                    normal_style,
                )
            )
            elements.append(Spacer(1, 6))
            journeys = transport_req.transport_details or []
            if journeys:
                journey_data = [["Date", "From", "To", "Departure", "Passengers"]]
                for journey in journeys:
                    journey_data.append(
                        [
                            journey.get("date", "-"),
                            journey.get("from", "-"),
                            journey.get("to", "-"),
                            journey.get("departureTime", "-"),
                            str(journey.get("numberOfPassengers", "-")),
                        ]
                    )
                elements.append(
                    pdf_export.make_table(
                        journey_data,
                        [1.2 * inch, 1.5 * inch, 1.5 * inch, 1.2 * inch, 1.1 * inch],
                    )
                )

    # Bank Details
    try:
        bank_detail = TrfAdvanceBankDetail.objects.get(trf=trf)
        elements.extend(pdf_export.section_heading("Bank Details for Advance", styles))
        bank_data = [
            ["Field", "Value"],
            ["Bank Name", bank_detail.bank_name or "-"],
            ["Account Name", bank_detail.account_name or "-"],
            ["Account Number", bank_detail.account_number or "-"],
            ["Currency", bank_detail.currency or "-"],
        ]
        elements.append(pdf_export.make_table(bank_data, [2 * inch, 5 * inch]))
    except TrfAdvanceBankDetail.DoesNotExist:
        pass

    # Advance Amount Requested
    advance_items = TrfAdvanceAmountRequestedItem.objects.filter(trf=trf).order_by(
        "date_from"
    )
    if advance_items.exists():
        elements.extend(pdf_export.section_heading("Advance Amount Requested", styles))
        advance_data = [["From", "To", "LH", "MA", "OA", "TR", "OE", "USD", "Remarks"]]
        total_usd = 0
        period_from = None
        period_to = None
        for item in advance_items:
            total_usd += item.usd or 0
            if item.date_from and (period_from is None or item.date_from < period_from):
                period_from = item.date_from
            if item.date_to and (period_to is None or item.date_to > period_to):
                period_to = item.date_to
            advance_data.append(
                [
                    item.date_from.strftime("%Y-%m-%d") if item.date_from else "-",
                    item.date_to.strftime("%Y-%m-%d") if item.date_to else "-",
                    f"{item.lh:,.2f}",
                    f"{item.ma:,.2f}",
                    f"{item.oa:,.2f}",
                    f"{item.tr:,.2f}",
                    f"{item.oe:,.2f}",
                    f"{item.usd:,.2f}",
                    (item.remarks or "-")[:30],
                ]
            )
        advance_data.append(["", "", "", "", "", "", "Total:", f"{total_usd:,.2f}", ""])
        elements.append(
            pdf_export.make_table(
                advance_data,
                [
                    0.8 * inch,
                    0.8 * inch,
                    0.6 * inch,
                    0.6 * inch,
                    0.6 * inch,
                    0.6 * inch,
                    0.6 * inch,
                    0.7 * inch,
                    1.7 * inch,
                ],
            )
        )

        # Advance T&C acknowledgement — the actual text the requestor agreed to
        # (previously only a bare "Yes/No" summary row appeared in the PDF at
        # all, in the Travel Details table above; this is the real wording
        # from advance-amount-editor.component.html, with the same values
        # substituted in, mirrored here so the PDF matches what was shown
        # on-screen at submission time).
        if (
            trf.travel_type in ("Overseas", "Home Leave")
            and trf.advance_consent_accepted
        ):
            elements.append(Spacer(1, 10))
            elements.extend(
                pdf_export.section_heading(
                    "Advance Terms & Conditions Acknowledgement", styles
                )
            )
            period_from_str = period_from.strftime("%Y-%m-%d") if period_from else "-"
            period_to_str = period_to.strftime("%Y-%m-%d") if period_to else "-"
            elements.append(
                Paragraph(
                    f"I, {trf.requestor_name or '-'}, hereby acknowledge the above Terms and "
                    f"Conditions and express my willingness that should there be any excess from "
                    f"actual expenditure as per approved Staff Expense Claim Form vs the advance "
                    f"of USD {total_usd:,.2f} (advance amount) or in case of non utilization of "
                    f"the advance amount which I received for my official travel or purpose from "
                    f"{period_from_str} to {period_to_str}, the excess or unutilized advanced "
                    f"amount shall be refunded to PETRONAS Carigali (Turkmenistan) Sdn Bhd "
                    f'("PC(T)SB/Company") by way of deduction from my salary. I also agree that '
                    f"the deduction of the excess advance or unutilized advance amount may be "
                    f"made either in full or in part at PC(T)SB's discretion.",
                    normal_style,
                )
            )
            elements.append(Spacer(1, 6))
            elements.append(
                Paragraph(
                    "I also agree that PC(T)SB reserves the right to instruct me to refund in "
                    "cash the excess advance or unutilized advance amount either in full or in "
                    "part.",
                    normal_style,
                )
            )
            elements.append(Spacer(1, 6))
            accepted_at = (
                trf.advance_consent_accepted_at.strftime("%Y-%m-%d %H:%M")
                if trf.advance_consent_accepted_at
                else "-"
            )
            elements.append(
                Paragraph(f"<b>Accepted:</b> Yes ({accepted_at})", normal_style)
            )

    # Flight Booking Details
    flight_bookings = trf.flight_bookings.all().order_by("departure_time")
    if flight_bookings.exists():
        elements.extend(pdf_export.section_heading("Flight Booking Details", styles))
        for booking in flight_bookings:
            summary_data = [
                ["Field", "Value"],
                ["PNR / Booking Reference", booking.booking_reference or "-"],
                ["Airline", booking.airline or "-"],
                ["Status", booking.status or "-"],
            ]
            elements.append(pdf_export.make_table(summary_data, [2 * inch, 5 * inch]))
            segment_data = [
                [
                    "Leg",
                    "Flight No.",
                    "Departure",
                    "Arrival",
                    "Departure Time",
                    "Arrival Time",
                ]
            ]
            for seg in booking.segments.all():
                label = f"{seg.get_direction_display()} {seg.sequence}"
                segment_data.append(
                    [
                        label,
                        seg.flight_number or "-",
                        seg.departure_airport or "-",
                        seg.arrival_airport or "-",
                        (
                            seg.departure_time.strftime("%Y-%m-%d %H:%M")
                            if seg.departure_time
                            else "-"
                        ),
                        (
                            seg.arrival_time.strftime("%Y-%m-%d %H:%M")
                            if seg.arrival_time
                            else "-"
                        ),
                    ]
                )
            if len(segment_data) == 1:
                segment_data.append(
                    [
                        "Outbound 1",
                        booking.flight_number or "-",
                        booking.departure_airport or "-",
                        booking.arrival_airport or "-",
                        (
                            booking.departure_time.strftime("%Y-%m-%d %H:%M")
                            if booking.departure_time
                            else "-"
                        ),
                        (
                            booking.arrival_time.strftime("%Y-%m-%d %H:%M")
                            if booking.arrival_time
                            else "-"
                        ),
                    ]
                )
            elements.append(
                pdf_export.make_table(
                    segment_data,
                    [
                        0.9 * inch,
                        0.9 * inch,
                        1.4 * inch,
                        1.4 * inch,
                        1.4 * inch,
                        1.4 * inch,
                    ],
                )
            )

    # Approval History — prefer modern WorkflowEngine steps, fall back to legacy.
    # TRF writes to both TrfApprovalStep (legacy) and WorkflowStepExecution
    # (modern) on every approval action, so legacy rows almost always exist
    # too; the modern rows are checked first because only they record who
    # actually actioned each step (actioned_by) — TrfApprovalStep never did,
    # only the role. Checking legacy first (as this used to) meant the
    # richer modern path was effectively never reached for TRF exports.
    from django.contrib.contenttypes.models import ContentType
    from workflows.models import WorkflowInstance

    content_type = ContentType.objects.get_for_model(trf)
    workflow_instance = (
        WorkflowInstance.objects.filter(content_type=content_type, object_id=trf.id)
        .order_by("-created_at")
        .first()
    )
    step_executions = (
        workflow_instance.step_executions.select_related(
            "workflow_step", "actioned_by"
        ).order_by("workflow_step__step_order")
        if workflow_instance
        else None
    )

    if step_executions is not None and step_executions.exists():
        elements.extend(pdf_export.section_heading("Approval History", styles))
        approval_data = [["Approver", "Role", "Status", "Date", "Comments"]]
        for execution in step_executions:
            # WorkflowStep.step_name is always "Step N: <Role> Approval"
            # (e.g. "Step 2: HOD Approval") — strip that boilerplate down to
            # just the role, matching the legacy TrfApprovalStep.step_role
            # convention this table used to show exclusively.
            step_name = execution.workflow_step.step_name or ""
            role_display = re.sub(r"^Step \d+:\s*", "", step_name)
            role_display = re.sub(r"\s*Approval$", "", role_display).strip()
            approval_data.append(
                [
                    (execution.actioned_by.name if execution.actioned_by else "-"),
                    (role_display or step_name or "-")[:22],
                    execution.status or "-",
                    (
                        execution.action_date.strftime("%Y-%m-%d %H:%M")
                        if execution.action_date
                        else "-"
                    ),
                    (execution.comments or "-")[:40],
                ]
            )
        elements.append(
            pdf_export.make_table(
                approval_data,
                [1.5 * inch, 1.5 * inch, 0.8 * inch, 1.3 * inch, 2.1 * inch],
            )
        )
    else:
        approval_steps = TrfApprovalStep.objects.filter(trf=trf).order_by("created_at")
        if approval_steps.exists():
            elements.extend(pdf_export.section_heading("Approval History", styles))
            # TrfApprovalStep never recorded who actioned a step, only their
            # role, so "Approver" is always "-" here.
            approval_data = [["Approver", "Role", "Status", "Date", "Comments"]]
            for step in approval_steps:
                approval_data.append(
                    [
                        "-",
                        step.step_role or "-",
                        step.status or "-",
                        (
                            step.step_date.strftime("%Y-%m-%d %H:%M")
                            if step.step_date
                            else "-"
                        ),
                        (step.comments or "-")[:50],
                    ]
                )
            elements.append(
                pdf_export.make_table(
                    approval_data,
                    [1.3 * inch, 1.2 * inch, 1 * inch, 1.4 * inch, 2.3 * inch],
                )
            )

    pdf_export.build(doc, elements)
    buffer.seek(0)
    return buffer.getvalue()
