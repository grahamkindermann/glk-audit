"""
report.py: PDF generation for the Structural Advantage Business Audit.

Pure function interface:
    build_pdf(audit_result, firmographics, output_path, mode=None) -> output_path

No Streamlit imports. ReportLab for layout, matplotlib (Agg backend) for the
radar chart rendered to an in-memory PNG. All content (questions, dimension
names, CTA, brand, band narratives) is pulled from rubric.py.

Run `python3 report.py` from inside glk-audit/ to regenerate the two sample
PDFs checked in alongside this file.
"""

from datetime import date
from io import BytesIO
from math import pi
from xml.sax.saxutils import escape as xml_escape

import matplotlib
matplotlib.use("Agg")  # must precede pyplot import
import matplotlib.pyplot as plt  # noqa: E402

from reportlab.lib.colors import Color, HexColor  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import LETTER  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from rubric import (  # noqa: E402
    BAND_NARRATIVE,
    BENCHMARKS,
    BRAND,
    CTA,
    DIMENSIONS,
    INSUFFICIENT_DATA_LABEL,
    MODE as DEFAULT_MODE,
    RUBRIC_VERSION,
)


# ---------------------------------------------------------------------------
# Brand colors
# Single source of truth for the PDF palette. Will migrate to branding.py in
# v2 when the whitelabel hook lands; until then, edit this block to rebrand.
# ---------------------------------------------------------------------------
NAVY            = HexColor("#0B1F3A")
OFFWHITE        = HexColor("#F5F1E8")
CHARCOAL        = HexColor("#2B2B2B")
RISK_RED        = HexColor("#8B2E2E")
STRENGTH_GREEN  = HexColor("#2E5D3A")
RULE_GRAY       = Color(0.82, 0.82, 0.82)

NAVY_HEX            = "#0B1F3A"
OFFWHITE_HEX        = "#F5F1E8"


# ---------------------------------------------------------------------------
# XML-escape helper for anything that flows into a ReportLab Paragraph.
# Dimension names contain "&" (e.g. "Personnel & Org") which must be escaped.
# ---------------------------------------------------------------------------

def _esc(text):
    if text is None:
        return ""
    return xml_escape(str(text))


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------

