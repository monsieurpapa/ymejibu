"""Load the five workbooks into the database. Idempotent (natural keys + update_or_create).

The Excel files are opened read-only and never saved. Every imported row keeps
its `source_ref` (file!sheet!cell) and the codes of the quality findings that
affected it in `flags`.
"""
import datetime as dt
import re
from collections import Counter, defaultdict
from decimal import Decimal

from django.db import transaction
from openpyxl.utils import column_index_from_string as col_idx

from core.models import (
    ASSET_TYPE_CODES,
    Asset,
    AssetType,
    Condition,
    Fitting,
    Node,
    NodeKind,
    Person,
    PipeRole,
    PipeSegment,
    Role,
    Site,
    StaffingNeed,
    Zone,
)
from kpi.models import MonthlyAggregate
from ops.models import DailyReading, FailureCause, NRWCause, QualityParameter, QualityThreshold, RecordSource, WaterQualityTest
from ops.quality import is_compliant
from plan.models import ActionPlanTask, BudgetLine, MonthlyBudget, Tariff
from stock.models import StockCategory, StockItem

from .xl import clean, is_formula, is_placeholder, node_code, parse_capacity, parse_gps, parse_month_year, strip_number


class Log:
    """Collects what the importer did, for the report."""

    def __init__(self):
        self.counts = Counter()
        self.skipped = []  # (ref, reason)
        self.flagged = []  # (ref, what, flag codes)
        self.mapping = []  # (excel label, ref, new code)
        self.notes = []

    def skip(self, ref, reason):
        self.skipped.append((ref, reason))

    def flag(self, ref, what, *codes):
        self.flagged.append((ref, what, ", ".join(codes)))


def d(v):
    if v is None or v == "":
        return None
    return Decimal(str(v))


# ------------------------------------------------------------ site & zones

def load_site(wb, log, code="GO", name="Goma Ouest"):
    site, _ = Site.objects.update_or_create(
        code=code, defaults={"name": name, "description": "Réseau d'eau potable Goma Ouest (Mugunga–Lac Vert), Yme Jibu"})
    # Zones: the staff register defines "Point focal du réseau Zone 1..3".
    ws = wb.f("staff", "1. Pers tech perm")
    zones = sorted({int(m.group(1)) for i in range(4, 13) for m in [re.search(r"Zone\s*(\d+)", str(ws[f"E{i}"].value or ""))] if m})
    for z in zones or [1, 2]:
        Zone.objects.update_or_create(site=site, code=f"Z{z}", defaults={"name": f"Zone {z}"})
        log.counts["zones"] += 1
    log.notes.append("Zones créées depuis le registre du personnel (« Point focal du réseau Zone N »). "
                     "L'affectation des nœuds et des BF aux zones n'existe pas dans Excel : à compléter.")
    return site


# ------------------------------------------------------------ assets (workbook 1, sheet 1)

class AssetCoder:
    def __init__(self, site):
        self.site = site
        self.used = Counter()

    def next(self, type_):
        self.used[type_] += 1
        return f"{self.site.code}-{ASSET_TYPE_CODES[type_]}-{self.used[type_]:03d}"


def _upsert_asset(site, code, log, ref, raw, **fields):
    flags = fields.pop("flags", [])
    asset, created = Asset.objects.update_or_create(
        code=code, defaults=dict(site=site, source_ref=ref, raw_label=(raw or "")[:255], flags=flags, **fields))
    log.counts["assets"] += 1
    log.mapping.append((raw, ref, code))
    if flags:
        log.flag(ref, code, *flags)
    return asset


TYPO_FIXES = [(r"doeseuse", "doseuse"), (r"Choration", "Chloration")]


def _nice(text):
    """Fix known typos, sentence-case ALL-CAPS names but keep short acronyms (CAJED)."""
    text = text.strip()
    for pat, rep in TYPO_FIXES:
        text = re.sub(pat, rep, text, flags=re.I)
    if text.isupper() and not (len(text.split()) == 1 and len(text) <= 5):
        text = text.title()
    text = re.sub(r"Unité de Chloration", "Unité de chloration", text)
    return text[:1].upper() + text[1:]


def _child_type(text):
    t = (text or "").lower()
    if "motopompe" in t or "groupe" in t and "pompe" in t:
        return AssetType.PUMP
    if "doseuse" in t or "doeseuse" in t:
        return AssetType.DOSING_PUMP
    if "réservoir" in t or "reservoir" in t:
        return AssetType.RESERVOIR
    if "tank" in t:
        return AssetType.TANK
    if "panneau" in t:
        return AssetType.SOLAR_PANEL
    if "batterie" in t:
        return AssetType.BATTERY
    return AssetType.OTHER


