"""
FairLens – PDF Fairness Audit Report Generator
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
import io
from datetime import datetime

W, H = A4

C_DARK   = colors.HexColor("#0D1117")
C_BLUE   = colors.HexColor("#1565C0")
C_TEAL   = colors.HexColor("#00695C")
C_RED    = colors.HexColor("#C62828")
C_ORANGE = colors.HexColor("#E65100")
C_GREEN  = colors.HexColor("#2E7D32")
C_GRAY   = colors.HexColor("#546E7A")
C_LGRAY  = colors.HexColor("#ECEFF1")
C_WHITE  = colors.white

SEV_COLOR = {
    "none":   C_GREEN,
    "low":    colors.HexColor("#F9A825"),
    "medium": C_ORANGE,
    "high":   C_RED,
}
SEV_BG = {
    "none":   colors.HexColor("#E8F5E9"),
    "low":    colors.HexColor("#FFFDE7"),
    "medium": colors.HexColor("#FFF3E0"),
    "high":   colors.HexColor("#FFEBEE"),
}

def _sty(name, **kw):
    return ParagraphStyle(name, **kw)

def sp(n=6): return Spacer(1, n)
def hr(): return HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#BBDEFB"),
                             spaceBefore=4, spaceAfter=4)

def _table(data, col_widths, style_cmds):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(style_cmds))
    return t


def generate_report(
    dataset_name: str,
    protected_col: str,
    privileged_group: str,
    unprivileged_group: str,
    metrics_result: dict,
    recommendations: list,
) -> bytes:
    buf = io.BytesIO()
    PW = W - 28*mm

    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=14*mm, rightMargin=14*mm,
        topMargin=14*mm, bottomMargin=14*mm)

    H1 = _sty("H1", fontName="Helvetica-Bold", fontSize=22, leading=28,
               textColor=C_BLUE, spaceAfter=4)
    H2 = _sty("H2", fontName="Helvetica-Bold", fontSize=13, leading=17,
               textColor=C_BLUE, spaceBefore=12, spaceAfter=4)
    H3 = _sty("H3", fontName="Helvetica-Bold", fontSize=10, leading=14,
               textColor=C_DARK, spaceAfter=3)
    BD = _sty("BD", fontName="Helvetica", fontSize=10, leading=16,
               textColor=C_DARK, alignment=TA_JUSTIFY)
    SM = _sty("SM", fontName="Helvetica", fontSize=9, leading=13,
               textColor=C_GRAY)
    BL = _sty("BL", fontName="Helvetica-Bold", fontSize=10, leading=14,
               textColor=C_DARK)
    CT = _sty("CT", fontName="Helvetica", fontSize=9, leading=13,
               textColor=C_WHITE, alignment=TA_CENTER)

    story = []
    overall = metrics_result.get("overall", {})
    metrics = metrics_result.get("metrics", {})
    groups  = metrics_result.get("group_stats", {})
    proxies = metrics_result.get("proxy_features", {})
    recs    = recommendations

    bias_score = overall.get("bias_score", 0)
    severity   = overall.get("severity", "none")
    sev_color  = SEV_COLOR.get(severity, C_GRAY)
    sev_bg     = SEV_BG.get(severity, C_LGRAY)

    # ── Header ────────────────────────────────────────────────────────────
    hdr = _table([[
        [Paragraph("FairLens", _sty("FL", fontName="Helvetica-Bold",
            fontSize=26, textColor=C_WHITE)),
         Paragraph("AI Fairness Audit Report", _sty("FS", fontName="Helvetica",
            fontSize=12, textColor=colors.HexColor("#BBDEFB")))],
        [Paragraph(dataset_name, _sty("DN", fontName="Helvetica-Bold",
            fontSize=11, textColor=C_WHITE, alignment=TA_CENTER)),
         Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}",
            _sty("GD", fontName="Helvetica", fontSize=9,
                 textColor=colors.HexColor("#90CAF9"), alignment=TA_CENTER))],
    ]], [PW*0.6, PW*0.4], [
        ("BACKGROUND",   (0,0), (-1,-1), C_BLUE),
        ("TOPPADDING",   (0,0), (-1,-1), 14),
        ("BOTTOMPADDING",(0,0), (-1,-1), 14),
        ("LEFTPADDING",  (0,0), (-1,-1), 16),
        ("RIGHTPADDING", (0,0), (-1,-1), 16),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ])
    story.append(hdr)
    story.append(sp(12))

    # ── Overall bias score card ───────────────────────────────────────────
    score_card = _table([[
        [Paragraph(f"{bias_score:.0f}", _sty("SC", fontName="Helvetica-Bold",
            fontSize=36, textColor=sev_color, alignment=TA_CENTER)),
         Paragraph("/ 100", _sty("SM2", fontName="Helvetica",
            fontSize=12, textColor=C_GRAY, alignment=TA_CENTER)),
         Paragraph("BIAS SCORE", _sty("SL", fontName="Helvetica-Bold",
            fontSize=8, textColor=C_GRAY, alignment=TA_CENTER))],
        [Paragraph(severity.upper(), _sty("SEV", fontName="Helvetica-Bold",
            fontSize=20, textColor=sev_color, alignment=TA_CENTER)),
         Paragraph("SEVERITY", _sty("SL2", fontName="Helvetica-Bold",
            fontSize=8, textColor=C_GRAY, alignment=TA_CENTER))],
        [Paragraph(f"{overall.get('model_accuracy', 0)*100:.1f}%",
            _sty("ACC", fontName="Helvetica-Bold", fontSize=20,
                 textColor=C_TEAL, alignment=TA_CENTER)),
         Paragraph("MODEL ACCURACY", _sty("SL3", fontName="Helvetica-Bold",
            fontSize=8, textColor=C_GRAY, alignment=TA_CENTER))],
        [Paragraph(str(overall.get("total_rows", 0)),
            _sty("RW", fontName="Helvetica-Bold", fontSize=20,
                 textColor=C_DARK, alignment=TA_CENTER)),
         Paragraph("TOTAL ROWS", _sty("SL4", fontName="Helvetica-Bold",
            fontSize=8, textColor=C_GRAY, alignment=TA_CENTER))],
    ]], [PW/4]*4, [
        ("BACKGROUND",   (0,0), (-1,-1), sev_bg),
        ("TOPPADDING",   (0,0), (-1,-1), 14),
        ("BOTTOMPADDING",(0,0), (-1,-1), 14),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("LINEBEFORE",   (1,0), (3,-1), 0.5, colors.HexColor("#BBDEFB")),
    ])
    story.append(score_card)
    story.append(sp(12))

    # ── Groups compared ───────────────────────────────────────────────────
    story.append(Paragraph("Groups Compared", H2))
    story.append(hr())
    gc = _table([[
        Paragraph(f"Protected attribute: {protected_col}", BL),
        Paragraph(f"Privileged group: {privileged_group}", BL),
        Paragraph(f"Unprivileged group: {unprivileged_group}", BL),
    ]], [PW/3]*3, [
        ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#E3F2FD")),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("LINEBEFORE",   (1,0), (2,-1), 0.5, colors.HexColor("#BBDEFB")),
    ])
    story.append(gc)
    story.append(sp(12))

    # ── Fairness metrics table ─────────────────────────────────────────────
    story.append(Paragraph("Fairness Metrics", H2))
    story.append(hr())

    m_rows = [
        [Paragraph("Metric", _sty("TH", fontName="Helvetica-Bold",
            fontSize=9, textColor=C_WHITE)),
         Paragraph("Value", _sty("TH2", fontName="Helvetica-Bold",
            fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)),
         Paragraph("Ideal", _sty("TH3", fontName="Helvetica-Bold",
            fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)),
         Paragraph("Severity", _sty("TH4", fontName="Helvetica-Bold",
            fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)),
         Paragraph("What it means", _sty("TH5", fontName="Helvetica-Bold",
            fontSize=9, textColor=C_WHITE))],
    ]
    style_cmds = [
        ("BACKGROUND",   (0,0), (-1,0), C_BLUE),
        ("TOPPADDING",   (0,0), (-1,-1), 7),
        ("BOTTOMPADDING",(0,0), (-1,-1), 7),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("LINEBELOW",    (0,0), (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
    ]

    metric_labels = {
        "statistical_parity_difference":      "Statistical Parity Difference",
        "disparate_impact":                   "Disparate Impact Ratio",
        "equalized_odds_difference_tpr":      "Equalized Odds (TPR)",
        "equalized_odds_difference_fpr":      "Equalized Odds (FPR)",
        "predictive_parity_difference":       "Predictive Parity Difference",
        "accuracy_difference":                "Accuracy Difference",
    }
    for i, (key, label) in enumerate(metric_labels.items()):
        m = metrics.get(key, {})
        val = m.get("value")
        sev = m.get("severity", "none")
        ideal = m.get("ideal", 0)
        desc  = m.get("description", "")
        sc    = SEV_COLOR.get(sev, C_GRAY)
        bg    = SEV_BG.get(sev, C_WHITE) if i % 2 == 1 else C_WHITE
        val_str = f"{val:.4f}" if val is not None else "N/A"
        ideal_str = str(ideal)
        m_rows.append([
            Paragraph(label, SM),
            Paragraph(val_str, _sty(f"V{i}", fontName="Helvetica-Bold",
                fontSize=10, textColor=sc, alignment=TA_CENTER)),
            Paragraph(ideal_str, _sty(f"ID{i}", fontName="Helvetica",
                fontSize=9, textColor=C_GRAY, alignment=TA_CENTER)),
            Paragraph(sev.upper(), _sty(f"S{i}", fontName="Helvetica-Bold",
                fontSize=9, textColor=sc, alignment=TA_CENTER)),
            Paragraph(desc, SM),
        ])
        if bg != C_WHITE:
            r = len(m_rows) - 1
            style_cmds.append(("BACKGROUND", (0, r), (-1, r), bg))

    mt = Table(m_rows, colWidths=[PW*0.25, PW*0.10, PW*0.08, PW*0.10, PW*0.47])
    mt.setStyle(TableStyle(style_cmds))
    story.append(mt)
    story.append(sp(12))

    # ── Group statistics ───────────────────────────────────────────────────
    story.append(Paragraph("Group-Level Statistics", H2))
    story.append(hr())

    gs_header = [
        Paragraph("Statistic", _sty("GH", fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE)),
    ]
    gs_row_labels = ["Sample size", "Positive outcome rate",
                     "Model accuracy", "True positive rate",
                     "False positive rate", "Precision (PPV)"]
    gs_keys = ["count", "positive_rate", "model_accuracy",
               "true_positive_rate", "false_positive_rate", "precision"]

    group_names = list(groups.keys())
    for gn in group_names:
        label = f"{'Privileged' if gn == str(privileged_group) else 'Unprivileged'}: {gn}"
        gs_header.append(Paragraph(label, _sty("GH2", fontName="Helvetica-Bold",
            fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)))

    gs_data = [gs_header]
    for i, (row_label, key) in enumerate(zip(gs_row_labels, gs_keys)):
        row = [Paragraph(row_label, SM)]
        for gn in group_names:
            val = groups.get(gn, {}).get(key, "N/A")
            if isinstance(val, float):
                val = f"{val:.4f}"
            row.append(Paragraph(str(val), _sty(f"GV{i}", fontName="Helvetica",
                fontSize=9, alignment=TA_CENTER, textColor=C_DARK)))
        gs_data.append(row)

    cw = [PW*0.4] + [PW*0.3]*len(group_names)
    gs_tbl = Table(gs_data, colWidths=cw[:len(gs_data[0])])
    gs_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), C_TEAL),
        ("BACKGROUND",   (0,1), (-1,1), colors.HexColor("#F5F5F5")),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("LINEBELOW",    (0,0), (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(gs_tbl)

    # ── Proxy features ─────────────────────────────────────────────────────
    if proxies:
        story.append(sp(12))
        story.append(Paragraph("Proxy Feature Detection", H2))
        story.append(hr())
        story.append(Paragraph(
            f"The following features are highly correlated with '{protected_col}' "
            "and may be acting as hidden proxies — allowing the model to learn "
            "the protected attribute indirectly even when it is excluded:", BD))
        story.append(sp(6))
        pf_rows = [[
            Paragraph("Feature", _sty("PH", fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE)),
            Paragraph("Correlation with protected attribute", _sty("PH2", fontName="Helvetica-Bold",
                fontSize=9, textColor=C_WHITE)),
            Paragraph("Risk level", _sty("PH3", fontName="Helvetica-Bold",
                fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)),
        ]]
        for feat, corr in proxies.items():
            risk = "High" if corr > 0.5 else ("Medium" if corr > 0.35 else "Low")
            rc   = C_RED if risk == "High" else (C_ORANGE if risk == "Medium" else colors.HexColor("#F9A825"))
            pf_rows.append([
                Paragraph(feat, SM),
                Paragraph(f"{corr:.3f}", _sty("PV", fontName="Helvetica-Bold",
                    fontSize=10, textColor=rc)),
                Paragraph(risk, _sty("PR", fontName="Helvetica-Bold",
                    fontSize=9, textColor=rc, alignment=TA_CENTER)),
            ])
        pf_tbl = Table(pf_rows, colWidths=[PW*0.35, PW*0.45, PW*0.20])
        pf_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), C_ORANGE),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ("LEFTPADDING",  (0,0), (-1,-1), 8),
            ("LINEBELOW",    (0,0), (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
        ]))
        story.append(pf_tbl)

    story.append(PageBreak())

    # ── Recommendations ────────────────────────────────────────────────────
    story.append(Paragraph("Fix Recommendations", H1))
    story.append(hr())
    story.append(sp(6))

    for i, rec in enumerate(recs):
        priority = rec.get("priority", "medium")
        pc = C_RED if priority == "high" else (C_ORANGE if priority == "medium" else C_TEAL)
        header = _table([[
            Paragraph(f"{i+1}. {rec['title']}", _sty("RH", fontName="Helvetica-Bold",
                fontSize=11, textColor=C_WHITE)),
            Paragraph(f"Priority: {priority.upper()}", _sty("RP", fontName="Helvetica-Bold",
                fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)),
            Paragraph(f"Impact: {rec.get('impact','').upper()}", _sty("RI", fontName="Helvetica-Bold",
                fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)),
        ]], [PW*0.60, PW*0.20, PW*0.20], [
            ("BACKGROUND",   (0,0), (-1,-1), pc),
            ("TOPPADDING",   (0,0), (-1,-1), 8),
            ("BOTTOMPADDING",(0,0), (-1,-1), 8),
            ("LEFTPADDING",  (0,0), (-1,-1), 12),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ])
        story.append(header)
        body = _table([[
            [Paragraph(rec.get("description",""), BD),
             sp(6),
             Paragraph("Suggested code:", _sty("CL", fontName="Helvetica-Bold",
                fontSize=9, textColor=C_GRAY)),
             Paragraph(rec.get("code","").replace("\n", "<br/>"),
                _sty("CD", fontName="Courier", fontSize=8, leading=13,
                     textColor=colors.HexColor("#1A237E"), backColor=colors.HexColor("#F8F9FF"))),
            ]
        ]], [PW], [
            ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#FAFAFA")),
            ("TOPPADDING",   (0,0), (-1,-1), 10),
            ("BOTTOMPADDING",(0,0), (-1,-1), 10),
            ("LEFTPADDING",  (0,0), (-1,-1), 12),
            ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ])
        story.append(body)
        story.append(sp(8))

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(sp(8))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE))
    story.append(sp(4))
    story.append(Paragraph(
        f"FairLens AI Fairness Audit  ·  {dataset_name}  ·  "
        f"Protected: {protected_col}  ·  Generated {datetime.now().strftime('%Y-%m-%d')}  ·  "
        "Built for Google Solution Challenge 2026",
        _sty("FT", fontName="Helvetica", fontSize=8,
             textColor=C_GRAY, alignment=TA_CENTER)
    ))

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_BLUE)
        canvas.rect(0, H - 6*mm, W, 6*mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#ECEFF1"))
        canvas.rect(0, 0, W, 5*mm, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(C_GRAY)
        canvas.drawCentredString(W/2, 1.5*mm,
            f"FairLens Bias Audit Report  ·  Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