def _build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["wordmark_cover"] = ParagraphStyle(
        "wordmark_cover", parent=base["Normal"],
        fontName="Times-Roman", fontSize=26, textColor=NAVY,
        alignment=TA_CENTER, leading=32,
    )
    styles["cover_subtitle"] = ParagraphStyle(
        "cover_subtitle", parent=base["Normal"],
        fontName="Helvetica", fontSize=13, textColor=CHARCOAL,
        alignment=TA_CENTER, leading=18,
    )
    styles["cover_company"] = ParagraphStyle(
        "cover_company", parent=base["Normal"],
        fontName="Times-Roman", fontSize=18, textColor=NAVY,
        alignment=TA_CENTER, leading=22,
    )
    styles["cover_meta"] = ParagraphStyle(
        "cover_meta", parent=base["Normal"],
        fontName="Helvetica", fontSize=11, textColor=CHARCOAL,
        alignment=TA_CENTER, leading=15,
    )
    styles["h1"] = ParagraphStyle(
        "h1", parent=base["Normal"],
        fontName="Times-Roman", fontSize=22, textColor=NAVY,
        leading=28, spaceAfter=10,
    )
    styles["h2"] = ParagraphStyle(
        "h2", parent=base["Normal"],
        fontName="Times-Roman", fontSize=16, textColor=NAVY,
        leading=22, spaceBefore=14, spaceAfter=6,
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontName="Helvetica", fontSize=10, textColor=CHARCOAL, leading=14,
    )
    styles["body_bold"] = ParagraphStyle(
        "body_bold", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=10, textColor=CHARCOAL, leading=14,
    )
    styles["question"] = ParagraphStyle(
        "question", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=11, textColor=CHARCOAL,
        leading=14, spaceAfter=3,
    )
    styles["small"] = ParagraphStyle(
        "small", parent=base["Normal"],
        fontName="Helvetica", fontSize=8, textColor=CHARCOAL, leading=10,
    )
    styles["small_caps"] = ParagraphStyle(
        "small_caps", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=8, textColor=NAVY,
        leading=10, spaceAfter=2,
    )
    styles["big_score"] = ParagraphStyle(
        "big_score", parent=base["Normal"],
        fontName="Times-Roman", fontSize=72, textColor=NAVY,
        leading=80, alignment=TA_CENTER,
    )
    styles["band_label"] = ParagraphStyle(
        "band_label", parent=base["Normal"],
        fontName="Times-Roman", fontSize=18, textColor=CHARCOAL,
        leading=22, alignment=TA_CENTER, spaceAfter=10,
    )
    styles["exec_narrative"] = ParagraphStyle(
        "exec_narrative", parent=base["Normal"],
        fontName="Helvetica", fontSize=11, textColor=CHARCOAL,
        leading=15, alignment=TA_CENTER, spaceAfter=6,
    )
    styles["cta_headline"] = ParagraphStyle(
        "cta_headline", parent=base["Normal"],
        fontName="Times-Roman", fontSize=18, textColor=NAVY,
        leading=24, alignment=TA_CENTER, spaceAfter=12,
    )
    styles["upsell_headline"] = ParagraphStyle(
        "upsell_headline", parent=base["Normal"],
        fontName="Times-Roman", fontSize=22, textColor=NAVY,
        leading=28, alignment=TA_CENTER, spaceAfter=8,
    )
    styles["upsell_body"] = ParagraphStyle(
        "upsell_body", parent=base["Normal"],
        fontName="Helvetica", fontSize=10, textColor=CHARCOAL,
        leading=14, alignment=TA_CENTER, spaceAfter=14,
    )
    styles["cta_button"] = ParagraphStyle(
        "cta_button", parent=base["Normal"],
        fontName="Helvetica-Bold", fontSize=12, textColor=OFFWHITE,
        leading=16, alignment=TA_CENTER,
    )
    styles["table_cell"] = ParagraphStyle(
        "table_cell", parent=base["Normal"],
        fontName="Helvetica", fontSize=9, textColor=CHARCOAL, leading=11,
    )
    styles["cta_secondary"] = ParagraphStyle(
        "cta_secondary", parent=base["Normal"],
        fontName="Helvetica", fontSize=10, textColor=NAVY,
        leading=14, alignment=TA_CENTER, spaceBefore=12,
    )
    styles["back_prepared"] = ParagraphStyle(
        "back_prepared", parent=base["Normal"],
        fontName="Helvetica", fontSize=10, textColor=CHARCOAL,
        leading=14, alignment=TA_CENTER,
    )
    return styles


# ---------------------------------------------------------------------------
# Radar chart
# ---------------------------------------------------------------------------

def _build_radar(audit_result):
    """Render a 6-axis radar chart to an in-memory PNG and return an Image."""
    dims = list(audit_result["dimensions"].values())
    labels = [d["name"] for d in dims]
    # Insufficient-Data dimensions plot as 0 on the radar; the dimension
    # table is the authoritative presentation (shows "-" and the label).
    values = [d["score"] if d["score"] is not None else 0 for d in dims]

    n = len(values)
    angles = [i * 2 * pi / n for i in range(n)]
    angles_closed = angles + [angles[0]]
    values_closed = values + [values[0]]

    fig, ax = plt.subplots(figsize=(5.0, 5.0), subplot_kw=dict(polar=True))
    ax.set_theta_offset(pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7, color="#2B2B2B")
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=9, color="#0B1F3A")
    ax.plot(angles_closed, values_closed, color=NAVY_HEX, linewidth=1.6)
    ax.fill(angles_closed, values_closed, color=NAVY_HEX, alpha=0.3)
    ax.grid(color="#CCCCCC", linewidth=0.5)
    ax.spines["polar"].set_color("#CCCCCC")

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    # 4.0-inch radar (down from 4.8) leaves enough vertical room for the
    # Per-Dimension Scores table to stay on the same page as the executive
    # summary. With the old 4.8-inch chart, only the first dimension row
    # fit on page 2 and the remaining five were orphaned to page 3.
    return Image(buf, width=4.0 * inch, height=4.0 * inch)


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------