def load_assets(wb, site, log):
    """Sheet 1: production, storage, treatment. Groups (column D) become parent assets."""
    S = "1. Registre_Actifs_Prod&Stock"
    ws = wb.f("assets", S)
    coder = AssetCoder(site)
    category = None
    parent = None
    parent_row = None
    by_type = {"pompage": AssetType.PUMP_STATION, "stockage": AssetType.STORAGE_SITE, "traitement": AssetType.CHLORINATION_UNIT}
    created = {}
    for i in range(4, ws.max_row + 1):
        c, dname, e = clean(ws[f"C{i}"].value), clean(ws[f"D{i}"].value), clean(ws[f"E{i}"].value)
        if c:
            category = c.lower()
        if dname:
            if is_placeholder(dname):
                log.skip(wb.ref("assets", S, f"D{i}"), f"Ligne modèle « {dname} » sans actif")
                parent = None
                continue
            ptype = by_type.get(category, AssetType.OTHER)
            name = _nice(strip_number(dname))
            flags = []
            if "Choration" in dname:
                flags.append("A14")
            gps_lat, gps_lon, gps_alt = parse_gps(ws[f"F{i}"].value) if not e else (None, None, None)
            if not e:
                flags.append("incomplet")
            parent = _upsert_asset(site, coder.next(ptype), log, wb.ref("assets", S, f"D{i}"), dname,
                                   name=name, type=ptype, parent=None, flags=flags,
                                   latitude=d(gps_lat), longitude=d(gps_lon), altitude_m=d(gps_alt))
            parent_row = i
            created[name.upper()] = parent
        if not e or parent is None:
            continue
        ref = wb.ref("assets", S, f"E{i}")
        typ = _child_type(e)
        g, h = clean(ws[f"G{i}"].value), clean(ws[f"H{i}"].value)
        cap, unit = parse_capacity(str(g) if g else "")
        power = re.search(r"(\d+(?:[.,]\d+)?)\s*kw\b", str(h or ""), re.I)
        head = re.search(r"HMT\s*(\d+)\s*m", str(h or ""), re.I)
        lat, lon, alt = parse_gps(ws[f"F{i}"].value)
        cond = {"bon": Condition.GOOD, "mauvais": Condition.POOR, "moyen": Condition.FAIR}.get(str(ws[f"I{i}"].value or "").strip().lower(),
                                                                                                Condition.UNKNOWN)
        inst = parse_month_year(ws[f"J{i}"].value)
        m = re.match(r"^\s*(\d+)\s+(.*)$", e)
        qty, label = (int(m.group(1)), m.group(2)) if m else (1, e)
        flags = []
        if lat is None:
            flags.append("A09")
        if inst and isinstance(ws[f"J{i}"].value, str):
            flags.append("A12")
        individual = typ in (AssetType.PUMP, AssetType.DOSING_PUMP)
        n = qty if individual else 1
        label = _nice(label)
        if individual and qty > 1:
            label = re.sub(r"(?i)^pompes doseuses", "Pompe doseuse", label)
        for k in range(n):
            name = label if n == 1 else f"{label} n°{k + 1}"
            attrs = {} if individual or qty == 1 else {"quantite": qty}
            if parent is not None:
                name = f"{name} — {parent.name}"
            asset = _upsert_asset(
                site, coder.next(typ), log, ref, e, name=name, type=typ, parent=parent,
                capacity_value=d(cap), capacity_unit=unit, power_kw=d(power.group(1).replace(",", ".")) if power else None,
                head_m=d(head.group(1)) if head else None, specs=h or "", condition=cond, install_date=inst,
                built_by=clean(ws[f"K{i}"].value) or "", om_documents=clean(ws[f"L{i}"].value) or "",
                latitude=d(lat), longitude=d(lon), altitude_m=d(alt), attributes=attrs,
                flags=flags + (["A13"] if qty > 1 else []))
            if typ == AssetType.RESERVOIR and parent is not None and parent.latitude is None and lat is not None:
                parent.latitude, parent.longitude = d(lat), d(lon)
                parent.save(update_fields=["latitude", "longitude"])
    # Parent stations inherit a missing GPS from their children when available.
    return created


def load_kiosks(wb, site, log):
    S = "4. Registre_Actifs_BF&Conn"
    ws = wb.f("assets", S)
    seen = {}
    for i in range(5, ws.max_row + 1):
        bid = clean(ws[f"B{i}"].value)
        if not bid:
            continue
        m = re.match(r"(BF|CP)\s*0*(\d+)", bid, re.I)
        if not m:
            log.skip(wb.ref("assets", S, f"B{i}"), f"Identifiant non reconnu « {bid} »")
            continue
        kind, num = m.group(1).upper(), int(m.group(2))
        typ = AssetType.KIOSK if kind == "BF" else AssetType.PRIVATE_CONNECTION
        code = f"{site.code}-BF-{num:02d}" if kind == "BF" else f"{site.code}-CP-{num:03d}"
        lat, lon, alt = ws[f"D{i}"].value, ws[f"C{i}"].value, ws[f"E{i}"].value
        flags = []
        key = (lat, lon)
        if key in seen:
            flags.append("A16")
        seen[key] = code
        g = clean(ws[f"G{i}"].value) or ""
        taps = re.search(r"(\d+)\s*robinet", g)
        attrs = {"id_excel": bid, "type": g, "robinets": int(taps.group(1)) if taps else None,
                 "dn_raccordement": clean(ws[f"H{i}"].value), "reference": clean(ws[f"F{i}"].value),
                 "beneficiaires": clean(ws[f"I{i}"].value)}
        cond = {"bon": Condition.GOOD, "mauvais": Condition.POOR}.get(str(ws[f"K{i}"].value or "").strip().lower(), Condition.UNKNOWN)
        if not ws[f"K{i}"].value:
            flags.append("A17")
        name = f"Borne fontaine {kind}{num:02d}" if kind == "BF" else f"Connexion privée {kind}{num}"
        _upsert_asset(site, code, log, wb.ref("assets", S, f"B{i}"), bid, name=name, type=typ,
                      latitude=d(round(lat, 7)) if lat is not None else None, longitude=d(round(lon, 7)) if lon is not None else None,
                      altitude_m=d(round(alt, 2)) if alt is not None else None, condition=cond,
                      built_by="" if clean(ws[f"J{i}"].value) in (None, "NA") else clean(ws[f"J{i}"].value),
                      attributes=attrs, flags=flags)


