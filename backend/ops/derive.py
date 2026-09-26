"""Turn a FormSubmission into normalised records. Idempotent.

Daily readings are shared: one row per asset and day, recomputed from *all*
non-rejected sheets that mention that asset on that day (two operator shifts =
two sheets, one reading). Each submission remembers which (asset, day) pairs it
fed (`derived_keys`) so an edit (new date, removed pump row) or a rejection
recomputes the old pairs too and never leaves stale values behind.

Everything else (checks, quality tests, complaints, incident, stock movements,
expense, work orders) is owned by one submission and replaced on re-derivation.
"""
import datetime as dt
import re
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.models import Asset, AssetType, Node, Sequence, Zone
from stock.models import StockItem, StockMovement

from .forms import get_path, to_date, to_datetime, to_decimal, to_time
from .models import (
    Complaint,
    DailyReading,
    Expense,
    FormSubmission,
    FormType,
    Incident,
    QualityParameter,
    RecordSource,
    SafetyCheck,
    WaterQualityTest,
    WorkOrder,
)
from .quality import is_compliant

OK_VALUES = {"BON": True, "MAUVAIS": False, "OUI": True, "NON": False}
# Checklist rows where "Oui" is the BAD answer (e.g. "Présence de fuite").
NEGATIVE_ROWS = {"leak", "intrusion", "cracks", "leaks"}


def _active(qs):
    return qs.exclude(status=FormSubmission.Status.REJECTED)


def _asset(site, code):
    if not code:
        return None
    return Asset.objects.filter(site=site, code=code).first()


def _zone(site, code):
    if not code:
        return None
    return Zone.objects.filter(site=site, code=code).first()


def _node(site, code):
    if not code:
        return None
    return Node.objects.filter(site=site, code=str(code)).first()


def hours_between(start, stop):
    """Hours between two HH:MM times; crossing midnight adds 24 h."""
    if start is None or stop is None:
        return None
    a = start.hour * 60 + start.minute
    b = stop.hour * 60 + stop.minute
    if b < a:
        b += 24 * 60
    return (Decimal(b - a) / Decimal(60)).quantize(Decimal("0.01"))


