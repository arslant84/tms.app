"""
Visa Application PDF export - extracted from VisaApplicationViewSet.export_pdf
(see docs/CODEBASE_REFACTOR_ROADMAP.md item 8). Pure presentational logic,
no business rules - a plain function, not a ViewSet action, so it needs no
DRF request/response wiring beyond the HttpResponse it returns.
"""

import io

from django.http import HttpResponse
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
from utils import pdf_export


def build_request_pdf(visa) -> HttpResponse:
    """
    Export Visa Application to PDF

    Returns a PDF document containing all visa application details including:
    - Applicant information
    - Travel details
    - Passport information
    - Visa type and entry details
    - Approval history and workflow status
    """
    buffer = io.BytesIO()
    doc = pdf_export.new_document(buffer)
    styles = pdf_export.get_styles()
    normal_style = styles["normal"]

    elements = pdf_export.build_header(
        title="Visa Application",
        request_number=visa.request_number or f"VISA-{visa.id}",
        status=visa.status,
        styles=styles,
    )

    # Applicant Information
    elements.extend(pdf_export.section_heading("Applicant Information", styles))
    applicant_data = [
        ["Field", "Value"],
        ["Name", visa.requestor_name or "Not provided"],
        ["Staff ID", visa.staff_id or "Not provided"],
        ["Department", visa.department or "Not provided"],
        ["Position", visa.position or "Not provided"],
        ["Email", visa.email or (visa.user.email if visa.user else "Not provided")],
        ["Contact Telephone", visa.contact_telephone or "Not provided"],
        ["Home Address", (visa.home_address or "Not provided")[:80]],
    ]
    elements.append(pdf_export.make_table(applicant_data, [2 * inch, 5 * inch]))

    # Status & Tracking
    elements.extend(pdf_export.section_heading("Status &amp; Tracking", styles))
    tracking_data = [
        ["Field", "Value"],
        ["Request Number", visa.request_number or f"VISA-{visa.id}"],
        ["Current Status", visa.status],
        ["TRF Reference", visa.trf_reference_number or "Not linked"],
        [
            "Created",
            (
                visa.created_at.strftime("%Y-%m-%d %H:%M")
                if visa.created_at
                else "Not available"
            ),
        ],
        [
            "Submitted",
            (
                visa.submitted_date.strftime("%Y-%m-%d %H:%M")
                if visa.submitted_date
                else "Not submitted"
            ),
        ],
        [
            "Processing Started",
            (
                visa.processing_started_at.strftime("%Y-%m-%d %H:%M")
                if visa.processing_started_at
                else "Not started"
            ),
        ],
        [
            "Processing Completed",
            (
                visa.processing_completed_at.strftime("%Y-%m-%d %H:%M")
                if visa.processing_completed_at
                else "Not completed"
            ),
        ],
    ]
    if visa.processing_completed_by:
        tracking_data.append(["Processed By", visa.processing_completed_by.name])
    tracking_data.append(
        [
            "Last Updated",
            (
                visa.updated_at.strftime("%Y-%m-%d %H:%M")
                if visa.updated_at
                else "Not available"
            ),
        ]
    )
    elements.append(pdf_export.make_table(tracking_data, [2 * inch, 5 * inch]))

    # Travel Details
    elements.extend(pdf_export.section_heading("Travel Details", styles))
    travel_data = [
        ["Field", "Value"],
        ["Destination", visa.destination or "-"],
        ["Travel Purpose", visa.travel_purpose or "-"],
        [
            "Trip Start Date",
            (
                visa.trip_start_date.strftime("%Y-%m-%d")
                if visa.trip_start_date
                else "-"
            ),
        ],
        [
            "Trip End Date",
            visa.trip_end_date.strftime("%Y-%m-%d") if visa.trip_end_date else "-",
        ],
        [
            "Approximate Arrival",
            (
                visa.approximately_arrival_date.strftime("%Y-%m-%d")
                if visa.approximately_arrival_date
                else "-"
            ),
        ],
        ["Duration of Stay", visa.duration_of_stay or "-"],
        ["Itinerary Details", (visa.itinerary_details or "-")[:100]],
    ]
    elements.append(pdf_export.make_table(travel_data, [2 * inch, 5 * inch]))

    # Visa Information
    elements.extend(pdf_export.section_heading("Visa Information", styles))
    visa_info_data = [
        ["Field", "Value"],
        ["Visa Type", visa.visa_type or "-"],
        ["Visa Entry Type", visa.visa_entry_type or "-"],
        ["Request Type", visa.request_type or "-"],
        ["Work Visit Category", visa.work_visit_category or "-"],
        ["Application Fees Borne By", visa.application_fees_borne_by or "-"],
        ["Cost Centre Number", visa.cost_centre_number or "-"],
        ["TRF Reference Number", visa.trf_reference_number or "-"],
    ]
    elements.append(pdf_export.make_table(visa_info_data, [2 * inch, 5 * inch]))

    # Passport Details
    elements.extend(pdf_export.section_heading("Passport Details", styles))
    passport_data = [
        ["Field", "Value"],
        ["Passport Number", visa.passport_number or "-"],
        [
            "Date of Issuance",
            (
                visa.passport_date_of_issuance.strftime("%Y-%m-%d")
                if visa.passport_date_of_issuance
                else "-"
            ),
        ],
        ["Place of Issuance", visa.passport_place_of_issuance or "-"],
        [
            "Expiry Date",
            (
                visa.passport_expiry_date.strftime("%Y-%m-%d")
                if visa.passport_expiry_date
                else "-"
            ),
        ],
    ]
    elements.append(pdf_export.make_table(passport_data, [2 * inch, 5 * inch]))

    # Personal Demographics
    elements.extend(pdf_export.section_heading("Personal Demographics", styles))
    personal_data = [
        ["Field", "Value"],
        [
            "Date of Birth",
            visa.date_of_birth.strftime("%Y-%m-%d") if visa.date_of_birth else "-",
        ],
        ["Place of Birth", visa.place_of_birth or "-"],
        ["Citizenship", visa.citizenship or "-"],
        ["Marital Status", visa.marital_status or "-"],
        ["Family Information", (visa.family_information or "-")[:80]],
        ["Education Details", (visa.education_details or "-")[:80]],
    ]
    elements.append(pdf_export.make_table(personal_data, [2 * inch, 5 * inch]))

    # Employment Information
    if visa.current_employer_name or visa.current_employer_address:
        elements.extend(pdf_export.section_heading("Employment Information", styles))
        employer_data = [
            ["Field", "Value"],
            ["Employer Name", visa.current_employer_name or "-"],
            ["Employer Address", (visa.current_employer_address or "-")[:80]],
        ]
        elements.append(pdf_export.make_table(employer_data, [2 * inch, 5 * inch]))

    # Processing Details - format as table if available
    if visa.processing_details and isinstance(visa.processing_details, dict):
        elements.extend(pdf_export.section_heading("Processing Details", styles))
        processing_data = [["Field", "Value"]]
        # Map field names to readable labels
        field_labels = {
            "visa_number": "Visa Number",
            "visa_valid_from": "Valid From",
            "visa_valid_to": "Valid To",
            # The non-dialog "complete processing" action sends these
            # instead of visa_valid_from/visa_valid_to (see
            # visa-processing.component.ts executeCompleteProcessing) -
            # same meaning, different key.
            "visa_issue_date": "Valid From",
            "visa_expiry_date": "Valid To",
            "completed_at": "Completed At",
            "processing_notes": "Processing Notes",
            "completed_by_admin": "Completed by Admin",
        }
        for key, value in visa.processing_details.items():
            label = field_labels.get(key, key.replace("_", " ").title())
            # Format boolean values
            if isinstance(value, bool):
                value = "Yes" if value else "No"
            processing_data.append([label, str(value)[:80] if value else "-"])
        elements.append(pdf_export.make_table(processing_data, [2 * inch, 5 * inch]))

    # Approval History - try workflow first, then fall back to legacy approval steps
    approval_found = False

    step_executions = pdf_export.get_latest_step_executions(visa)
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
        approval_steps = visa.visaapprovalstep_set.all().order_by("created_at")
        if approval_steps.exists():
            elements.extend(pdf_export.section_heading("Approval History", styles))
            elements.append(
                pdf_export.make_table(
                    pdf_export.legacy_approval_history_rows(approval_steps),
                    pdf_export.APPROVAL_HISTORY_COL_WIDTHS,
                )
            )

    # Additional Comments
    if visa.additional_comments:
        elements.extend(pdf_export.section_heading("Additional Comments", styles))
        elements.append(Paragraph(visa.additional_comments[:500], normal_style))

    # Build PDF
    pdf_export.build(doc, elements)
    buffer.seek(0)

    # Create response
    filename = f"Visa-{visa.request_number or visa.id}.pdf"
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