# ------------------------------------------------------------ network (sheets 2 & 3)

SPECIAL_NODES = {
    "bosco lac": NodeKind.PUMP_STATION,
    "cv1 pompage": NodeKind.JUNCTION,
    "sr": NodeKind.RESERVOIR_OUTLET,
    "lac": NodeKind.OUTFALL,
}


def _norm_node(raw_code):
    """Returns (code, note, kind)."""
    if raw_code is None:
        return None, "", None
    code = str(raw_code).strip()
    note = ""
    m = re.match(r"^([\d.]+)\s*\((.+)\)$", code)
    if m:
        code, note = m.group(1), m.group(2)
    bf = re.match(r"^(BF|CP)\s*0*(\d+)$", code, re.I)
    if bf:
        return f"{bf.group(1).upper()}{int(bf.group(2)):02d}", note, NodeKind.DELIVERY
    kind = SPECIAL_NODES.get(code.lower(), NodeKind.JUNCTION)
    return code, note, kind


def _node(site, cell_or_code, log, ref, cache):
    raw = node_code(cell_or_code) if hasattr(cell_or_code, "value") else cell_or_code
    code, note, kind = _norm_node(raw)
    if code is None:
        return None
    if code not in cache:
        flags = ["A02"] if code == "1.10" else []
        node, _ = Node.objects.update_or_create(site=site, code=code, defaults={"kind": kind, "source_ref": ref, "note": note,
                                                                               "raw_label": str(raw), "flags": flags})
        cache[code] = node
        log.counts["nodes"] += 1
    return cache[code]


def load_network(wb, site, log):
    S = "2. Registre_Actifs_Regul&tuy"
    ws = wb.f("assets", S)
    dn_cols = {}
    for c in range(col_idx("F"), col_idx("L") + 1):
        m = re.search(r"DN\s*(\d+)", str(ws.cell(5, c).value or ""))
        if m:
            dn_cols[c] = int(m.group(1))
    cache = {}
    for i in range(6, ws.max_row + 1):
        from_cell, to_cell = ws[f"C{i}"], ws[f"D{i}"]
        if from_cell.value in (None, "") and to_cell.value in (None, ""):
            continue
        if str(from_cell.value or "").startswith("Total"):
            break
        ref = wb.ref("assets", S, f"B{i}")
        a = _node(site, from_cell, log, wb.ref("assets", S, f"C{i}"), cache) if from_cell.value not in (None, "") else None
        b = _node(site, to_cell, log, wb.ref("assets", S, f"D{i}"), cache)
        comment = clean(ws[f"N{i}"].value) or ""
        lengths = [(dn_cols[c], ws.cell(i, c).value) for c in dn_cols if isinstance(ws.cell(i, c).value, (int, float))]
        if not lengths:
            log.skip(ref, f"Tronçon {a.code if a else '?'} → {b.code} sans longueur")
            continue
        flags = []
        if a is None:
            flags.append("A04")
        if not clean(ws[f"E{i}"].value):
            flags.append("A07")
        if "DN 150" in comment or "DN150" in comment:
            flags.append("A06")
        for dn, length in lengths:
            role = PipeRole.MAIN
            if b.kind == NodeKind.DELIVERY:
                role = PipeRole.SERVICE
            elif b.kind == NodeKind.OUTFALL or (len(lengths) > 1 and dn == min(x[0] for x in lengths)):
                role = PipeRole.OVERFLOW
            code = f"{a.code if a else '?'}>{b.code}#DN{dn}"
            PipeSegment.objects.update_or_create(
                site=site, code=code,
                defaults=dict(from_node=a, to_node=b, dn=dn, material=clean(ws[f"E{i}"].value) or "", length_m=d(length),
                              role=role, note=comment, source_ref=ref, flags=flags))
            log.counts["pipe_segments"] += 1
            if flags:
                log.flag(ref, code, *flags)
    # Kiosk delivery nodes point at their kiosk asset.
    for code, node in cache.items():
        if node.kind == NodeKind.DELIVERY:
            m = re.match(r"(BF|CP)(\d+)", code)
            asset_code = f"{site.code}-BF-{int(m.group(2)):02d}" if m.group(1) == "BF" else f"{site.code}-CP-{int(m.group(2)):03d}"
            Asset.objects.filter(code=asset_code).update(node=node)
    station = Asset.objects.filter(site=site, type=AssetType.PUMP_STATION, name__icontains="bosco").first()
    if station and "Bosco Lac" in cache:
        Asset.objects.filter(pk=station.pk).update(node=cache["Bosco Lac"])

    # Sheet 3: fittings per node.
    S3 = "3. Registre_Actifs_OrgRegu"
    ws3 = wb.f("assets", S3)
    headers = {c: clean(ws3.cell(5, c).value) for c in range(col_idx("F"), col_idx("AD") + 1)}
    for i in range(6, ws3.max_row + 1):
        cell = ws3[f"C{i}"]
        if cell.value in (None, "") or str(ws3[f"B{i}"].value).startswith("Total"):
            continue
        node = _node(site, cell, log, wb.ref("assets", S3, f"C{i}"), cache)
        state = clean(ws3[f"E{i}"].value)
        if state:
            node.condition = Condition.POOR if re.search(r"fuite|remplac|mauvais", state, re.I) else node.condition
            node.note = (node.note + " | " if node.note else "") + state
            node.flags = sorted(set(node.flags + ["A19"]))
            loc = clean(ws3[f"D{i}"].value)
            if loc:
                node.note += f" | {loc.replace(chr(10), ' ')}"
            node.save()
        for c, desc in headers.items():
            q = ws3.cell(i, c).value
            if isinstance(q, (int, float)) and q > 0 and desc:
                m = re.search(r"DN\s*(\d+)", desc)
                Fitting.objects.update_or_create(node=node, description=desc,
                                                 defaults={"dn": int(m.group(1)) if m else None, "quantity": int(q),
                                                           "source_ref": wb.ref("assets", S3, f"{ws3.cell(i, c).column_letter}{i}")})
                log.counts["fittings"] += 1


