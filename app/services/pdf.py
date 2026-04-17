
import io
import os
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import KeepTogether

# ── Brand colours ─────────────────────────────────────────────────────────────
NIT_DARK_BLUE  = colors.HexColor("#003366")   # deep navy header
NIT_MID_BLUE   = colors.HexColor("#0055A5")   # accent / column headers
NIT_LIGHT_BLUE = colors.HexColor("#D6E4F7")   # header row fill
NIT_LUNCH_BG   = colors.HexColor("#E8E8E8")   # lunch column
NIT_ROW_ALT    = colors.HexColor("#F4F8FD")   # alternating row tint
NIT_BORDER     = colors.HexColor("#AABFD4")   # grid lines
NIT_TEXT_DARK  = colors.HexColor("#1A1A2E")   # body text
NIT_GOLD       = colors.HexColor("#C8960C")   # thin accent rule under header


def build_timetable(data):
    slots = ["period1", "period2", "period3", "period4",
             "period5", "period6", "period7", "period8"]
    days  = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    timetable = {day: [""] * 9 for day in days}

    for doc in data:
        day  = doc.get("day")
        slot = doc.get("slot")
        if day not in timetable or slot not in slots:
            continue
        db_index = slots.index(slot)
        index    = db_index if db_index < 4 else db_index + 1
        slot_data = doc.get("slotData", [])
        if not slot_data:
            continue
        entry   = slot_data[0]
        subject = entry.get("subject", "")
        room    = entry.get("room", "")
        timetable[day][index] = f"{subject}\n({room})"

    for day in timetable:
        timetable[day][4] = "LUNCH"

    return timetable