def _cover_page(firmographics, mode, styles):
    elements = []

    elements.append(Spacer(1, 2.0 * inch))

    # Letter-spaced wordmark: insert non-breaking spaces between each char.
    chars = list(BRAND["wordmark"])
    wordmark_text = "&nbsp;".join(_esc(c) for c in chars)
    elements.append(Paragraph(wordmark_text, styles["wordmark_cover"]))
    elements.append(Spacer(1, 0.25 * inch))

    subtitle = BRAND["cover_subtitle"].get(mode, "")
    elements.append(Paragraph(_esc(subtitle), styles["cover_subtitle"]))

    elements.append(Spacer(1, 1.6 * inch))

    company = (firmographics.get("company_name") or "").strip() or "-"
    revenue = firmographics.get("revenue_band") or "-"
    industry = firmographics.get("industry") or "-"

    elements.append(Paragraph(_esc(company), styles["cover_company"]))
    elements.append(Spacer(1, 0.08 * inch))
    elements.append(Paragraph(
        f"{_esc(revenue)} &nbsp;·&nbsp; {_esc(industry)}",
        styles["cover_meta"],
    ))

    elements.append(Spacer(1, 0.8 * inch))
    today = date.today().isoformat()
    elements.append(Paragraph(_esc(today), styles["cover_meta"]))
    elements.append(Paragraph(f"Rubric v{_esc(RUBRIC_VERSION)}", styles["small"]))

    return elements


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------

def _exec_summary(audit_result, styles):
    elements = []
    elements.append(Paragraph("Executive Summary", styles["h1"]))

    overall = audit_result["overall"]
    score_str = f"{overall['score']:.0f}" if overall["score"] is not None else "-"
    band_label = overall["band_label"] or INSUFFICIENT_DATA_LABEL
    band_id = overall.get("band_id")

    elements.append(Paragraph(score_str, styles["big_score"]))
    elements.append(Paragraph(_esc(band_label.upper()), styles["band_label"]))

    narrative = BAND_NARRATIVE.get(band_id, "") if band_id else ""
    if narrative:
        elements.append(Paragraph(_esc(narrative), styles["exec_narrative"]))

    return elements


# ---------------------------------------------------------------------------
# Per-dimension table
# ---------------------------------------------------------------------------