# ------------------------------------------------------------ people (workbook 4)

ROLE_RULES = [
    (r"adjoint", Role.ADJOINT),
    (r"responsable technique", Role.RESP_TECH),
    (r"zone\s*\d", Role.ZONE_TECH),
    (r"stockage", Role.STORAGE_FOCAL),
    (r"pompage", Role.PUMP_FOCAL),
    (r"sse|santé", Role.SSE),
    (r"base des donn", Role.DATA_OFFICER),
]


def load_people(wb, site, log):
    S = "1. Pers tech perm"
    ws = wb.f("staff", S)
    titles = Counter(clean(ws[f"D{i}"].value) for i in range(4, 13))
    for i in range(4, ws.max_row + 1):
        title = clean(ws[f"D{i}"].value)
        if not title:
            continue
        duties = clean(ws[f"E{i}"].value) or ""
        text = f"{title} {duties}".lower()
        role = next((r_ for pat, r_ in ROLE_RULES if re.search(pat, text)), Role.ZONE_TECH)
        z = re.search(r"zone\s*(\d+)", duties, re.I)
        zone = Zone.objects.filter(site=site, code=f"Z{z.group(1)}").first() if z else None
        flags = []
        if titles[title] > 1:
            flags.append("P01")
        if not clean(ws[f"C{i}"].value):
            flags.append("P02")
        ref = wb.ref("staff", S, f"B{i}")
        Person.objects.update_or_create(site=site, source_ref=ref, defaults=dict(
            full_name=clean(ws[f"C{i}"].value) or "", title=title, role=role, duties=duties, zone=zone, permanent=True, flags=flags))
        log.counts["people"] += 1
    S2 = "2. Pers tech non perm"
    ws = wb.f("staff", S2)
    for i in range(4, ws.max_row + 1):
        title = clean(ws[f"D{i}"].value)
        if not title:
            continue
        start = ws[f"G{i}"].value.date() if isinstance(ws[f"G{i}"].value, dt.datetime) else None
        dur = ws[f"F{i}"].value
        ref = wb.ref("staff", S2, f"B{i}")
        Person.objects.update_or_create(site=site, source_ref=ref, defaults=dict(
            full_name=clean(ws[f"C{i}"].value) or "", title=title, role=Role.CONTRACTOR, duties=clean(ws[f"E{i}"].value) or "",
            permanent=False, contract_start=start,
            contract_end=start + dt.timedelta(days=int(dur)) if start and isinstance(dur, (int, float)) else None,
            flags=["P02", "P03"]))
        log.counts["people"] += 1
    S3 = "3. Besoin en personnel"
    ws = wb.f("staff", S3)
    for i in range(4, ws.max_row + 1):
        title = clean(ws[f"C{i}"].value)
        ref = wb.ref("staff", S3, f"B{i}")
        if not title:
            if ws[f"G{i}"].value is not None:
                log.skip(ref, "Besoin sans titre (durée/date seules)")
            continue
        start = ws[f"H{i}"].value.date() if isinstance(ws[f"H{i}"].value, dt.datetime) else None
        dur = ws[f"G{i}"].value
        StaffingNeed.objects.update_or_create(site=site, source_ref=ref, defaults=dict(
            title=title, duties=clean(ws[f"D{i}"].value) or "", headcount=ws[f"E{i}"].value,
            permanent=None, duration_value=int(dur) if isinstance(dur, (int, float)) else None, start=start,
            end=start + dt.timedelta(days=int(dur)) if start and isinstance(dur, (int, float)) else None,
            comment=clean(ws[f"J{i}"].value) or "", flags=["P03", "P04"]))
        log.counts["staffing_needs"] += 1


# ------------------------------------------------------------ stock (workbook 3)