def generate_pdf_bytes(timetable, title_name) -> bytes:
    buffer = io.BytesIO()

    PAGE_W, PAGE_H = landscape(A4)
    MARGIN = 18 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=14 * mm,  bottomMargin=14 * mm,
    )

    # ── Styles ────────────────────────────────────────────────────────────────
    inst_style = ParagraphStyle(
        "inst",
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=NIT_DARK_BLUE,
        alignment=TA_CENTER,
        spaceAfter=2,
        leading=18,
    )
    sub_style = ParagraphStyle(
        "sub",
        fontName="Helvetica",
        fontSize=9,
        textColor=NIT_MID_BLUE,
        alignment=TA_CENTER,
        spaceAfter=0,
        leading=12,
    )
    title_style = ParagraphStyle(
        "tit",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=NIT_DARK_BLUE,
        alignment=TA_CENTER,
        spaceBefore=6,
        spaceAfter=4,
        leading=14,
    )

    elements = []

    # ── Header: logo + institute name side-by-side ────────────────────────────
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nit_logo.png")
    logo_exists = os.path.exists(logo_path)

    header_data = []
    if logo_exists:
        logo = Image(logo_path, width=18 * mm, height=18 * mm)
        text_cell = [
            Paragraph("Dr B R Ambedkar National Institute of Technology, Jalandhar", inst_style),
        ]
        header_data = [[logo, text_cell, logo]]  # logo on both sides for symmetry
        header_table = Table(header_data, colWidths=[22 * mm, PAGE_W - 2 * MARGIN - 44 * mm, 22 * mm])
        header_table.setStyle(TableStyle([
            ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",   (0, 0), (0,  0),  "RIGHT"),
            ("ALIGN",   (2, 0), (2,  0),  "LEFT"),
            ("ALIGN",   (1, 0), (1,  0),  "CENTER"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(header_table)
    else:
        elements.append(Paragraph(
            "Dr B R Ambedkar National Institute of Technology, Jalandhar", inst_style))


    # Gold divider line
    elements.append(Spacer(1, 3))
    elements.append(HRFlowable(width="100%", thickness=2, color=NIT_GOLD, spaceAfter=2))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=NIT_MID_BLUE, spaceAfter=4))

    # Timetable title
    elements.append(Paragraph(f"Timetable &nbsp; — &nbsp; {title_name.title()}", title_style))
    elements.append(Spacer(1, 4))

    # ── Table ─────────────────────────────────────────────────────────────────
    # Build header row as Paragraphs for rich styling
    header_cell_style = ParagraphStyle(
        "hcell",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        textColor=colors.white,
        alignment=TA_CENTER,
        leading=10,
    )
    day_cell_style = ParagraphStyle(
        "dcell",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=NIT_DARK_BLUE,
        alignment=TA_CENTER,
        leading=11,
    )
    content_style = ParagraphStyle(
        "ccell",
        fontName="Helvetica",
        fontSize=7.5,
        textColor=NIT_TEXT_DARK,
        alignment=TA_CENTER,
        leading=10,
    )
    lunch_style = ParagraphStyle(
        "lunch",
        fontName="Helvetica-BoldOblique",
        fontSize=8,
        textColor=colors.HexColor("#666666"),
        alignment=TA_CENTER,
        leading=10,
    )

    header_labels = [
        ("Day /\nPeriod", ""),
        ("P1", "8:30–9:25"),
        ("P2", "9:30–10:25"),
        ("P3", "10:30–11:25"),
        ("P4", "11:30–12:25"),
        ("LUNCH", "12:30–1:25"),
        ("P5", "1:30–2:25"),
        ("P6", "2:30–3:25"),
        ("P7", "3:30–4:25"),
        ("P8", "4:30–5:25"),
    ]

    header_row = []
    for label, time in header_labels:
        txt = f"<b>{label}</b>"
        if time:
            txt += f"<br/><font size='6.5'>{time}</font>"
        header_row.append(Paragraph(txt, header_cell_style))

    table_data = [header_row]
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for i, day in enumerate(days_order):
        periods = timetable[day]
        row = [Paragraph(day, day_cell_style)]
        for j, cell in enumerate(periods):
            if cell == "LUNCH":
                row.append(Paragraph("LUNCH", lunch_style))
            elif cell:
                row.append(Paragraph(cell.replace("\n", "<br/>"), content_style))
            else:
                row.append("")
        table_data.append(row)

    # Column widths: day col + 9 period cols
    available_w = PAGE_W - 2 * MARGIN
    day_col_w   = 22 * mm
    lunch_col_w = 18 * mm
    period_col_w = (available_w - day_col_w - lunch_col_w) / 8

    col_widths = [day_col_w] + [period_col_w] * 4 + [lunch_col_w] + [period_col_w] * 4

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Build row-by-row alternating background commands
    row_cmds = []
    for r in range(1, 6):
        bg = NIT_ROW_ALT if r % 2 == 0 else colors.white
        row_cmds.append(("BACKGROUND", (0, r), (-1, r), bg))

    table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0),  NIT_MID_BLUE),
        ("BACKGROUND",    (0, 0), (0,  0),  NIT_DARK_BLUE),

        # Lunch column
        ("BACKGROUND",    (5, 0), (5, -1),  NIT_LUNCH_BG),
        ("BACKGROUND",    (5, 0), (5,  0),  colors.HexColor("#556B7D")),

        # Day column body
        ("BACKGROUND",    (0, 1), (0, -1),  NIT_LIGHT_BLUE),

        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.4, NIT_BORDER),
        ("LINEBELOW",     (0, 0), (-1,  0), 1.5, NIT_DARK_BLUE),
        ("LINEAFTER",     (0, 0), (0,  -1), 1.0, NIT_BORDER),

        # Alignment
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),

        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),

        # Row heights
        ("ROWHEIGHT",     (0, 0), (-1,  0), 28),
        ("ROWHEIGHT",     (0, 1), (-1, -1), 38),

        *row_cmds,
    ]))

    elements.append(table)

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 5))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=NIT_BORDER))
    footer_style = ParagraphStyle(
        "footer",
        fontName="Helvetica",
        fontSize=7,
        textColor=colors.HexColor("#888888"),
        alignment=TA_CENTER,
        spaceBefore=3,
    )
    elements.append(Paragraph(
        "Dr B R Ambedkar NIT Jalandhar  •  Auto-generated Timetable  •  For internal use only",
        footer_style
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# ── Quick local test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = {
        "Monday":    ["", "AA\n(ALT-0-2)", "", "Tut-MA-I(B3a)\n(ALT-0-2)", "LUNCH", "", "", "Maths-I\n(SB-3)", ""],
        "Tuesday":   ["", "Tut-MA-I(B3b)\n(ALT-0-2)", "", "", "LUNCH", "", "AA\n(PHY-209)", "", ""],
        "Wednesday": ["", "Tut-MA-I(B3c)\n(ALT-0-2)", "", "", "LUNCH", "", "AA\n(PHY-209)", "", ""],
        "Thursday":  ["", "", "AA\n(ALT-3-3)", "", "LUNCH", "", "", "Maths-I\n(SB-3)", ""],
        "Friday":    ["", "", "", "", "LUNCH", "Maths-I\n(SB-3)", "", "", ""],
    }
    data = generate_pdf_bytes(sample, "Vipin Kumar")
    with open("/home/claude/test_timetable.pdf", "wb") as f:
        f.write(data)
    print("PDF written to test_timetable.pdf")