def _dimension_table(audit_result, styles):
    """Return the Per-Dimension Scores block as a single flowable wrapped in
    KeepTogether so the header never gets orphaned from the table rows.
    Returned as a list to preserve the existing story.extend(...) caller
    contract in build_pdf."""
    header_para = Paragraph("Per-Dimension Scores", styles["h2"])

    header = ["Dimension", "Score", "Band"]
    rows = [header]
    for _dim_id, dim in audit_result["dimensions"].items():
        if dim["insufficient"] or dim["score"] is None:
            score_str = "-"
            band_str = INSUFFICIENT_DATA_LABEL
        else:
            score_str = f"{dim['score']:.0f}"
            band_str = dim["band_label"]
        rows.append([dim["name"], score_str, band_str])

    tbl = Table(rows, colWidths=[3.2 * inch, 0.9 * inch, 1.9 * inch])
    tbl.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",   (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",   (0, 1), (-1, -1), CHARCOAL),
        ("ALIGN",       (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW",   (0, 0), (-1, 0), 1.0, NAVY),
        ("LINEBELOW",   (0, 1), (-1, -2), 0.25, RULE_GRAY),
        ("LINEBELOW",   (0, -1), (-1, -1), 0.5, RULE_GRAY),
        ("TOPPADDING",  (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [KeepTogether([header_para, tbl])]
    return elements


# ---------------------------------------------------------------------------
# Accent blocks (risks and opportunities)
# ---------------------------------------------------------------------------

def _accent_block(index, item, body_key, accent_color, styles):
    dim_para = Paragraph(
        f"{index}. {_esc(item['dimension_name'].upper())}",
        styles["small_caps"],
    )
    q_para = Paragraph(_esc(item["question_text"]), styles["question"])
    body_para = Paragraph(_esc(item[body_key]), styles["body"])

    inner = [dim_para, q_para, body_para]
    tbl = Table(
        [[" ", inner]],
        colWidths=[0.1 * inch, 6.0 * inch],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), accent_color),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING",  (1, 0), (1, 0), 12),
        ("RIGHTPADDING", (1, 0), (1, 0), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def _risks_section(audit_result, styles):
    elements = []
    elements.append(Paragraph("Top Risks", styles["h1"]))
    risks = audit_result["risks"]
    if not risks:
        elements.append(Paragraph("No risks surfaced.", styles["body"]))
        return elements
    for i, r in enumerate(risks, 1):
        elements.append(_accent_block(i, r, "risk_copy", RISK_RED, styles))
        elements.append(Spacer(1, 0.15 * inch))
    return elements


def _opportunities_section(audit_result, styles):
    elements = []
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph("Top Opportunities", styles["h1"]))
    opps = audit_result["opportunities"]
    if not opps:
        elements.append(Paragraph(
            "No mid-band opportunities surfaced under this input.",
            styles["body"],
        ))
        return elements
    for i, o in enumerate(opps, 1):
        elements.append(_accent_block(i, o, "opportunity_copy", STRENGTH_GREEN, styles))
        elements.append(Spacer(1, 0.15 * inch))
    return elements


def _recommendations_section(audit_result, styles):
    elements = []
    # Gather recommendations from both risks and opportunities
    steps = []
    for r in audit_result["risks"]:
        rec = r.get("recommendation", "")
        if rec:
            steps.append({"dimension_name": r["dimension_name"], "recommendation": rec})
    for o in audit_result["opportunities"]:
        rec = o.get("recommendation", "")
        if rec:
            steps.append({"dimension_name": o["dimension_name"], "recommendation": rec})
    if not steps:
        return elements
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph("Recommended Next Steps", styles["h2"]))
    for i, s in enumerate(steps, 1):
        elements.append(Paragraph(
            f"{i}. {_esc(s['dimension_name'])}",
            styles["body_bold"],
        ))
        elements.append(Paragraph(_esc(s["recommendation"]), styles["body"]))
        elements.append(Spacer(1, 0.1 * inch))
    return elements


# ---------------------------------------------------------------------------
# How You Compare (benchmark table)
# ---------------------------------------------------------------------------

BENCHMARK_GREEN = HexColor("#2E5D3A")
BENCHMARK_YELLOW = HexColor("#8B7A2E")
BENCHMARK_RED = HexColor("#8B2E2E")

def _benchmark_section(answers, industry, styles):
    elements = []
    if not industry or not answers:
        return elements

    rows_data = []
    for dim in DIMENSIONS:
        for q in dim["questions"]:
            if q["type"] not in ("number", "percent"):
                continue
            val = answers.get(q["id"])
            if val is None or val == "N/A":
                continue
            bm = BENCHMARKS.get((industry, q["id"]))
            if not bm:
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            lib = q.get("lower_is_better", False)
            suffix = "%" if q["type"] == "percent" else ""
            if lib:
                if v <= bm["p25"]:
                    grade, color = "Top quartile", BENCHMARK_GREEN
                elif v <= bm["p50"]:
                    grade, color = "Above median", BENCHMARK_GREEN
                elif v <= bm["p75"]:
                    grade, color = "Below median", BENCHMARK_YELLOW
                else:
                    grade, color = "Bottom quartile", BENCHMARK_RED
            else:
                if v >= bm["p75"]:
                    grade, color = "Top quartile", BENCHMARK_GREEN
                elif v >= bm["p50"]:
                    grade, color = "Above median", BENCHMARK_GREEN
                elif v >= bm["p25"]:
                    grade, color = "Below median", BENCHMARK_YELLOW
                else:
                    grade, color = "Bottom quartile", BENCHMARK_RED
            rows_data.append((q["text"], f"{v:g}{suffix}",
                              f"{bm['p50']}{suffix}",
                              f"{bm['p25'] if lib else bm['p75']}{suffix}",
                              grade, color))

    if not rows_data:
        return elements

    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("How You Compare", styles["h1"]))
    elements.append(Paragraph(
        f"Benchmarks for {_esc(industry)}", styles["body"]))
    elements.append(Spacer(1, 0.1 * inch))

    header = ["Metric", "Yours", "Median", "Top Quartile", "Standing"]
    tbl_rows = [header]
    for metric, yours, med, top, grade, _color in rows_data:
        # Wrap the metric cell in a Paragraph so long question text (e.g.
        # "Number of workflows with AI augmentation in production") line-
        # wraps inside the column instead of overflowing into "Yours".
        metric_para = Paragraph(_esc(metric), styles["table_cell"])
        tbl_rows.append([metric_para, yours, med, top, grade])

    col_widths = [3.0 * inch, 0.7 * inch, 0.7 * inch, 0.95 * inch, 1.15 * inch]
    tbl = Table(tbl_rows, colWidths=col_widths)

    style_commands = [
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",   (0, 1), (-1, -1), CHARCOAL),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",       (0, 0), (0, -1), "LEFT"),
        # Center-align numeric/standing cells vertically so they line up
        # visually with the wrapped metric Paragraph, which can occupy 1-2
        # lines depending on question length.
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",   (0, 0), (-1, 0), 1.0, NAVY),
        ("LINEBELOW",   (0, 1), (-1, -2), 0.25, RULE_GRAY),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    # Color-code the "Standing" column
    for i, (_m, _y, _med, _t, _g, color) in enumerate(rows_data):
        row_idx = i + 1
        style_commands.append(("TEXTCOLOR", (4, row_idx), (4, row_idx), color))

    tbl.setStyle(TableStyle(style_commands))
    elements.append(tbl)
    return elements


# ---------------------------------------------------------------------------
# 30/60/90 action plan (advisory mode)
# ---------------------------------------------------------------------------

def _action_plan_section(audit_result, styles):
    elements = []
    action_plan = audit_result.get("action_plan")
    if not action_plan:
        return elements

    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("30 / 60 / 90 Day Action Plan", styles["h1"]))

    for phase, label in [("30_day", "30 Days: Quick Wins"),
                          ("60_day", "60 Days: Systemic Fixes"),
                          ("90_day", "90 Days: Strategic Initiatives")]:
        items = action_plan.get(phase, [])
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(_esc(label), styles["h2"]))
        if not items:
            elements.append(Paragraph("No items for this phase.", styles["body"]))
        else:
            for item in items:
                elements.append(Paragraph(
                    f"\u2022  <b>{_esc(item['dimension_name'])}</b>: {_esc(item['action'])}",
                    styles["body"],
                ))
                elements.append(Spacer(1, 0.06 * inch))

    return elements