def load_stock(wb, site, log):
    specs = [
        ("1. Eq &outil pour amél la perf.", StockCategory.PERFORMANCE, "B", "C", "D", None, ("E", "F", "G", "H", "I"), "J", None),
        ("2. Outils & Mats pour O&M", StockCategory.OM_TOOLS, "B", "D", "E", "F", ("G", "H", "I", "J", "K"), "L", None),
        ("3. Produit chim trait de l'eau", StockCategory.CHEMICAL, None, "B", "D", None, ("E", "F", "G", "H", "I"), "J", "C"),
    ]
    n = 0
    for sheet, category, group_col, name_col, unit_col, rent_col, qty_cols, notes_col, monthly_col in specs:
        ws = wb.f("stock", sheet)
        group = ""
        for i in range(5, ws.max_row + 1):
            if group_col and clean(ws[f"{group_col}{i}"].value):
                group = strip_number(clean(ws[f"{group_col}{i}"].value))
            name = clean(ws[f"{name_col}{i}"].value)
            ref = wb.ref("stock", sheet, f"{name_col}{i}")
            if not name or (isinstance(name, str) and is_placeholder(name)) or isinstance(name, (int, float)):
                continue
            cat = category
            if category == StockCategory.OM_TOOLS and re.search(r"protection", group, re.I):
                cat = StockCategory.PPE
            elif category == StockCategory.OM_TOOLS and re.search(r"logistique", group, re.I):
                cat = StockCategory.LOGISTICS
            n += 1
            code = f"ART-{n:03d}"
            qty = {k: ws[f"{c}{i}"].value for k, c in zip(("stock", "sortie", "entree", "restant", "besoin"), qty_cols)}
            flags = []
            original = {}
            if any(isinstance(v, (int, float)) for k, v in qty.items() if k != "restant") or is_formula(qty["restant"]):
                flags.append("S01")
                original = {k: v for k, v in qty.items() if v is not None}
                log.flag(ref, f"{code} {strip_number(name)} — quantités d'origine non importées : {original}", "S01")
            item, _ = StockItem.objects.update_or_create(
                site=site, source_ref=ref,
                defaults=dict(code=code, category=cat, group=group, name=strip_number(name),
                              unit=clean(ws[f"{unit_col}{i}"].value) or "", notes=clean(ws[f"{notes_col}{i}"].value) or "",
                              monthly_requirement=d(ws[f"{monthly_col}{i}"].value) if monthly_col else None, flags=flags))
            log.counts["stock_items"] += 1


# ------------------------------------------------------------ KPI workbook

KPI = "O&M KPI"
MONTH_COLS = [chr(ord("C") + k) for k in range(12)]  # C..N

KPI_ROWS = {
    5: "downtime_pump", 6: "downtime_pipe", 7: "downtime_power", 8: "downtime_planned",
    13: "incidents_reported",
    18: f"rca_{FailureCause.VANDALISM}", 19: f"rca_{FailureCause.OVERPRESSURE}", 20: f"rca_{FailureCause.SHALLOW_PIPE}",
    21: f"rca_{FailureCause.ILLEGAL_CONNECTION}", 22: f"rca_{FailureCause.MISHANDLING}", 23: f"rca_{FailureCause.POOR_PIPE_QUALITY}",
    24: f"rca_{FailureCause.POOR_BACKFILL}", 25: f"rca_{FailureCause.GROUND_MOVEMENT}", 26: f"rca_{FailureCause.POOR_INSTALLATION}",
    27: f"rca_{FailureCause.WATER_HAMMER}", 28: f"rca_{FailureCause.FAULTY_CONNECTION}",
    30: "volume_introduced", 31: "volume_billed",
    36: f"nrw_{NRWCause.PIPE_LEAK}", 37: f"nrw_{NRWCause.PIPE_BURST}", 38: f"nrw_{NRWCause.RESERVOIR_OVERFLOW}",
    39: f"nrw_{NRWCause.NETWORK_FLUSH}", 40: f"nrw_{NRWCause.DRAINING}", 41: f"nrw_{NRWCause.RESERVOIR_CLEANING}",
    42: f"nrw_{NRWCause.FIREFIGHTING}", 43: f"nrw_{NRWCause.ILLEGAL_BRANCH}", 44: f"nrw_{NRWCause.FAULTY_METER}",
    45: f"nrw_{NRWCause.MISCALIBRATED_METER}", 46: f"nrw_{NRWCause.ILLEGAL_CONNECTION}", 47: f"nrw_{NRWCause.READING_ERROR}",
    48: f"nrw_{NRWCause.UNBILLED_CONSUMPTION}",
    50: "pm_planned_CAPTAGE", 51: "pm_planned_POMPAGE", 52: "pm_planned_RESERVOIR", 53: "pm_planned_RESEAU", 54: "pm_planned_BF",
    59: "kwh", 61: "fuel_l",
    71: "cost_urgent", 72: "cost_corrective", 73: "cost_preventive", 74: "cost_support",
}


def first_daily_date(wb):
    ws = wb.v("kpi", "POMPES")
    dates = [c.value.date() for c in ws[2] if isinstance(c.value, dt.datetime)]
    return min(dates) if dates else None