def _mean(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return (sum(values) / len(values)).quantize(Decimal("0.01"))


def _sum(values):
    values = [v for v in values if v is not None]
    return sum(values) if values else None


def _to_int(value):
    d = to_decimal(value)
    return int(d) if d is not None else None


# ------------------------------------------------------------------ shared daily readings

SUM_FIELDS = {"hours_run", "volume_m3", "volume_in_m3", "volume_out_m3", "kwh", "fuel_l", "chlorine_g"}
MEAN_FIELDS = {"pressure_bar", "pressure_in_bar", "pressure_out_bar", "flow_m3h", "current_a", "level_pct"}


def _contrib(out, code, **values):
    slot = out.setdefault(code, defaultdict(list))
    for k, v in values.items():
        if v not in (None, ""):
            slot[k].append(v)


def contributions(sub):
    """{asset_code: {field: [values]}} that this sheet adds to the daily readings of its date."""
    out = {}
    p = sub.payload or {}
    if sub.form_type == FormType.POMPAGE:
        for row in p.get("pumps") or []:
            if not row.get("pump"):
                continue
            hours = hours_between(to_time(row.get("start")), to_time(row.get("stop")))
            flow = to_decimal(row.get("flow_m3h"))
            volume = to_decimal(row.get("volume_m3"))
            if volume is None and flow is not None and hours is not None:
                volume = (flow * hours).quantize(Decimal("0.01"))
            _contrib(out, row["pump"], hours_run=hours, volume_m3=volume, flow_m3h=flow,
                     pressure_bar=to_decimal(row.get("pressure_bar")), current_a=to_decimal(row.get("current_a")),
                     observations=row.get("observations"))
        station = get_path(p, "general.station")
        if station:
            energy = p.get("energy") or {}
            _contrib(out, station, kwh=to_decimal((energy.get("snel") or {}).get("quantity")),
                     fuel_l=to_decimal((energy.get("genset") or {}).get("quantity")),
                     chlorine_g=to_decimal(((p.get("quality") or {}).get("chlorine_g") or {}).get("value")),
                     observations=get_path(p, "maintenance.maintenance_done"), _touch=True)
    elif sub.form_type == FormType.STOCKAGE:
        res = get_path(p, "general.reservoir")
        if res:
            d = p.get("daily") or {}
            rows = p.get("operations") or []
            _contrib(out, res, volume_in_m3=to_decimal(d.get("volume_in_m3")), volume_out_m3=to_decimal(d.get("volume_out_m3")),
                     pressure_in_bar=to_decimal(d.get("pressure_in_bar")), pressure_out_bar=to_decimal(d.get("pressure_out_bar")),
                     chlorine_g=to_decimal(((p.get("quality") or {}).get("chlorine_g") or {}).get("value")),
                     observations=get_path(p, "incidents.incidents"), _touch=True)
            for row in rows:
                _contrib(out, res, level_pct=to_decimal(row.get("level_pct")), pressure_bar=to_decimal(row.get("pressure_bar")))
    elif sub.form_type == FormType.RESEAU_BF:
        for row in p.get("kiosks") or []:
            v = to_decimal(row.get("volume_sold_m3"))
            if row.get("kiosk") and v is not None:
                _contrib(out, row["kiosk"], volume_m3=v)
    return out


def recompute_readings(site, form_type, keys):
    """Rebuild the DailyReading of each (asset_code, iso_date) from every active sheet of that day."""
    for code, iso in sorted({tuple(k) for k in keys}):
        day = dt.date.fromisoformat(iso)
        asset = _asset(site, code)
        if asset is None:
            continue
        merged = defaultdict(list)
        latest = None
        for s in _active(FormSubmission.objects.filter(site=site, form_type=form_type, date=day)).order_by("updated_at"):
            part = contributions(s).get(code)
            if not part:
                continue
            latest = s
            for k, vals in part.items():
                merged[k].extend(vals)
        existing = DailyReading.objects.filter(asset=asset, date=day).first()
        if latest is None:
            if existing and existing.source != RecordSource.IMPORT:
                existing.delete()
            continue
        fields = {f: (_sum(merged.get(f, [])) if f in SUM_FIELDS else _mean(merged.get(f, []))) for f in SUM_FIELDS | MEAN_FIELDS}
        operators = sorted({get_path(s.payload, "general.operator") or "" for s in
                            _active(FormSubmission.objects.filter(site=site, form_type=form_type, date=day))} - {""})
        DailyReading.objects.update_or_create(
            asset=asset, date=day,
            defaults=dict(site=site, submission=latest, source=latest.source, source_ref="", flags=[],
                          operator=", ".join(operators)[:160], observations=" | ".join(str(o) for o in merged.get("observations", [])),
                          **fields))


def derive_readings(sub, active=True):
    new_keys = [[code, sub.date.isoformat()] for code in contributions(sub)] if active else []
    old_keys = sub.derived_keys or []
    recompute_readings(sub.site, sub.form_type, old_keys + new_keys)
    FormSubmission.objects.filter(pk=sub.pk).update(derived_keys=new_keys)
    sub.derived_keys = new_keys


# ------------------------------------------------------------------ owned records

def _checks(submission, section_key, rows_answer_col, asset=None, zone=None, location_col=None):
    data = submission.payload.get(section_key) or {}
    for row_key, values in data.items():
        values = values or {}
        answer = values.get(rows_answer_col)
        if answer in (None, "") and not any(values.values()):
            continue
        ok = OK_VALUES.get(answer)
        if ok is not None and row_key in NEGATIVE_ROWS and answer in ("OUI", "NON"):
            ok = not ok
        SafetyCheck.objects.create(
            site=submission.site, submission=submission, asset=asset, zone=zone, date=submission.date,
            item=f"{section_key}.{row_key}", ok=ok,
            location=str(values.get(location_col) or "") if location_col else "",
            observation=str(values.get("observations") or values.get("observation") or ""),
            source=submission.source,
        )


def _quality(submission, asset, section_key="quality"):
    data = submission.payload.get(section_key) or {}
    mapping = {
        "residual_chlorine": QualityParameter.RESIDUAL_CHLORINE,
        "turbidity": QualityParameter.TURBIDITY,
        "odour_colour": QualityParameter.ODOUR_COLOUR,
    }
    for row_key, parameter in mapping.items():
        values = data.get(row_key) or {}
        raw = values.get("value")
        if raw in (None, "") and values.get("conforme") in (None, ""):
            continue
        if parameter == QualityParameter.ODOUR_COLOUR:
            # The question is "abnormal odour/colour?": OUI means NOT compliant.
            value = None
            compliant = is_compliant(submission.site, parameter, raw) if raw not in (None, "") else None
        else:
            value = to_decimal(raw)
            compliant = is_compliant(submission.site, parameter, value, asset)
            if compliant is None and values.get("conforme") in ("OUI", "NON"):
                compliant = values.get("conforme") == "OUI"
        WaterQualityTest.objects.create(
            site=submission.site, submission=submission, asset=asset, date=submission.date,
            parameter=parameter, value=value, compliant=compliant,
            corrective_action=str(values.get("action") or ""), source=submission.source,
        )


def _clear_owned(submission):
    SafetyCheck.objects.filter(submission=submission).delete()
    WaterQualityTest.objects.filter(submission=submission).delete()
    Complaint.objects.filter(submission=submission).delete()


# ------------------------------------------------------------------ per form

def derive_pompage(sub):
    station = _asset(sub.site, get_path(sub.payload, "general.station"))
    _clear_owned(sub)
    _checks(sub, "technical", "state", asset=station)
    _quality(sub, station)


def derive_stockage(sub):
    reservoir = _asset(sub.site, get_path(sub.payload, "general.reservoir"))
    _clear_owned(sub)
    _checks(sub, "safety", "answer", asset=reservoir)
    _quality(sub, reservoir)


def derive_reseau(sub):
    site = sub.site
    zone = _zone(site, get_path(sub.payload, "general.zone"))
    _clear_owned(sub)
    for i, row in enumerate(sub.payload.get("network") or []):
        problems = [k for k in ("leak", "low_pressure", "illegal") if row.get(k) == "OUI"]
        SafetyCheck.objects.create(
            site=site, submission=sub, zone=zone, date=sub.date, item=f"network[{i}]",
            ok=not problems if any(row.get(k) for k in ("leak", "low_pressure", "illegal")) else None,
            location=f"{row.get('node') or ''} {row.get('reference') or ''}".strip(),
            observation="; ".join(filter(None, [
                ", ".join(problems), row.get("damaged"), row.get("cause"), row.get("intervention"), row.get("observation")])),
            source=sub.source,
        )
    for row in sub.payload.get("kiosks") or []:
        kiosk = _asset(site, row.get("kiosk"))
        if kiosk is None:
            continue
        SafetyCheck.objects.create(site=site, submission=sub, asset=kiosk, zone=zone, date=sub.date, item="kiosk.working",
                                   ok=OK_VALUES.get(row.get("working")), observation=str(row.get("damaged") or ""), source=sub.source)
        value = to_decimal(row.get("residual_chlorine"))
        if value is not None:
            compliant = is_compliant(site, QualityParameter.RESIDUAL_CHLORINE, value, kiosk)
            if compliant is None and row.get("conforme") in ("OUI", "NON"):
                compliant = row["conforme"] == "OUI"
            WaterQualityTest.objects.create(site=site, submission=sub, asset=kiosk, date=sub.date,
                                            parameter=QualityParameter.RESIDUAL_CHLORINE, value=value, compliant=compliant,
                                            corrective_action=str(row.get("action") or ""), source=sub.source)
    for row in sub.payload.get("complaints") or []:
        if row.get("nature"):
            Complaint.objects.create(site=site, submission=sub, zone=zone, date=sub.date, nature=row["nature"],
                                     location=str(row.get("location") or ""), action_taken=str(row.get("action") or ""),
                                     source=sub.source)


def next_incident_number(site, year):
    """Never reused, safe under concurrency (row lock on the counter)."""
    prefix = f"{site.code}-INC-{year}-"
    floor = 0
    for n in Incident.objects.filter(number__startswith=prefix).values_list("number", flat=True):
        m = re.search(r"(\d+)$", n)
        if m:
            floor = max(floor, int(m.group(1)))
    return f"{prefix}{Sequence.next(site, f'incident-{year}', floor):04d}"


def derive_panne(sub):
    site = sub.site
    p = sub.payload
    g = p.get("general") or {}
    d = p.get("description") or {}
    a = p.get("analysis") or {}
    iv = p.get("intervention") or {}
    ver = p.get("verification") or {}
    tz = timezone.get_current_timezone()
    detected = timezone.make_aware(dt.datetime.combine(to_date(g.get("date")), to_time(g.get("detected_time")) or dt.time(0, 0)), tz)
    start = to_datetime(iv.get("start"))
    end = to_datetime(iv.get("end"))
    if start and timezone.is_naive(start):
        start = timezone.make_aware(start, tz)
    if end and timezone.is_naive(end):
        end = timezone.make_aware(end, tz)
    interrupted = d.get("service_interrupted") == "OUI"
    downtime = to_decimal(d.get("downtime_hours"))
    if downtime is None:
        downtime = Decimal(0)
        if interrupted and end and end > detected:
            downtime = (Decimal((end - detected).total_seconds()) / Decimal(3600)).quantize(Decimal("0.01"))
    restored = (ver.get("restored") or {}).get("answer") == "OUI"
    status = Incident.Status.CLOSED if restored else (Incident.Status.IN_PROGRESS if start else Incident.Status.OPEN)
    gps = g.get("gps") or {}

    fields = dict(
        site=site, source=sub.source, source_ref=sub.source_ref, detected_at=detected,
        reported_by=str(g.get("reported_by") or ""),
        asset=_asset(site, d.get("asset")), node=_node(site, g.get("node")), zone=_zone(site, g.get("zone")),
        location_detail=str(g.get("location") or ""),
        latitude=to_decimal(gps.get("lat")) if gps else None, longitude=to_decimal(gps.get("lon")) if gps else None,
        description=str(a.get("damage") or ""), incident_type=str(d.get("incident_type") or ""),
        severity=d.get("severity") or Incident.Severity.MEDIUM, service_interrupted=interrupted,
        downtime_cause=(d.get("downtime_cause") or ("OTHER" if interrupted else "")),
        downtime_hours=downtime if interrupted else Decimal(0),
        affected_zone=str(d.get("affected_zone") or ""),
        affected_population=_to_int(d.get("affected_population")),
        probable_cause=a.get("probable_cause") or "", root_cause=str(a.get("root_cause") or ""),
        nrw_cause=a.get("nrw_cause") or "", estimated_loss_m3=to_decimal(a.get("estimated_loss_m3")),
        maintenance_type=iv.get("maintenance_type") or "CORRECTIVE",
        intervention_start=start, intervention_end=end, team=str(iv.get("team") or ""),
        materials_used=str(iv.get("materials") or ""), cost_usd=to_decimal(iv.get("cost_usd")),
        status=status, closed_at=(end or detected) if restored else None,
        verification=ver, lessons=p.get("lessons") or {},
    )
    incident = Incident.objects.filter(submission=sub).first()
    if incident is None:
        # A rejected-then-restored report keeps the number the server gave it (never one typed on the phone).
        number = sub.assigned_number
        if not number or Incident.objects.filter(number=number).exists():
            number = next_incident_number(site, detected.year)
        incident = Incident.objects.create(submission=sub, number=number, **fields)
        if sub.assigned_number != number:
            FormSubmission.objects.filter(pk=sub.pk).update(assigned_number=number)
            sub.assigned_number = number
    else:
        for k, v in fields.items():
            setattr(incident, k, v)
        incident.save()
    if (p.get("general") or {}).get("number") != incident.number:
        p.setdefault("general", {})["number"] = incident.number
        FormSubmission.objects.filter(pk=sub.pk).update(payload=p)
        sub.payload = p

    StockMovement.objects.filter(incident=incident).delete()
    for row in p.get("parts") or []:
        item = StockItem.objects.filter(site=site, code=row.get("item")).first()
        qty = to_decimal(row.get("quantity"))
        if item and qty:
            StockMovement.objects.create(site=site, item=item, date=sub.date, kind=StockMovement.Kind.OUT, quantity=qty,
                                         incident=incident, reference=incident.number, source=sub.source)
    Expense.objects.filter(incident=incident).delete()
    if incident.cost_usd:
        Expense.objects.create(site=site, date=sub.date, maintenance_type=incident.maintenance_type,
                               amount_usd=incident.cost_usd, description=f"Incident {incident.number}",
                               incident=incident, source=sub.source)


def _release_work_orders(sub, keep_categories=()):
    """Undo what this checklist did to work orders outside `keep_categories`."""
    for wo in WorkOrder.objects.filter(submission=sub).exclude(category__in=keep_categories):
        if wo.origin == WorkOrder.Origin.CHECKLIST:
            wo.delete()  # it only existed because of this checklist
        else:
            wo.status, wo.done_date, wo.submission, wo.findings = WorkOrder.Status.PLANNED, None, None, []
            wo.save()


def _derive_preventive(sub, categories, asset=None, zone=None):
    site = sub.site
    findings = [r for r in (sub.payload.get("maintenance") or []) if any((r or {}).values())]
    _release_work_orders(sub, keep_categories=categories)
    label = asset.code if asset else (zone.code if zone else "")
    for cat in categories:
        wo = WorkOrder.objects.filter(submission=sub, category=cat).first()
        if wo is not None and wo.origin != WorkOrder.Origin.CHECKLIST and (
                (asset and wo.asset_id not in (None, asset.id)) or (zone and wo.zone_id not in (None, zone.id))):
            # The checklist now concerns another pump/zone: give the planned order back to the plan.
            wo.status, wo.done_date, wo.submission, wo.findings = WorkOrder.Status.PLANNED, None, None, []
            wo.save()
            wo = None
        if wo is None:
            scope = {"asset": asset} if asset else ({"zone": zone} if zone else {})
            wo = WorkOrder.objects.filter(
                site=site, kind="PREVENTIVE", category=cat, status=WorkOrder.Status.PLANNED, submission__isnull=True,
                planned_date__year=sub.date.year, planned_date__month=sub.date.month, **scope,
            ).exclude(origin=WorkOrder.Origin.CHECKLIST).order_by("planned_date").first()
        if wo is None:
            wo = WorkOrder(site=site, kind="PREVENTIVE", category=cat, planned_date=sub.date, origin=WorkOrder.Origin.CHECKLIST,
                           title=f"Maintenance préventive {dict(WorkOrder.Category.choices)[cat]} {label}".strip())
        elif wo.origin == WorkOrder.Origin.CHECKLIST:
            wo.planned_date = sub.date
            wo.asset, wo.zone = asset, zone
        wo.asset = wo.asset or asset
        wo.zone = wo.zone or zone
        wo.done_date = sub.date
        wo.status = WorkOrder.Status.DONE
        wo.findings = findings
        wo.submission = sub
        wo.source = sub.source
        wo.save()


def derive_mp_pompe(sub):
    pump = _asset(sub.site, get_path(sub.payload, "general.pump"))
    _clear_owned(sub)
    for section in ("mechanical", "electrical", "performance"):
        _checks(sub, section, "state", asset=pump)
    _derive_preventive(sub, ("POMPAGE",), asset=pump)


def derive_mp_reservoir(sub):
    res = _asset(sub.site, get_path(sub.payload, "general.reservoir"))
    _clear_owned(sub)
    for section in ("structural", "sanitary"):
        _checks(sub, section, "answer", asset=res)
    _derive_preventive(sub, ("RESERVOIR",), asset=res)


def derive_mp_reseau(sub):
    zone = _zone(sub.site, get_path(sub.payload, "general.zone"))
    _clear_owned(sub)
    _checks(sub, "network", "answer", zone=zone, location_col="location")
    _checks(sub, "kiosks", "answer", zone=zone, location_col="location")
    has_bf = any(any((v or {}).values()) for v in (sub.payload.get("kiosks") or {}).values())
    _derive_preventive(sub, ("RESEAU", "BF") if has_bf else ("RESEAU",), zone=zone)


DERIVERS = {
    FormType.POMPAGE: derive_pompage,
    FormType.STOCKAGE: derive_stockage,
    FormType.RESEAU_BF: derive_reseau,
    FormType.PANNE: derive_panne,
    FormType.MP_POMPE: derive_mp_pompe,
    FormType.MP_RESERVOIR: derive_mp_reservoir,
    FormType.MP_RESEAU: derive_mp_reseau,
}
READING_FORMS = {FormType.POMPAGE, FormType.STOCKAGE, FormType.RESEAU_BF}


@transaction.atomic
def derive(submission):
    """(Re)build every record that depends on `submission` (or remove them if it is rejected)."""
    active = submission.status != FormSubmission.Status.REJECTED
    if submission.form_type in READING_FORMS:
        derive_readings(submission, active=active)
    if active:
        DERIVERS[submission.form_type](submission)
    else:
        undo(submission)


def undo(submission):
    _clear_owned(submission)
    Incident.objects.filter(submission=submission).delete()  # stock movements and expense cascade
    _release_work_orders(submission)


__all__ = ["derive", "undo", "hours_between", "next_incident_number", "contributions", "AssetType"]
