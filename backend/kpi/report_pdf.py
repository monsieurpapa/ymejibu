"""PDF report of the indicators (annual report, or one month), with vector charts.

Built with ReportLab only (no browser, no matplotlib), so it runs on the small
production server. Everything comes from `compute_year` and the shared
`catalog`, exactly like the dashboard: same values, same labels, same targets.
Missing data stays blank ("—"), never 0.
"""
import datetime as dt
import io
import math
import os
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from . import catalog
from .service import MONTHS_FR

# --------------------------------------------------------------------------------------- fonts
_FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def _register_fonts():
    for regular, bold in _FONT_CANDIDATES:
        if os.path.exists(regular) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("Body", regular))
            pdfmetrics.registerFont(TTFont("Body-Bold", bold))
            return True
    # Fallback: fonts bundled with ReportLab (Latin-1 coverage; text is sanitised below).
    import reportlab

    base = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    pdfmetrics.registerFont(TTFont("Body", os.path.join(base, "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("Body-Bold", os.path.join(base, "VeraBd.ttf")))
    return False


UNICODE_FONT = _register_fonts()


def t(s):
    """Replace glyphs missing from the fallback font."""
    s = str(s)
    if not UNICODE_FONT:
        s = s.replace("−", "-").replace("≥", ">=").replace("≤", "<=").replace(" ", " ")
    return s


def x(s):
    """Plain text for a Paragraph (escapes &, <, >)."""
    return escape(t(s))


MONTHS_SHORT = ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]


# --------------------------------------------------------------------------------------- style
BRAND = colors.HexColor("#0d4a8f")
SERIES = colors.HexColor("#2a78d6")
INK = colors.HexColor("#0f1722")
MUTED = colors.HexColor("#5b6676")
GRID = colors.HexColor("#e3e8ee")
LINE = colors.HexColor("#d6dde6")
SURFACE2 = colors.HexColor("#f5f7fa")
GOOD, GOOD_BG = colors.HexColor("#17632a"), colors.HexColor("#e3f4e6")
BAD, BAD_BG = colors.HexColor("#a11d1d"), colors.HexColor("#fde8e8")
WARN_BG = colors.HexColor("#fff3d6")

S = {
    "title": ParagraphStyle("title", fontName="Body-Bold", fontSize=20, leading=24, textColor=INK, spaceAfter=4),
    "subtitle": ParagraphStyle("subtitle", fontName="Body", fontSize=10.5, leading=14, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=14, leading=18, textColor=BRAND, spaceBefore=10, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Body", fontSize=9, leading=12, textColor=INK),
    "small": ParagraphStyle("small", fontName="Body", fontSize=7.5, leading=10, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8, leading=10, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=8, leading=10, textColor=INK),
    "num": ParagraphStyle("num", fontName="Body", fontSize=8, leading=10, textColor=INK, alignment=TA_RIGHT),
    "left": ParagraphStyle("left", fontName="Body", fontSize=8, leading=10, alignment=TA_LEFT),
}

# --------------------------------------------------------------------------------------- numbers
NBSP = " "


def _group(n, decimals):
    """French grouping: 12 345,6 (non-breaking space), trailing decimal zeros removed."""
    s = f"{abs(n):,.{decimals}f}".replace(",", "\u00a0").replace(".", ",")
    if decimals:
        s = s.rstrip("0").rstrip(",")
    return f"-{s}" if n < 0 and s.strip("0,\u00a0") else s


def fmt(v, kind):
    if v is None:
        return "—"
    v = float(v) if isinstance(v, Decimal) else v
    return {
        "pct": lambda: f"{_group(v * 100, 1)}{NBSP}%",
        "int": lambda: _group(v, 0),
        "num": lambda: _group(v, 1),
        "dec3": lambda: _group(v, 3),
        "usd": lambda: f"{_group(v, 0)}{NBSP}USD",
        "usd3": lambda: f"{_group(v, 3)}{NBSP}USD",
        "h": lambda: f"{_group(v, 1)}{NBSP}h",
        "m3": lambda: f"{_group(v, 0)}{NBSP}m³",
        "kwh": lambda: f"{_group(v, 0)}{NBSP}kWh",
        "l": lambda: f"{_group(v, 0)}{NBSP}L",
    }.get(kind, lambda: _group(v, 1))()


def _val(month, key):
    v = month["values"].get(key)
    return float(v) if isinstance(v, Decimal) else v


def target_ok(kpi, v):
    tg = kpi.get("target")
    if v is None or not tg:
        return None
    return v >= tg["value"] if tg["better"] == "up" else v <= tg["value"]


def latest(months, key, upto=None):
    for m in reversed(months[: upto or 12]):
        v = _val(m, key)
        if m["status"] != "future" and v is not None:
            return m, v
    return None, None


# --------------------------------------------------------------------------------------- charts
def line_chart(months, kpi, width, height=48 * mm, highlight=None):
    """Monthly line with gaps for missing months, dashed target, optional highlighted month."""
    d = Drawing(width, height)
    vals = [_val(m, kpi["key"]) for m in months]
    present = [v for v in vals if v is not None]
    tg = kpi.get("target")
    ref = present + ([tg["value"]] if tg else [])
    lo, hi = (min(ref), max(ref)) if ref else (0.0, 1.0)
    span = (hi - lo) or (abs(hi) or 1) * 0.2
    lo, hi = lo - span * 0.15, hi + span * 0.15
    if min(ref or [0]) >= 0:
        lo = max(lo, 0.0)  # quantities and rates are never negative
    if kpi["fmt"] == "pct":
        hi = min(hi, 1.0) if max(ref or [0]) <= 1 else hi
    step = 10 ** math.floor(math.log10(max(hi - lo, 1e-9)))
    lo, hi = math.floor(lo / step) * step, math.ceil(hi / step) * step
    ticks = [lo, (lo + hi) / 2, hi]
    labels = [t(fmt(v, kpi["fmt"])) for v in ticks]
    pad_l = max(pdfmetrics.stringWidth(lbl, "Body", 6.5) for lbl in labels) + 6
    pad_r, pad_t, pad_b = 6, 8, 14
    px = lambda i: pad_l + i * (width - pad_l - pad_r) / 11  # noqa: E731
    y = lambda v: pad_b + (v - lo) / (hi - lo) * (height - pad_t - pad_b)  # noqa: E731

    if highlight is not None:
        band = (width - pad_l - pad_r) / 11
        d.add(Rect(px(highlight) - band / 2, pad_b, band, height - pad_t - pad_b, fillColor=colors.HexColor("#e6effb"),
                   strokeColor=None))
    for tv, lbl in zip(ticks, labels):
        d.add(Line(pad_l, y(tv), width - pad_r, y(tv), strokeColor=GRID, strokeWidth=0.6))
        d.add(String(pad_l - 3, y(tv) - 2, lbl, fontName="Body", fontSize=6.5, fillColor=MUTED, textAnchor="end"))
    for i, m in enumerate(MONTHS_SHORT):
        d.add(String(px(i), 3, t(m), fontName="Body", fontSize=6.5, fillColor=MUTED, textAnchor="middle"))
    if not present:
        d.add(String(width / 2, height - pad_t - 10, t("Pas de donnée"), fontName="Body", fontSize=8, fillColor=MUTED, textAnchor="middle"))
    if tg:
        d.add(Line(pad_l, y(tg["value"]), width - pad_r, y(tg["value"]), strokeColor=INK, strokeWidth=0.6,
                   strokeDashArray=[3, 2]))
        d.add(String(width - pad_r, y(tg["value"]) + 2, t(tg["label"]), fontName="Body", fontSize=6.5, fillColor=INK,
                     textAnchor="end"))
    seg = []
    for i, v in enumerate(vals + [None]):
        if v is None:
            if len(seg) >= 2:
                d.add(PolyLine(sum(seg, []), strokeColor=SERIES, strokeWidth=1.4))
            seg = []
        else:
            seg.append([px(i), y(v)])
    for i, v in enumerate(vals):
        if v is not None:
            r = 2.6 if i == highlight else 1.8
            d.add(Circle(px(i), y(v), r, fillColor=SERIES, strokeColor=colors.white, strokeWidth=0.8))
    return d


def hbars(items, kind, width, bar_h=9):
    """Horizontal bars (label | bar | value); items: [(label, value)] with value > 0."""
    label_w = min(62 * mm, width * 0.45)
    value_w = 20 * mm
    row = bar_h + 5
    height = row * len(items) + 2
    d = Drawing(width, height)
    top = max(v for _, v in items) or 1
    for i, (lbl, v) in enumerate(items):
        yy = height - (i + 1) * row + 2
        text = t(lbl)
        while pdfmetrics.stringWidth(text, "Body", 7.5) > label_w - 4 and len(text) > 4:
            text = text[:-2]
        if text != t(lbl):
            text = text.rstrip() + "…"
        d.add(String(0, yy + 2, text, fontName="Body", fontSize=7.5, fillColor=INK))
        span = width - label_w - value_w
        d.add(Rect(label_w, yy, max(span * v / top, 1.5), bar_h, fillColor=SERIES, strokeColor=None))
        d.add(String(width, yy + 2, t(fmt(v, kind)), fontName="Body", fontSize=7.5, fillColor=INK, textAnchor="end"))
    return d


# --------------------------------------------------------------------------------------- tables
def _table(rows, widths, header=True, zebra=True, extra=None):
    tb = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONT", (0, 0), (-1, -1), "Body", 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [("FONT", (0, 0), (-1, 0), "Body-Bold", 7.5), ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.8, LINE)]
    if zebra:
        for r in range(1 if header else 0, len(rows)):
            if r % 2 == 0:
                style.append(("BACKGROUND", (0, r), (-1, r), SURFACE2))
    tb.setStyle(TableStyle(style + (extra or [])))
    return tb


def status_cell(ok):
    if ok is None:
        return Paragraph("—", S["small"])
    color, text = (GOOD, "atteinte") if ok else (BAD, "sous la cible")
    return Paragraph(f'<font color="{color.hexval().replace("0x", "#")}"><b>{t(text)}</b></font>', S["cell"])


def delta_cell(kpi, cur, prev):
    if cur is None or prev is None:
        return Paragraph("—", S["small"])
    diff = cur - prev
    if abs(diff) < 1e-12:
        return Paragraph("=", S["cell"])
    better = kpi.get("better")
    good = None if not better else (diff > 0) == (better == "up")
    arrow = "▲" if diff > 0 else "▼"
    if not UNICODE_FONT:
        arrow = "+" if diff > 0 else "-"
    shown = fmt(abs(diff) * (100 if kpi["fmt"] == "pct" else 1), "num") + (" pts" if kpi["fmt"] == "pct" else "")
    if kpi["fmt"] != "pct":
        shown = fmt(abs(diff), kpi["fmt"])
    color = "#5b6676" if good is None else ("#17632a" if good else "#a11d1d")
    return Paragraph(f'<font color="{color}">{arrow} {t(shown)}</font>', S["cell"])


# --------------------------------------------------------------------------------------- sections
def _month_label(m, year):
    return f"{MONTHS_FR[m - 1]} {year}"


def summary_section(result, width, upto=None):
    months = result["months"]
    rows = [["Indicateur", "Dernière valeur", "Mois", "Année", "Cible", "Statut"]]
    for k in catalog.KPIS:
        m, v = latest(months, k["key"], upto)
        annual = result["annual"].get(k["key"]) if upto is None else None
        rows.append([
            Paragraph(x(k["title"]), S["cellb"]),
            Paragraph(x(fmt(v, k["fmt"])), S["num"]),
            Paragraph(x(MONTHS_SHORT[m["month"] - 1] + "." if m else "—"), S["cell"]),
            Paragraph(x(fmt(annual, k["fmt"])) if upto is None else "", S["num"]),
            Paragraph(x(k["target"]["label"]) if k.get("target") else "—", S["small"]),
            status_cell(target_ok(k, v)),
        ])
    w = width
    return _table(rows, [w * 0.34, w * 0.16, w * 0.09, w * 0.15, w * 0.12, w * 0.14])


def charts_section(result, width, highlight=None):
    col = (width - 6 * mm) / 2
    cells, grid = [], []
    for k in catalog.KPIS:
        block = [Paragraph(x(k["title"]), S["h2"]), Paragraph(x(k["help"]), S["small"]), Spacer(1, 2),
                 line_chart(result["months"], k, col, highlight=highlight)]
        cells.append(block)
    for i in range(0, len(cells), 2):
        grid.append([cells[i], cells[i + 1] if i + 1 < len(cells) else ""])
    tb = Table(grid, colWidths=[col + 3 * mm, col + 3 * mm])
    tb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return tb


def monthly_table(result, width):
    months = result["months"]
    head = ["Indicateur"] + [t(MONTHS_SHORT[m["month"] - 1]) for m in months] + ["Année"]
    rows = [head]
    # Units move to the row label so figures fit in narrow month columns.
    compact = {"usd": ("int", " (USD)"), "usd3": ("dec3", " (USD)"), "m3": ("int", " (m³)"), "h": ("num", " (h)")}
    for key, label, kind in catalog.TABLE_ROWS:
        kind, unit = compact.get(kind, (kind, ""))
        row = [Paragraph(x(label + unit), S["cell"])]
        for m in months:
            v = _val(m, key)
            hist = m["sources"].get(key) == "historique" and v is not None
            row.append(Paragraph(x(fmt(v, kind) if v is not None else "") + (" <super>h</super>" if hist else ""), S["num"]))
        row.append(Paragraph(f"<b>{t(fmt(result['annual'].get(key), kind) if result['annual'].get(key) is not None else '')}</b>",
                             S["num"]))
        rows.append(row)
    first = 44 * mm
    rest = (width - first) / 13
    extra = [("BACKGROUND", (i + 1, 0), (i + 1, -1), colors.HexColor("#fafbfc"))
             for i, m in enumerate(months) if m["status"] == "future"]
    return _table(rows, [first] + [rest] * 13, extra=extra)


def causes_section(result, width):
    out = []
    for b in catalog.BREAKDOWNS:
        items = [(lbl, float(result["annual"].get(k) or 0)) for k, lbl in b["items"]]
        items = sorted([i for i in items if i[1] > 0], key=lambda i: -i[1])
        if items:
            out.append(KeepTogether([Paragraph(x(b["title"]) + " — année", S["h2"]), hbars(items, b["fmt"], width)]))
    return out


def month_detail(result, m_idx, width, include_trend=False):
    """Everything about one month: KPIs vs previous month and target, key figures, breakdowns."""
    year = result["year"]
    months = result["months"]
    mon = months[m_idx]
    prev = months[m_idx - 1] if m_idx > 0 else None
    status = {"closed": "mois clôturé", "current": "mois en cours (valeurs partielles)", "future": "à venir"}[mon["status"]]
    cov = mon["coverage"]
    story = [Paragraph(x(f"Détail du mois — {_month_label(m_idx + 1, year)}"), S["h1"]),
             Paragraph(x(f"{status.capitalize()} · relevés de pompage : {cov['pump_reading_days']} jour(s) sur {cov['days']}"
                         + (" · contient des valeurs de l'historique Excel" if "historique" in mon["sources"].values() else "")),
                       S["subtitle"]), Spacer(1, 6)]
    if not mon["has_data"] and mon["status"] != "future":
        story += [Paragraph("Aucune donnée d'exploitation pour ce mois.", S["body"]), Spacer(1, 4)]

    rows = [["Indicateur", "Ce mois", "Mois précédent", "Évolution", "Cible", "Statut"]]
    for k in catalog.KPIS:
        cur = _val(mon, k["key"])
        pv = _val(prev, k["key"]) if prev else None
        rows.append([Paragraph(x(k["title"]), S["cellb"]), Paragraph(x(fmt(cur, k["fmt"])), S["num"]),
                     Paragraph(x(fmt(pv, k["fmt"])), S["num"]), delta_cell(k, cur, pv),
                     Paragraph(x(k["target"]["label"]) if k.get("target") else "—", S["small"]), status_cell(target_ok(k, cur))])
    w = width
    story.append(_table(rows, [w * 0.32, w * 0.15, w * 0.15, w * 0.14, w * 0.11, w * 0.13]))
    story.append(Spacer(1, 8))

    # Key figures, two groups per row.
    blocks = []
    for title, items in catalog.FIGURES:
        rws = [[Paragraph(x(title), S["cellb"]), ""]] + [
            [Paragraph(x(lbl), S["cell"]), Paragraph(x(fmt(_val(mon, key), kind)), S["num"])] for lbl, key, kind in items]
        tb = Table(rws, colWidths=[(w / 2 - 6 * mm) * 0.62, (w / 2 - 6 * mm) * 0.38])
        tb.setStyle(TableStyle([("SPAN", (0, 0), (1, 0)), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
                                ("BACKGROUND", (0, 0), (-1, 0), SURFACE2), ("TOPPADDING", (0, 0), (-1, -1), 2),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        blocks.append(tb)
    pm_rows = [[Paragraph("Maintenance préventive", S["cellb"]), Paragraph("prévue", S["small"]), Paragraph("réalisée", S["small"])]]
    for key, lbl in catalog.PM_CATEGORIES:
        pm_rows.append([Paragraph(x(lbl), S["cell"]), Paragraph(fmt(_val(mon, f"pm_planned_{key}"), "int"), S["num"]),
                        Paragraph(fmt(_val(mon, f"pm_done_{key}"), "int"), S["num"])])
    pm = Table(pm_rows, colWidths=[(w / 2 - 6 * mm) * 0.5, (w / 2 - 6 * mm) * 0.25, (w / 2 - 6 * mm) * 0.25])
    pm.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("BACKGROUND", (0, 0), (-1, 0), SURFACE2),
                            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    blocks.append(pm)
    grid = [[blocks[i], blocks[i + 1] if i + 1 < len(blocks) else ""] for i in range(0, len(blocks), 2)]
    gt = Table(grid, colWidths=[w / 2, w / 2])
    gt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(gt)

    for b in catalog.BREAKDOWNS:
        items = sorted([(lbl, float(_val(mon, k) or 0)) for k, lbl in b["items"] if (_val(mon, k) or 0) > 0], key=lambda i: -i[1])
        if items:
            story.append(KeepTogether([Paragraph(x(b["title"]), S["h2"]), hbars(items, b["fmt"], w)]))
    if include_trend:
        story += [CondPageBreak(90 * mm), Paragraph("Tendance sur l'année (mois sélectionné en surbrillance)", S["h1"]),
                  charts_section(result, w, highlight=m_idx)]
    return story


# --------------------------------------------------------------------------------------- document
class _Doc(BaseDocTemplate):
    def __init__(self, buf, header, **kw):
        super().__init__(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=18 * mm, bottomMargin=16 * mm, **kw)
        self.header = header
        portrait = Frame(self.leftMargin, self.bottomMargin, A4[0] - 30 * mm, A4[1] - 34 * mm, id="p")
        lw, lh = landscape(A4)
        land = Frame(15 * mm, 16 * mm, lw - 30 * mm, lh - 34 * mm, id="l")
        self.addPageTemplates([PageTemplate("portrait", [portrait], onPage=self._decorate, pagesize=A4),
                               PageTemplate("landscape", [land], onPage=self._decorate, pagesize=landscape(A4))])

    def _decorate(self, canv, doc):
        w, h = canv._pagesize
        canv.saveState()
        canv.setFillColor(BRAND)
        canv.rect(0, h - 8 * mm, w, 8 * mm, stroke=0, fill=1)
        canv.setFillColor(colors.white)
        canv.setFont("Body-Bold", 8)
        canv.drawString(15 * mm, h - 5.5 * mm, t("Yme Jibu — Exploitation & Maintenance"))
        canv.setFont("Body", 8)
        canv.drawRightString(w - 15 * mm, h - 5.5 * mm, t(self.header))
        canv.setFillColor(MUTED)
        canv.setFont("Body", 7)
        canv.drawString(15 * mm, 8 * mm, t("Valeurs calculées à partir des fiches terrain et de l'historique Excel. « — » = pas de donnée."))
        canv.drawRightString(w - 15 * mm, 8 * mm, f"Page {doc.page}")
        canv.restoreState()


def build_report(result, site_name, month=None, generated_by=""):
    """Annual report (month=None) or monthly report (month=1..12). Returns PDF bytes."""
    year = result["year"]
    buf = io.BytesIO()
    now = dt.datetime.now()
    header = f"{site_name} · {year}" if month is None else f"{site_name} · {_month_label(month, year)}"
    doc = _Doc(buf, header, title=t(f"Indicateurs E&M — {header}"), author="Yme Jibu", subject="Rapport des indicateurs")
    width = A4[0] - 30 * mm
    story = []

    if month is None:
        closed = [m for m in result["months"] if m["has_data"]]
        period = (f"{closed[0]['label']} – {closed[-1]['label']} {year}" if closed else "aucun mois avec données")
        story += [Paragraph(x(f"Rapport des indicateurs E&M {year}"), S["title"]),
                  Paragraph(x(f"Réseau d'eau {site_name} · période couverte : {period}"), S["subtitle"]),
                  Paragraph(x(f"Généré le {now:%d/%m/%Y à %H:%M}" + (f" par {generated_by}" if generated_by else "")), S["small"]),
                  Spacer(1, 8), Paragraph("Synthèse", S["h1"]), summary_section(result, width),
                  Spacer(1, 4),
                  Paragraph(x("Cibles par défaut, à valider par le Responsable technique. Statut évalué sur la dernière valeur connue."),
                            S["small"]),
                  PageBreak(), Paragraph("Évolution mensuelle", S["h1"]), charts_section(result, width)]
        causes = causes_section(result, width)
        if causes:
            story += [CondPageBreak(70 * mm), Paragraph("Analyse des causes", S["h1"])] + causes
        story += [NextPageTemplate("landscape"), PageBreak(), Paragraph(x(f"Tableau mensuel {year}"), S["h1"]),
                  Paragraph(x("h = valeur de l'historique Excel (mois antérieurs à l'application) ; case vide = pas de donnée ; "
                              "colonnes grisées = mois à venir."), S["small"]), Spacer(1, 4),
                  monthly_table(result, landscape(A4)[0] - 30 * mm), NextPageTemplate("portrait")]
        for i, m in enumerate(result["months"]):
            if m["has_data"]:
                story += [PageBreak()] + month_detail(result, i, width)
    else:
        story += [Paragraph(x(f"Rapport mensuel — {_month_label(month, year)}"), S["title"]),
                  Paragraph(x(f"Réseau d'eau {site_name}"), S["subtitle"]),
                  Paragraph(x(f"Généré le {now:%d/%m/%Y à %H:%M}" + (f" par {generated_by}" if generated_by else "")), S["small"]),
                  Spacer(1, 4)] + month_detail(result, month - 1, width, include_trend=True)
    doc.build(story)
    return buf.getvalue()