def load_kpi_history(wb, site, log, year, today, actual_until=None):
    """Monthly totals before the daily sheets start = ACTUAL (to confirm); from then until today = PROVISIONAL; future = skipped."""
    ws = wb.f("kpi", KPI)
    start_daily = first_daily_date(wb)
    actual_until = actual_until or (dt.date(start_daily.year, start_daily.month, 1) if start_daily else dt.date(year, 1, 1))
    for row, metric in KPI_ROWS.items():
        for k, col in enumerate(MONTH_COLS):
            month = dt.date(year, k + 1, 1)
            cell = ws[f"{col}{row}"]
            ref = wb.ref("kpi", KPI, f"{col}{row}")
            v = cell.value
            if v in (None, ""):
                continue
            if is_formula(v):
                log.skip(ref, f"Formule {v} (valeur dérivée, non importée)")
                continue
            if not isinstance(v, (int, float)):
                continue
            if month > today:
                log.skip(ref, f"Mois futur ({month:%m/%Y}) — valeur {v} non importée")
                continue
            status = MonthlyAggregate.Status.ACTUAL if month < actual_until else MonthlyAggregate.Status.PROVISIONAL
            MonthlyAggregate.objects.update_or_create(
                site=site, month=month, metric=metric,
                defaults={"value": d(v), "status": status, "source_ref": ref,
                          "note": "Historique Excel à confirmer" if status == "ACTUAL" else "Provisoire : non utilisé dans les KPI"})
            log.counts[f"history_{status.lower()}"] += 1
    # Budget envelope (row 70) = plan, all months.
    for k, col in enumerate(MONTH_COLS):
        v = ws[f"{col}70"].value
        if isinstance(v, (int, float)):
            MonthlyBudget.objects.update_or_create(site=site, month=dt.date(year, k + 1, 1),
                                                   defaults={"amount_usd": d(v), "source_ref": wb.ref("kpi", KPI, f"{col}70")})
            log.counts["monthly_budgets"] += 1
    # Tariffs hidden in formulas C63 (=C59*0.25) and C64 (=C61*1.7).
    for cell, kind in (("C63", Tariff.Kind.ELECTRICITY), ("C64", Tariff.Kind.FUEL)):
        m = re.search(r"\*\s*([\d.]+)", str(ws[cell].value))
        if m:
            Tariff.objects.update_or_create(site=site, kind=kind, valid_from=dt.date(year, 1, 1),
                                            defaults={"price_usd": d(m.group(1)), "source_ref": wb.ref("kpi", KPI, cell)})
            log.counts["tariffs"] += 1
    log.notes.append(f"Historique mensuel : mois avant {actual_until:%m/%Y} = « validé » (à confirmer), "
                     f"de {actual_until:%m/%Y} à aujourd'hui = « provisoire », mois futurs non importés.")


def _block_width(ws):
    starts = [c.column for c in ws[2] if isinstance(c.value, dt.datetime)]
    return starts[1] - starts[0] if len(starts) > 1 else None, starts


def load_daily(wb, site, log):
    """Only real daily values: POMPES and STOCKAGE (RESEAU is autofilled test data, see K19)."""
    pumps = {a.name: a for a in Asset.objects.filter(site=site, type=AssetType.PUMP)}
    caprari = next((a for n, a in pumps.items() if "CAPRARI" in n.upper()), None)
    shimge = sorted((a for n, a in pumps.items() if "SHIMGE" in n.upper()), key=lambda a: a.code)
    station = Asset.objects.filter(site=site, type=AssetType.PUMP_STATION, name__icontains="bosco").first()
    ws = wb.f("kpi", "POMPES")
    wv = wb.v("kpi", "POMPES")
    width, starts = _block_width(ws)
    for start in starts:
        day = ws.cell(2, start).value.date()
        for row in (4, 5, 6, 7):
            vals = [wv.cell(row, start + k).value for k in range(width)]
            raw = {k: (v if isinstance(v, (int, float)) else None) for k, v in enumerate(vals)}
            if all(v in (None, 0) for v in raw.values()):
                continue
            label = str(ws.cell(row, 1).value or "")
            flow = raw.get(2)
            flags = []
            if flow is not None and flow <= 100 and shimge:
                asset = shimge[0]
                if "CAPRARI" in label.upper():
                    flags.append("K18")
            else:
                asset = caprari
            if asset is None:
                continue
            hours = raw.get(0)
            ref = wb.ref("kpi", "POMPES", f"{ws.cell(row, start).column_letter}{row}")
            volume = d(flow) * d(hours) if flow is not None and hours is not None else None
            if DailyReading.objects.filter(asset=asset, date=day).exclude(source=RecordSource.IMPORT).exists():
                log.skip(ref, f"Relevé {day} de {asset.code} déjà saisi dans l'application : conservé")
                continue
            DailyReading.objects.update_or_create(
                asset=asset, date=day,
                defaults=dict(site=site, source=RecordSource.IMPORT, source_ref=ref, flags=flags, hours_run=d(hours),
                              pressure_bar=d(raw.get(1)), flow_m3h=d(flow), volume_m3=volume, kwh=d(raw.get(4)),
                              fuel_l=d(raw.get(5)), chlorine_g=d(raw.get(7)), operator="(import Excel)"))
            log.counts["daily_readings"] += 1
            if flags:
                log.flag(ref, f"Relevé {day} → {asset.code}", *flags)
            if raw.get(6) is not None:
                WaterQualityTest.objects.update_or_create(
                    site=site, asset=station, date=day, parameter=QualityParameter.RESIDUAL_CHLORINE, source=RecordSource.IMPORT,
                    source_ref=ref, defaults={"value": d(raw[6]), "compliant": is_compliant(site, QualityParameter.RESIDUAL_CHLORINE, d(raw[6]), station)})
    reservoirs = list(Asset.objects.filter(site=site, type=AssetType.RESERVOIR).order_by("code"))
    ws = wb.f("kpi", "STOCKAGE")
    wv = wb.v("kpi", "STOCKAGE")
    width, starts = _block_width(ws)
    for start in starts:
        day = ws.cell(2, start).value.date()
        for row in (4, 5, 6):
            label = str(ws.cell(row, 1).value or "")
            vals = [wv.cell(row, start + k).value for k in range(width)]
            if all(not isinstance(v, (int, float)) for v in vals):
                continue
            cap = re.search(r"(\d+)\s*m3", label)
            asset = next((r_ for r_ in reservoirs if cap and r_.capacity_value == Decimal(cap.group(1))), None)
            if asset is None:
                log.skip(wb.ref("kpi", "STOCKAGE", f"A{row}"), f"Réservoir « {label} » non reconnu")
                continue
            ref = wb.ref("kpi", "STOCKAGE", f"{ws.cell(row, start).column_letter}{row}")
            num = lambda k: d(vals[k]) if k < len(vals) and isinstance(vals[k], (int, float)) else None  # noqa: E731
            if DailyReading.objects.filter(asset=asset, date=day).exclude(source=RecordSource.IMPORT).exists():
                log.skip(ref, f"Relevé {day} de {asset.code} déjà saisi dans l'application : conservé")
                continue
            DailyReading.objects.update_or_create(
                asset=asset, date=day,
                defaults=dict(site=site, source=RecordSource.IMPORT, source_ref=ref, volume_in_m3=num(0), volume_out_m3=num(1),
                              pressure_in_bar=num(2), pressure_out_bar=num(3), chlorine_g=num(5), operator="(import Excel)",
                              flags=["K16"]))
            log.counts["daily_readings"] += 1
            if num(4) is not None:
                WaterQualityTest.objects.update_or_create(
                    site=site, asset=asset, date=day, parameter=QualityParameter.RESIDUAL_CHLORINE, source=RecordSource.IMPORT,
                    source_ref=ref, defaults={"value": num(4), "compliant": is_compliant(site, QualityParameter.RESIDUAL_CHLORINE, num(4), asset)})
    log.skip(wb.ref("kpi", "RESEAU", "B4:NK5"), "Feuille RESEAU : 106 lignes générées par recopie incrémentale (K19), non importées")


