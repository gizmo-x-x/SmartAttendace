"""
pdf_service.py

Converts attendance data to a printable PDF and reads it back out later.
Both the student data AND the table configuration (columns, week count) are
hidden in the PDF's metadata, so re-importing rebuilds the exact same table.
"""

import json
from io import BytesIO

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from pypdf import PdfReader, PdfWriter

CUSTOM_METADATA_KEY = "/SnapAttendData"


def generate_attendance_pdf(students, config):
    columns = config.get("columns", [])
    num_weeks = config.get("numWeeks", 14)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()

    elements = [Paragraph("Attendance Register", styles["Title"]), Spacer(1, 10)]

    header = [c["label"] for c in columns] + [f"Wk{w}" for w in range(1, num_weeks + 1)]
    table_data = [header]

    for student in students:
        weekly_attendance = student.get("weekly_attendance", [])
        status_by_week = {entry["week"]: entry["status"] for entry in weekly_attendance}
        row = [student.get(c["id"], "") for c in columns]
        for week in range(1, num_weeks + 1):
            row.append(status_by_week.get(week, "Unclear"))
        table_data.append(row)

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
    ]))
    elements.append(table)
    doc.build(elements)

    visible_pdf_bytes = buffer.getvalue()
    buffer.close()

    reader = PdfReader(BytesIO(visible_pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    json_data = json.dumps({"students": students, "config": config})
    writer.add_metadata({CUSTOM_METADATA_KEY: json_data})

    output_buffer = BytesIO()
    writer.write(output_buffer)
    final_pdf_bytes = output_buffer.getvalue()
    output_buffer.close()

    return final_pdf_bytes


def extract_data_from_pdf(pdf_bytes):
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as e:
        return {"success": False, "data": None, "error": f"Could not read the PDF file: {e}"}

    metadata = reader.metadata
    if not metadata or CUSTOM_METADATA_KEY not in metadata:
        return {
            "success": False,
            "data": None,
            "error": "This PDF doesn't contain SnapAttend attendance data. "
                     "Only PDFs previously downloaded from SnapAttend can be re-imported this way.",
        }

    raw_json = metadata[CUSTOM_METADATA_KEY]

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return {"success": False, "data": None, "error": "The hidden data in this PDF was corrupted or unreadable."}

    return {"success": True, "data": parsed, "error": None}