# ---------------------------------------------------------------------------
# CTA section
# ---------------------------------------------------------------------------

def _cta_section(mode, styles):
    elements = []
    cta = CTA.get(mode, {})
    if not cta:
        return elements

    elements.append(Spacer(1, 0.4 * inch))

    # Upsell block (free/lead_magnet PDFs only): lead with the Full Report
    # offer, then separate with a horizontal rule, then show the secondary
    # "book a call" CTA. This converts readers on the highest-intent page
    # of the free deliverable instead of routing everyone to a solo call.
    upsell_label = cta.get("upsell_label")
    upsell_url = cta.get("upsell_url")
    if upsell_label and upsell_url:
        upsell_headline = cta.get("upsell_headline", "")
        upsell_body = cta.get("upsell_body", "")
        if upsell_headline:
            elements.append(Paragraph(_esc(upsell_headline), styles["upsell_headline"]))
        if upsell_body:
            elements.append(Paragraph(_esc(upsell_body), styles["upsell_body"]))

        upsell_markup = (
            f'<link href="{_esc(upsell_url)}" color="{OFFWHITE_HEX}">'
            f'{_esc(upsell_label)}'
            f'</link>'
        )
        upsell_button_para = Paragraph(upsell_markup, styles["cta_button"])
        upsell_btn_tbl = Table([[upsell_button_para]], colWidths=[3.2 * inch])
        upsell_btn_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        upsell_outer = Table([[upsell_btn_tbl]], colWidths=[6.5 * inch])
        upsell_outer.setStyle(TableStyle([
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(upsell_outer)

        # Rule + breathing room before the secondary CTA
        elements.append(Spacer(1, 0.35 * inch))
        rule = Table([[""]], colWidths=[4.0 * inch], rowHeights=[0.01 * inch])
        rule.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.5, RULE_GRAY),
        ]))
        rule_outer = Table([[rule]], colWidths=[6.5 * inch])
        rule_outer.setStyle(TableStyle([
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(rule_outer)
        elements.append(Spacer(1, 0.25 * inch))

    elements.append(Paragraph(_esc(cta.get("headline", "")), styles["cta_headline"]))

    primary_url = cta.get("primary_url", "")
    primary_label = cta.get("primary_label", "")
    button_markup = (
        f'<link href="{_esc(primary_url)}" color="{OFFWHITE_HEX}">'
        f'{_esc(primary_label)}'
        f'</link>'
    )
    button_para = Paragraph(button_markup, styles["cta_button"])

    btn_tbl = Table([[button_para]], colWidths=[2.8 * inch])
    btn_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))

    # Outer table to horizontally center the button on the page width.
    outer = Table([[btn_tbl]], colWidths=[6.5 * inch])
    outer.setStyle(TableStyle([
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(outer)

    secondary_url = cta.get("secondary_url")
    secondary_label = cta.get("secondary_label")
    if secondary_url and secondary_label:
        secondary_markup = (
            f'<link href="{_esc(secondary_url)}" color="{NAVY_HEX}">'
            f'{_esc(secondary_label)}'
            f'</link>'
        )
        elements.append(Paragraph(secondary_markup, styles["cta_secondary"]))

    return elements


# ---------------------------------------------------------------------------
# Back page
# ---------------------------------------------------------------------------

def _back_page(styles):
    elements = []
    elements.append(Spacer(1, 3.5 * inch))
    elements.append(Paragraph(_esc(BRAND["prepared_by"]), styles["back_prepared"]))
    elements.append(Spacer(1, 0.3 * inch))
    today = date.today().isoformat()
    footer = f"Rubric v{_esc(RUBRIC_VERSION)} · generated {_esc(today)}"
    elements.append(Paragraph(footer, styles["small"]))
    return elements


# ---------------------------------------------------------------------------
# AI-generated sections (Phase 3)
# ---------------------------------------------------------------------------

def _ai_executive_summary_section(ai_recs, styles):
    elements = []
    summary = ai_recs.get("executive_summary", "")
    if not summary:
        return elements
    elements.append(Paragraph("Executive Summary", styles["h1"]))
    elements.append(Spacer(1, 0.1 * inch))
    # Split paragraphs for proper spacing
    for para in summary.split("\n\n"):
        para = para.strip()
        if para:
            elements.append(Paragraph(_esc(para), styles["body"]))
            elements.append(Spacer(1, 0.08 * inch))
    return elements


def _ai_dimension_analyses_section(ai_recs, styles):
    elements = []
    analyses = ai_recs.get("dimension_analyses", [])
    if not analyses:
        return elements
    elements.append(Paragraph("Detailed Analysis", styles["h1"]))
    elements.append(Spacer(1, 0.1 * inch))
    for da in analyses:
        elements.append(Paragraph(_esc(da.get("dimension", "")), styles["h2"]))
        analysis = da.get("analysis", "")
        if analysis:
            elements.append(Paragraph(_esc(analysis), styles["body"]))
            elements.append(Spacer(1, 0.06 * inch))
        for rec in da.get("recommendations", []):
            elements.append(Paragraph(
                f"\u2022  {_esc(rec)}", styles["body"],
            ))
            elements.append(Spacer(1, 0.04 * inch))
        elements.append(Spacer(1, 0.1 * inch))
    return elements


def _ai_action_plan_section(ai_recs, styles):
    elements = []
    plan = ai_recs.get("action_plan", {})
    if not plan:
        return elements
    elements.append(Paragraph("30 / 60 / 90 Day Action Plan", styles["h1"]))
    elements.append(Spacer(1, 0.1 * inch))

    for phase, label in [("30_day", "30 Days: Quick Wins"),
                          ("60_day", "60 Days: Systemic Fixes"),
                          ("90_day", "90 Days: Strategic Initiatives")]:
        items = plan.get(phase, [])
        elements.append(Paragraph(_esc(label), styles["h2"]))
        if not items:
            elements.append(Paragraph("No items for this phase.", styles["body"]))
        else:
            for item in items:
                action = item.get("action", "")
                owner = item.get("owner", "")
                outcome = item.get("expected_outcome", "")
                elements.append(Paragraph(
                    f"\u2022  <b>{_esc(action)}</b>", styles["body"],
                ))
                if owner or outcome:
                    elements.append(Paragraph(
                        f"    Owner: {_esc(owner)} · Expected: {_esc(outcome)}",
                        styles["small"],
                    ))
                elements.append(Spacer(1, 0.06 * inch))
        elements.append(Spacer(1, 0.1 * inch))
    return elements


def _ai_roi_section(ai_recs, styles):
    elements = []
    estimates = ai_recs.get("roi_estimates", [])
    if not estimates:
        return elements
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph("Estimated ROI: Top Recommendations", styles["h1"]))
    elements.append(Spacer(1, 0.1 * inch))

    header = ["Recommendation", "Estimated Impact", "Confidence"]
    tbl_rows = [header]
    for e in estimates:
        tbl_rows.append([
            e.get("recommendation", ""),
            e.get("estimated_impact", ""),
            e.get("confidence", "").title(),
        ])

    col_widths = [3.0 * inch, 2.3 * inch, 1.0 * inch]
    tbl = Table(tbl_rows, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",   (0, 1), (-1, -1), CHARCOAL),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",       (0, 0), (0, -1), "LEFT"),
        ("LINEBELOW",   (0, 0), (-1, 0), 1.0, NAVY),
        ("LINEBELOW",   (0, 1), (-1, -2), 0.25, RULE_GRAY),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(tbl)
    return elements


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def _progress_section(audit_result, previous_audit, styles):
    """Render a 'Progress Since Last Audit' section with delta scores."""
    elements = []
    if not previous_audit:
        return elements

    prev_dims = previous_audit.get("dimension_scores") or {}
    prev_overall = previous_audit.get("overall_score")
    curr_overall = audit_result.get("overall", {}).get("score")
    prev_date = (previous_audit.get("created_at") or "")[:10]

    if not prev_dims and prev_overall is None:
        return elements

    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Progress Since Last Audit", styles["h1"]))
    if prev_date:
        elements.append(Paragraph(
            f"Compared to audit on {_esc(prev_date)}", styles["body"]))
    elements.append(Spacer(1, 0.1 * inch))

    # Overall delta
    if curr_overall is not None and prev_overall is not None:
        delta = curr_overall - prev_overall
        arrow = "\u2191" if delta > 0 else ("\u2193" if delta < 0 else "\u2192")
        elements.append(Paragraph(
            f"Overall: {curr_overall:.0f} ({arrow} {delta:+.0f} from {prev_overall:.0f})",
            styles["body_bold"],
        ))
        elements.append(Spacer(1, 0.1 * inch))

    # Per-dimension deltas
    header = ["Dimension", "Current", "Previous", "Change"]
    rows = [header]
    curr_dims = audit_result.get("dimensions", {})
    for dim_id, dim in curr_dims.items():
        curr_s = dim.get("score")
        prev = prev_dims.get(dim_id, {})
        prev_s = prev.get("score")
        if curr_s is not None and prev_s is not None:
            delta = curr_s - prev_s
            arrow = "\u2191" if delta > 0 else ("\u2193" if delta < 0 else "\u2192")
            rows.append([
                dim.get("name", dim_id),
                f"{curr_s:.0f}",
                f"{prev_s:.0f}",
                f"{arrow} {delta:+.0f}",
            ])
        elif curr_s is not None:
            rows.append([dim.get("name", dim_id), f"{curr_s:.0f}", "N/A", "N/A"])

    if len(rows) > 1:
        tbl = Table(rows, colWidths=[2.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
        tbl.setStyle(TableStyle([
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 0), (-1, -1), 10),
            ("TEXTCOLOR",   (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",   (0, 1), (-1, -1), CHARCOAL),
            ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
            ("ALIGN",       (0, 0), (0, -1), "LEFT"),
            ("LINEBELOW",   (0, 0), (-1, 0), 1.0, NAVY),
            ("LINEBELOW",   (0, 1), (-1, -2), 0.25, RULE_GRAY),
            ("TOPPADDING",  (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(tbl)

    return elements


def build_pdf(audit_result, firmographics, output_path, mode=None, answers=None,
              ai_recommendations=None, previous_audit=None):
    """Build the audit PDF.

    audit_result:       dict returned by scoring.run_audit()
    firmographics:      dict from Streamlit session_state.firmographics
    output_path:        str or Path; PDF written here
    mode:               "lead_magnet" | "advisory" | None (defaults to rubric.MODE)
    answers:            flat {question_id: answer} dict (for benchmark comparison)
    ai_recommendations: dict from recommendations.generate_recommendations() or None
    previous_audit:     dict with previous audit data for delta comparison, or None

    Returns: output_path (for chaining).
    """
    use_mode = mode if mode is not None else DEFAULT_MODE
    firm = firmographics or {}
    answers = answers or {}
    ai_recs = ai_recommendations

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"{BRAND['wordmark']}, {BRAND['cover_subtitle'].get(use_mode, '')}",
        author="GLK Holdings LLC",
    )

    styles = _build_styles()
    story = []

    # Cover
    story.extend(_cover_page(firm, use_mode, styles))
    story.append(PageBreak())

    # AI executive summary (if available, advisory mode)
    if ai_recs and use_mode == "advisory":
        story.extend(_ai_executive_summary_section(ai_recs, styles))
        story.append(PageBreak())

    # Executive summary + radar + dimension table on one page (flows naturally)
    story.extend(_exec_summary(audit_result, styles))
    story.append(Spacer(1, 0.15 * inch))
    story.append(_build_radar(audit_result))
    story.append(Spacer(1, 0.15 * inch))
    story.extend(_dimension_table(audit_result, styles))
    story.append(PageBreak())

    # Progress since last audit (if available)
    progress = _progress_section(audit_result, previous_audit, styles)
    if progress:
        story.extend(progress)
        story.append(Spacer(1, 0.2 * inch))

    # Risks
    story.extend(_risks_section(audit_result, styles))

    # Benchmark comparison (shown in both modes when industry is available)
    industry = firm.get("industry")
    bm_elements = _benchmark_section(answers, industry, styles)
    if bm_elements:
        story.append(PageBreak())
        story.extend(bm_elements)

    # Mode-dependent tail
    if use_mode == "advisory":
        story.extend(_opportunities_section(audit_result, styles))

        if ai_recs:
            # AI-generated detailed analysis replaces canned recommendations
            story.append(PageBreak())
            story.extend(_ai_dimension_analyses_section(ai_recs, styles))
            story.append(PageBreak())
            story.extend(_ai_action_plan_section(ai_recs, styles))
            story.extend(_ai_roi_section(ai_recs, styles))
        else:
            # Canned fallback path (no ANTHROPIC_API_KEY). Previously this
            # rendered _recommendations_section AND _action_plan_section,
            # which showed the SAME six items in two different layouts -
            # padding that made the paid PDF look longer but undermined
            # perceived value. Keep only the 30/60/90 action plan; it's
            # more structured and less repetitive.
            story.append(PageBreak())
            story.extend(_action_plan_section(audit_result, styles))

        story.extend(_cta_section(use_mode, styles))
    else:
        story.extend(_cta_section(use_mode, styles))

    # Back page
    story.append(PageBreak())
    story.extend(_back_page(styles))

    doc.build(story)
    return output_path


# ---------------------------------------------------------------------------
# Sample generator (runs when this file is executed directly)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from scoring import run_audit
    from test_scoring import build_synthetic_answers

    answers = build_synthetic_answers()
    industry = "Professional Services"
    result = run_audit(answers, industry=industry)

    # Representative firmographics for the sample. Not real.
    sample_firm = {
        "company_name": "Acme Industrial Services",
        "revenue_band": "$5–20M",
        "ebitda_margin": 18,
        "employees": 42,
        "industry": industry,
        "years": 12,
        "owner_hours": 55,
    }

    build_pdf(result, sample_firm, "sample_lead_magnet.pdf",
              mode="lead_magnet", answers=answers)
    print("wrote sample_lead_magnet.pdf")

    build_pdf(result, sample_firm, "sample_advisory.pdf",
              mode="advisory", answers=answers)
    print("wrote sample_advisory.pdf")