BUDGET_CATEGORIES = [
    (r"personn?el", BudgetLine.Category.STAFF), (r"logistique", BudgetLine.Category.LOGISTICS),
    (r"outils", BudgetLine.Category.TOOLS), (r"matériel|materiel", BudgetLine.Category.MATERIALS),
    (r"énergie|energie", BudgetLine.Category.ENERGY), (r"communication", BudgetLine.Category.COMMUNICATION),
]
MT = {"exploitation de routine": "ROUTINE", "maintenance urgente": "URGENT", "maintenance corrective": "CORRECTIVE",
      "maintenance préventive": "PREVENTIVE", "autres activités de support": "SUPPORT"}


def load_budget(wb, site, log):
    S = "Besoins et budget E&M_mensuel"
    ws = wb.f("kpi", S)
    month = parse_month_year(str(ws["B3"].value or "")) or dt.date.today().replace(day=1)
    cat = BudgetLine.Category.OTHER
    for i in range(5, 30):
        b = clean(ws[f"B{i}"].value)
        if b:
            cat = next((c for pat, c in BUDGET_CATEGORIES if re.search(pat, b, re.I)), BudgetLine.Category.OTHER)
        act = clean(ws[f"C{i}"].value)
        ref = wb.ref("kpi", S, f"C{i}")
        if not act or is_placeholder(act):
            continue
        qty, pu = ws[f"G{i}"].value, ws[f"H{i}"].value
        flags = [] if isinstance(qty, (int, float)) and isinstance(pu, (int, float)) else ["K25"]
        BudgetLine.objects.update_or_create(site=site, source_ref=ref, defaults=dict(
            month=month, category=cat, activity=strip_number(act), purpose=clean(ws[f"D{i}"].value) or "",
            maintenance_type=MT.get(str(ws[f"E{i}"].value or "").strip().lower(), ""), unit=clean(ws[f"F{i}"].value) or "",
            quantity=d(qty) if isinstance(qty, (int, float)) else None, unit_price_usd=d(pu) if isinstance(pu, (int, float)) else None,
            responsible=clean(ws[f"J{i}"].value) or "", supplier=clean(ws[f"K{i}"].value) or "",
            start=ws[f"L{i}"].value.date() if isinstance(ws[f"L{i}"].value, dt.datetime) else None,
            end=ws[f"M{i}"].value.date() if isinstance(ws[f"M{i}"].value, dt.datetime) else None, flags=flags))
        log.counts["budget_lines"] += 1


FREQ = {"I": ActionPlanTask.Frequency.DAILY, "II": ActionPlanTask.Frequency.WEEKLY, "III": ActionPlanTask.Frequency.MONTHLY,
        "IV": ActionPlanTask.Frequency.PERIODIC}


