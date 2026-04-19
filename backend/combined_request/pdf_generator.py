"""
PDF generator for Combined Request export.
Extracted from views.py to keep ViewSet lean.
"""

import io
from django.http import HttpResponse
from django.utils import timezone


# ── Design-system colour tokens ──────────────────────────────────────────────
PRIMARY_HEX = '#0d9488'


def _build_styles():
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    styles = getSampleStyleSheet()
    primary = colors.HexColor(PRIMARY_HEX)

    title_style = ParagraphStyle(
        'CRTitle', parent=styles['Heading1'],
        fontSize=18, spaceAfter=20, textColor=primary,
    )
    heading_style = ParagraphStyle(
        'CRHeading', parent=styles['Heading2'],
        fontSize=12, spaceBefore=15, spaceAfter=10, textColor=primary,
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=colors.grey,
    )

    from reportlab.platypus import TableStyle
    table_style = TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  primary),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.whitesmoke),
        ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  10),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  12),
        ('BACKGROUND',    (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR',     (0, 1), (-1, -1), colors.black),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 9),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])

    return styles['Normal'], title_style, heading_style, footer_style, table_style


def generate_combined_request_pdf(cr) -> HttpResponse:
    """Build and return an HttpResponse with the PDF for *cr*."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
    from django.contrib.contenttypes.models import ContentType
    from workflows.models import WorkflowInstance

    normal, title_style, heading_style, footer_style, table_style = _build_styles()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.5 * inch, leftMargin=0.5 * inch,
        topMargin=0.5 * inch,  bottomMargin=0.5 * inch,
    )

    two_col = [2 * inch, 5 * inch]
    elements = []

    # ── Title ─────────────────────────────────────────────────────────────────
    elements.append(Paragraph(
        f"Combined Request - {cr.request_number or f'CR-{cr.id}'}",
        title_style,
    ))
    elements.append(Spacer(1, 8))

    modules = cr.get_included_modules() if hasattr(cr, 'get_included_modules') else []
    if modules:
        elements.append(Paragraph(f"<b>Modules:</b> {', '.join(modules)}", normal))
    elements.append(Spacer(1, 12))

    # ── Requestor Information ─────────────────────────────────────────────────
    elements.append(Paragraph("Requestor Information", heading_style))
    elements.append(Table([
        ['Field', 'Value'],
        ['Name',         cr.requestor_name or 'Not provided'],
        ['Staff ID',     cr.staff_id or 'Not provided'],
        ['Department',   cr.department or 'Not provided'],
        ['Position',     cr.position or 'Not provided'],
        ['Email',        cr.email or (cr.requestor.email if cr.requestor else 'Not provided')],
        ['Phone',        cr.phone or 'Not provided'],
        ['Cost Center',  cr.cost_center or 'Not provided'],
    ], colWidths=two_col, style=table_style))

    # ── Status & Tracking ─────────────────────────────────────────────────────
    elements.append(Paragraph("Status &amp; Tracking", heading_style))
    elements.append(Table([
        ['Field', 'Value'],
        ['Request Number', cr.request_number or f'CR-{cr.id}'],
        ['Status',         cr.status or 'Draft'],
        ['Created',        cr.created_at.strftime('%Y-%m-%d %H:%M') if cr.created_at else '-'],
        ['Submitted',      cr.submitted_at.strftime('%Y-%m-%d %H:%M') if cr.submitted_at else 'Not submitted'],
    ], colWidths=two_col, style=table_style))

    # ── Travel / TSR Details ──────────────────────────────────────────────────
    if cr.include_travel:
        elements.append(Paragraph("Travel / TSR Details", heading_style))
        elements.append(Table([
            ['Field', 'Value'],
            ['Travel Type',         (cr.travel_type or '-').capitalize()],
            ['Trip Type',           cr.trip_type or 'Round Trip'],
            ['Purpose',             (cr.travel_purpose or 'Not provided')[:120]],
            ['Departure Date',      str(cr.departure_date) if cr.departure_date else '-'],
            ['Return Date',         str(cr.return_date) if cr.return_date else '-'],
            ['Destination Country', cr.destination_country or '-'],
            ['Destination City',    cr.destination_city or '-'],
        ], colWidths=two_col, style=table_style))

        itinerary = cr.itinerary_segments.all().order_by('segment_order')
        if itinerary.exists():
            elements.append(Paragraph("Itinerary", heading_style))
            itin_data = [['#', 'Day', 'Date', 'From', 'To', 'Mode', 'Flight']]
            for seg in itinerary:
                itin_data.append([
                    str(seg.segment_order),
                    seg.day_of_week or '-',
                    str(seg.segment_date) if seg.segment_date else '-',
                    (seg.from_location or '-')[:20],
                    (seg.to_location or '-')[:20],
                    seg.mode_of_travel or '-',
                    seg.flight_number or '-',
                ])
            elements.append(Table(itin_data, style=table_style,
                                  colWidths=[0.3*inch, 0.9*inch, 0.9*inch,
                                             1.4*inch, 1.4*inch, 0.8*inch, 0.8*inch]))

    # ── Transport Details ─────────────────────────────────────────────────────
    if cr.include_transport:
        elements.append(Paragraph("Transport Details", heading_style))
        elements.append(Table([
            ['Field', 'Value'],
            ['Purpose',       (cr.transport_purpose or 'Not provided')[:120]],
            ['TSR Reference', cr.transport_tsr_reference or '-'],
        ], colWidths=two_col, style=table_style))

        segments = cr.transport_segments.all().order_by('segment_order')
        if segments.exists():
            elements.append(Paragraph("Transport Segments", heading_style))
            seg_data = [['#', 'Date', 'From', 'To', 'Time', 'Type', 'Pax']]
            for seg in segments:
                seg_data.append([
                    str(seg.segment_order),
                    str(seg.pickup_date) if seg.pickup_date else '-',
                    (seg.pickup_location or '-')[:20],
                    (seg.dropoff_location or '-')[:20],
                    str(seg.pickup_time) if seg.pickup_time else '-',
                    seg.transport_type or '-',
                    str(seg.passengers or '-'),
                ])
            elements.append(Table(seg_data, style=table_style,
                                  colWidths=[0.3*inch, 0.9*inch, 1.3*inch,
                                             1.3*inch, 0.8*inch, 1*inch, 0.7*inch]))

    # ── Accommodation Details ─────────────────────────────────────────────────
    if cr.include_accommodation:
        elements.append(Paragraph("Accommodation Details", heading_style))
        elements.append(Table([
            ['Field', 'Value'],
            ['Location',         cr.accommodation_location or '-'],
            ['Gender',           cr.accommodation_gender or '-'],
            ['Room Type',        cr.accommodation_room_type or '-'],
            ['Check-in',         str(cr.accommodation_checkin) if cr.accommodation_checkin else '-'],
            ['Check-out',        str(cr.accommodation_checkout) if cr.accommodation_checkout else '-'],
            ['Special Requests', (cr.accommodation_special_requests or '-')[:80]],
        ], colWidths=two_col, style=table_style))

    # ── Visa Details ──────────────────────────────────────────────────────────
    if cr.include_visa:
        elements.append(Paragraph("Visa Details", heading_style))
        elements.append(Table([
            ['Field', 'Value'],
            ['Destination Country', cr.visa_destination_country or '-'],
            ['Visa Type',           cr.visa_type or '-'],
            ['Passport Number',     cr.visa_passport_number or '-'],
            ['Passport Expiry',     str(cr.visa_passport_expiry_date) if cr.visa_passport_expiry_date else '-'],
            ['Entry Type',          cr.visa_entry_type or '-'],
            ['Duration of Stay',    cr.visa_duration_of_stay or '-'],
        ], colWidths=two_col, style=table_style))

    # ── Approval History ──────────────────────────────────────────────────────
    try:
        content_type = ContentType.objects.get_for_model(cr)
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type, object_id=cr.id
        ).first()

        if workflow_instance and workflow_instance.step_executions.exists():
            elements.append(Paragraph("Approval History", heading_style))
            approval_data = [['Step', 'Role', 'Status', 'Actioned By', 'Date', 'Comments']]
            for step in workflow_instance.step_executions.all().order_by('workflow_step__step_order'):
                approval_data.append([
                    str(step.workflow_step.step_order),
                    (step.workflow_step.step_name or '-')[:25],
                    step.status or '-',
                    step.actioned_by.name if step.actioned_by else '-',
                    step.action_date.strftime('%Y-%m-%d') if step.action_date else '-',
                    (step.comments or '-')[:30],
                ])
            elements.append(Table(approval_data, style=table_style,
                                  colWidths=[0.4*inch, 1.5*inch, 0.9*inch,
                                             1.2*inch, 1*inch, 2.3*inch]))
    except Exception:
        pass

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} | Travel Management System",
        footer_style,
    ))

    doc.build(elements)
    buffer.seek(0)

    filename = f"combined_request_{cr.request_number or cr.id}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
