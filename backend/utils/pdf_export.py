"""
Shared PDF export theme for TRF, Transport, Visa, and Accommodation
`export_pdf` endpoints.

Each module used to hand-roll its own reportlab title/heading/table styles
and a plain one-line footer, so the four PDFs looked subtly different and
none of them had page numbers, status-aware coloring, or zebra-striped
tables. This module centralizes that visual language so every export looks
like it came from the same system - business logic (which sections/rows to
show) stays in each module's own `export_pdf`.
"""

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================
# Palette
# ============================================================
PRIMARY = colors.HexColor("#0d9488")
PRIMARY_DARK = colors.HexColor("#0f766e")
PRIMARY_TINT = colors.HexColor("#99f6e4")
INK = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
BORDER = colors.HexColor("#e2e8f0")
ROW_ALT = colors.HexColor("#f8fafc")
WHITE = colors.white

# Status -> (text color, background tint). Matched by substring against the
# lowercased status string, so "Pending Line Manager", "Pending HOD", etc.
# all fall through to the generic "pending" amber.
_STATUS_COLORS = {
    "reject": (colors.HexColor("#b91c1c"), colors.HexColor("#fee2e2")),
    "cancel": (colors.HexColor("#b91c1c"), colors.HexColor("#fee2e2")),
    "draft": (colors.HexColor("#475569"), colors.HexColor("#f1f5f9")),
    "complet": (colors.HexColor("#15803d"), colors.HexColor("#dcfce7")),
    "approv": (colors.HexColor("#15803d"), colors.HexColor("#dcfce7")),
    "assign": (colors.HexColor("#15803d"), colors.HexColor("#dcfce7")),
    "process": (colors.HexColor("#1d4ed8"), colors.HexColor("#dbeafe")),
    "pending": (colors.HexColor("#b45309"), colors.HexColor("#fef3c7")),
    "submit": (colors.HexColor("#b45309"), colors.HexColor("#fef3c7")),
}


def status_colors(status: str):
    """Returns (text_color, background_color) for a status string."""
    status_lower = (status or "").lower()
    for keyword, pair in _STATUS_COLORS.items():
        if keyword in status_lower:
            return pair
    return (MUTED, colors.HexColor("#f1f5f9"))


# ============================================================
# Styles
# ============================================================
def get_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PDFTitle",
            parent=base["Heading1"],
            fontSize=16,
            leading=19,
            textColor=WHITE,
            fontName="Helvetica-Bold",
        ),
        "banner_meta": ParagraphStyle(
            "PDFBannerMeta",
            parent=base["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=PRIMARY_TINT,
            alignment=2,  # right
        ),
        "heading": ParagraphStyle(
            "PDFHeading",
            parent=base["Heading2"],
            fontSize=11.5,
            spaceBefore=14,
            spaceAfter=4,
            textColor=PRIMARY_DARK,
            fontName="Helvetica-Bold",
        ),
        "normal": ParagraphStyle(
            "PDFNormal",
            parent=base["Normal"],
            fontSize=9,
            leading=13,
            textColor=INK,
        ),
        "note": ParagraphStyle(
            "PDFNote",
            parent=base["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
        ),
    }


# ============================================================
# Table
# ============================================================
TABLE_STYLE = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ROW_ALT]),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 1, PRIMARY_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 6.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]
)


def make_table(data, col_widths):
    """Build a themed table. `data[0]` is treated as the header row."""
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TABLE_STYLE)
    return table


def section_heading(text, styles):
    """Section heading with a colored accent rule underneath."""
    return [
        Paragraph(text, styles["heading"]),
        HRFlowable(
            width="100%",
            thickness=0.75,
            color=BORDER,
            spaceBefore=0,
            spaceAfter=8,
        ),
    ]


# ============================================================
# Header banner + status badge
# ============================================================
def build_header(title, request_number, status, styles):
    """
    Full-width colored banner (title left, request-number/timestamp right)
    followed by a status badge pill. Returns a list of flowables to append
    at the top of `elements`.
    """
    generated = timezone.now().strftime("%Y-%m-%d %H:%M")
    banner = Table(
        [
            [
                Paragraph(title, styles["title"]),
                Paragraph(
                    f"{request_number}<br/>Generated {generated}",
                    styles["banner_meta"],
                ),
            ]
        ],
        colWidths=[3.9 * inch, 3.1 * inch],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (0, 0), 14),
                ("RIGHTPADDING", (1, 0), (1, 0), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    text_color, bg_color = status_colors(status)
    badge_style = ParagraphStyle(
        "PDFStatusBadge",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=text_color,
    )
    badge = Table(
        [[Paragraph((status or "-").upper(), badge_style)]],
        colWidths=[None],
    )
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                ("BOX", (0, 0), (-1, -1), 0.75, text_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    return [banner, Spacer(1, 10), badge, Spacer(1, 10)]


# ============================================================
# Document + footer (page numbers on every page)
# ============================================================
def new_document(buffer):
    return SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.55 * inch,
    )


def draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(0.5 * inch, 0.4 * inch, letter[0] - 0.5 * inch, 0.4 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        0.5 * inch,
        0.27 * inch,
        f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} | Travel Management System",
    )
    canvas.drawRightString(letter[0] - 0.5 * inch, 0.27 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(doc, elements):
    """Build the document with the themed footer/page numbers on every page."""
    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