def load_plan(wb, site, log):
    S = "Plan d'Action et Calendrier"
    ws = wb.f("kpi", S)
    wv = wb.v("kpi", S)
    day_cols = {c.column: c.value.date() for c in ws[7] if isinstance(c.value, dt.datetime)}
    year = min(day_cols.values()).year if day_cols else dt.date.today().year
    progress_col = next((c.column for c in ws[6] if "progr" in str(c.value or "").lower()), None)
    status_col = progress_col + 1 if progress_col else None
    freq = ActionPlanTask.Frequency.DAILY
    section = sub = ""
    reservoirs = {a.name.upper(): a for a in Asset.objects.filter(site=site, type__in=[AssetType.STORAGE_SITE, AssetType.RESERVOIR])}
    order = 0
    for i in range(8, ws.max_row + 1):
        b, c = clean(ws[f"B{i}"].value), clean(ws[f"C{i}"].value)
        ref = wb.ref("kpi", S, f"C{i}")
        if isinstance(b, str) and b in FREQ:
            freq, section, sub = FREQ[b], c or "", ""
            continue
        marks = [dt_ for col, dt_ in day_cols.items() if ws.cell(i, col).value == 1]
        typed_date = ws.cell(i, 7).value
        is_header = c and re.fullmatch(r"[A-ZÉÈ0-9 \-]+(M3|m3)?", c.strip()) and ws[f"D{i}"].value is None
        if is_header:
            sub = c.strip()
            if marks:
                log.skip(ref, f"En-tête de section « {sub} » avec {len(marks)} jour(s) coché(s) par erreur")
            continue
        if not c:
            if b or ws[f"D{i}"].value is not None:
                log.skip(ref, f"Tâche {b or ''} sans description (durée {ws[f'D{i}'].value}, date {typed_date})")
            continue
        flags = []
        asset = None
        if sub:
            key = next((k for k in reservoirs if sub.split()[0] in k), None)
            asset = reservoirs.get(key) if key else None
            if asset is None and re.search(r"m3", sub, re.I):
                flags.append("K22")
        if "Nyabyunyu" in c and sub and "NYABYUNYU" not in sub.upper() and "K22" not in flags:
            flags.append("K22")
        progress = wv.cell(i, progress_col).value if progress_col else None
        if progress_col and is_formula(ws.cell(i, progress_col).value) and "#REF" in str(ws.cell(i, progress_col).value):
            progress = None
            flags.append("K21")
        start = min(marks) if marks else (typed_date.date() if isinstance(typed_date, dt.datetime) else None)
        dur = wv[f"D{i}"].value
        order += 1
        ActionPlanTask.objects.update_or_create(site=site, year=year, source_ref=ref, defaults=dict(
            code=str(b or ""), section=f"{section} — {sub}" if sub else section, title=c, frequency=freq, asset=asset,
            start=start, end=max(marks) if marks else None, duration_days=int(dur) if isinstance(dur, (int, float)) else None,
            scheduled_dates=[x.isoformat() for x in sorted(marks)], order=order,
            progress_pct=d(progress) if isinstance(progress, (int, float)) else None,
            status_note=clean(ws.cell(i, status_col).value) or "" if status_col else "",
            comment=clean(ws.cell(i, status_col + 1).value) or "" if status_col else "", flags=flags))
        log.counts["plan_tasks"] += 1
        if flags:
            log.flag(ref, c, *flags)


# ------------------------------------------------------------ defaults

DEFAULT_THRESHOLDS = [
    # parameter, asset_type, min, max, note
    (QualityParameter.RESIDUAL_CHLORINE, AssetType.KIOSK, "0.2", "0.5",
     "Point de distribution : 0,2–0,5 mg/L (norme Sphère). À confirmer par le Responsable technique."),
    (QualityParameter.RESIDUAL_CHLORINE, AssetType.RESERVOIR, "0.2", "1.0",
     "Sortie réservoir : 0,2–1,0 mg/L. À confirmer par le Responsable technique."),
    (QualityParameter.RESIDUAL_CHLORINE, "", "0.2", "1.0", "Valeur générique. À confirmer."),
    (QualityParameter.TURBIDITY, "", None, "5", "OMS : < 5 NTU. À confirmer."),
]


def load_defaults(site, log):
    for param, atype, mn, mx, note in DEFAULT_THRESHOLDS:
        QualityThreshold.objects.update_or_create(site=site, parameter=param, asset_type=atype, asset=None,
                                                  defaults={"min_value": d(mn), "max_value": d(mx), "note": note, "to_confirm": True})
        log.counts["quality_thresholds"] += 1
    log.notes.append("Seuils de qualité : valeurs par défaut marquées « à confirmer » (la colonne « Valeur acceptable » des fiches est vide).")


@transaction.atomic
def import_all(wb, year, today, site_code="GO", site_name="Goma Ouest"):
    log = Log()
    site = load_site(wb, log, site_code, site_name)
    load_defaults(site, log)
    load_assets(wb, site, log)
    load_kiosks(wb, site, log)
    load_network(wb, site, log)
    load_people(wb, site, log)
    load_stock(wb, site, log)
    load_kpi_history(wb, site, log, year, today)
    load_daily(wb, site, log)
    load_budget(wb, site, log)
    load_plan(wb, site, log)
    return site, log
