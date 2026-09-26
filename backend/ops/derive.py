"""Turn a FormSubmission into normalised records. Idempotent.

Daily readings are recomputed from *all* non-rejected submissions of the same
asset and day (two operator shifts = two sheets, one reading). Everything
else (checks, quality tests, incident, work order, stock movements, expense)
is owned by one submission and replaced when it is re-derived.
"""
import datetime as dt
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.models import Asset, AssetType, Node, Zone
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


def _siblings(submission, asset_field):
    """Non-rejected submissions of the same form, same day, same asset."""
    qs = FormSubmission.objects.filter(
        site=submission.site, form_type=submission.form_type, date=submission.date
    ).exclude(status=FormSubmission.Status.REJECTED)
    code = get_path(submission.payload, asset_field)
    return [s for s in qs if get_path(s.payload, asset_field) == code]


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
            site=submission.site,
            submission=submission,
            asset=asset,
            zone=zone,
            date=submission.date,
            item=f"{section_key}.{row_key}",
            ok=ok,
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


# ---------------------------------------------------------------- per form

def derive_pompage(sub):
    site = sub.site
    station = _asset(site, get_path(sub.payload, "general.station"))
    _clear_owned(sub)
    _checks(sub, "technical", "state", asset=station)
    _quality(sub, station)

    siblings = _siblings(sub, "general.station")
    per_pump = {}
    station_vals = {"kwh": [], "fuel": [], "chlorine": [], "obs": [], "operators": []}
    for s in siblings:
        for row in s.payload.get("pumps") or []:
            code = row.get("pump")
            if not code:
                continue
            hours = hours_between(to_time(row.get("start")), to_time(row.get("stop")))
            flow = to_decimal(row.get("flow_m3h"))
            volume = to_decimal(row.get("volume_m3"))
            if volume is None and flow is not None and hours is not None:
                volume = (flow * hours).quantize(Decimal("0.01"))
            p = per_pump.setdefault(code, {"hours": [], "volume": [], "flow": [], "pressure": [], "current": [], "obs": []})
            p["hours"].append(hours)
            p["volume"].append(volume)
            p["flow"].append(flow)
            p["pressure"].append(to_decimal(row.get("pressure_bar")))
            p["current"].append(to_decimal(row.get("current_a")))
            if row.get("observations"):
                p["obs"].append(str(row["observations"]))
        energy = s.payload.get("energy") or {}
        station_vals["kwh"].append(to_decimal((energy.get("snel") or {}).get("quantity")))
        station_vals["fuel"].append(to_decimal((energy.get("genset") or {}).get("quantity")))
        station_vals["chlorine"].append(to_decimal(((s.payload.get("quality") or {}).get("chlorine_g") or {}).get("value")))
        station_vals["operators"].append(get_path(s.payload, "general.operator") or "")

    operator = ", ".join(sorted({o for o in station_vals["operators"] if o}))
    for code, p in per_pump.items():
        pump = _asset(site, code)
        if pump is None:
            continue
        DailyReading.objects.update_or_create(
            asset=pump, date=sub.date,
            defaults=dict(
                site=site, submission=sub, source=sub.source, operator=operator,
                hours_run=_sum(p["hours"]), volume_m3=_sum(p["volume"]), flow_m3h=_mean(p["flow"]),
                pressure_bar=_mean(p["pressure"]), current_a=_mean(p["current"]),
                observations=" | ".join(p["obs"]),
            ),
        )
    if station is not None:
        DailyReading.objects.update_or_create(
            asset=station, date=sub.date,
            defaults=dict(
                site=site, submission=sub, source=sub.source, operator=operator,
                kwh=_sum(station_vals["kwh"]), fuel_l=_sum(station_vals["fuel"]),
                chlorine_g=_sum(station_vals["chlorine"]),
                observations=str(get_path(sub.payload, "maintenance.maintenance_done") or ""),
            ),
        )


def derive_stockage(sub):
    site = sub.site
    reservoir = _asset(site, get_path(sub.payload, "general.reservoir"))
    _clear_owned(sub)
    _checks(sub, "safety", "answer", asset=reservoir)
    _quality(sub, reservoir)
    if reservoir is None:
        return
    siblings = _siblings(sub, "general.reservoir")
    vin, vout, pin, pout, chl, levels, pressures = [], [], [], [], [], [], []
    for s in siblings:
        d = s.payload.get("daily") or {}
        vin.append(to_decimal(d.get("volume_in_m3")))
        vout.append(to_decimal(d.get("volume_out_m3")))
        pin.append(to_decimal(d.get("pressure_in_bar")))
        pout.append(to_decimal(d.get("pressure_out_bar")))
        chl.append(to_decimal(((s.payload.get("quality") or {}).get("chlorine_g") or {}).get("value")))
        for row in s.payload.get("operations") or []:
            levels.append(to_decimal(row.get("level_pct")))
            pressures.append(to_decimal(row.get("pressure_bar")))
    DailyReading.objects.update_or_create(
        asset=reservoir, date=sub.date,
        defaults=dict(
            site=site, submission=sub, source=sub.source,
            operator=str(get_path(sub.payload, "general.operator") or ""),
            volume_in_m3=_sum(vin), volume_out_m3=_sum(vout),
            pressure_in_bar=_mean(pin), pressure_out_bar=_mean(pout),
            pressure_bar=_mean(pressures), level_pct=_mean(levels), chlorine_g=_sum(chl),
            observations=str(get_path(sub.payload, "incidents.incidents") or ""),
        ),
    )


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
        SafetyCheck.objects.create(
            site=site, submission=sub, asset=kiosk, zone=zone, date=sub.date, item="kiosk.working",
            ok=OK_VALUES.get(row.get("working")), observation=str(row.get("damaged") or ""), source=sub.source,
        )
        value = to_decimal(row.get("residual_chlorine"))
        if value is not None:
            compliant = is_compliant(site, QualityParameter.RESIDUAL_CHLORINE, value, kiosk)
            if compliant is None and row.get("conforme") in ("OUI", "NON"):
                compliant = row["conforme"] == "OUI"
            WaterQualityTest.objects.create(
                site=site, submission=sub, asset=kiosk, date=sub.date, parameter=QualityParameter.RESIDUAL_CHLORINE,
                value=value, compliant=compliant, corrective_action=str(row.get("action") or ""), source=sub.source,
            )
    for row in sub.payload.get("complaints") or []:
        if row.get("nature"):
            Complaint.objects.create(site=site, submission=sub, zone=zone, date=sub.date, nature=row["nature"],
                                     location=str(row.get("location") or ""), action_taken=str(row.get("action") or ""),
                                     source=sub.source)
    # Volume sold per kiosk = sum over every network sheet of the day.
    sold = {}
    same_day = FormSubmission.objects.filter(site=site, form_type=FormType.RESEAU_BF, date=sub.date).exclude(
        status=FormSubmission.Status.REJECTED)
    for s in same_day:
        for row in s.payload.get("kiosks") or []:
            v = to_decimal(row.get("volume_sold_m3"))
            if row.get("kiosk") and v is not None:
                sold[row["kiosk"]] = sold.get(row["kiosk"], Decimal(0)) + v
    for code, volume in sold.items():
        kiosk = _asset(site, code)
        if kiosk:
            DailyReading.objects.update_or_create(
                asset=kiosk, date=sub.date,
                defaults=dict(site=site, submission=sub, source=sub.source, volume_m3=volume),
            )


def next_incident_number(site, year):
    prefix = f"{site.code}-INC-{year}-"
    last = Incident.objects.filter(number__startswith=prefix).aggregate(m=Max("number"))["m"]
    seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"


def derive_panne(sub):
    site = sub.site
    p = sub.payload
    g = p.get("general") or {}
    d = p.get("description") or {}
    a = p.get("analysis") or {}
    iv = p.get("intervention") or {}
    ver = p.get("verification") or {}
    tz = timezone.get_current_timezone()
    detected = dt.datetime.combine(to_date(g.get("date")), to_time(g.get("detected_time")) or dt.time(0, 0))
    detected = timezone.make_aware(detected, tz)
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

    incident = Incident.objects.filter(submission=sub).first()
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
        affected_population=int(d["affected_population"]) if d.get("affected_population") not in (None, "") else None,
        probable_cause=a.get("probable_cause") or "", root_cause=str(a.get("root_cause") or ""),
        nrw_cause=a.get("nrw_cause") or "", estimated_loss_m3=to_decimal(a.get("estimated_loss_m3")),
        maintenance_type=iv.get("maintenance_type") or "CORRECTIVE",
        intervention_start=start, intervention_end=end, team=str(iv.get("team") or ""),
        materials_used=str(iv.get("materials") or ""), cost_usd=to_decimal(iv.get("cost_usd")),
        status=status, closed_at=(end or detected) if restored else None,
        verification=ver, lessons=p.get("lessons") or {},
    )
    if incident is None:
        incident = Incident.objects.create(submission=sub, number=next_incident_number(site, detected.year), **fields)
    else:
        for k, v in fields.items():
            setattr(incident, k, v)
        incident.save()
    # Write the server-assigned number back into the form.
    if (p.get("general") or {}).get("number") != incident.number:
        p.setdefault("general", {})["number"] = incident.number
        FormSubmission.objects.filter(pk=sub.pk).update(payload=p)
        sub.payload = p

    # Parts used -> stock ledger (OUT), replaced on re-derivation.
    StockMovement.objects.filter(incident=incident).delete()
    for row in p.get("parts") or []:
        item = StockItem.objects.filter(site=site, code=row.get("item")).first()
        qty = to_decimal(row.get("quantity"))
        if item and qty:
            StockMovement.objects.create(site=site, item=item, date=sub.date, kind=StockMovement.Kind.OUT, quantity=qty,
                                         incident=incident, reference=incident.number, source=sub.source)
    # Actual spending -> expense ledger.
    Expense.objects.filter(incident=incident).delete()
    if incident.cost_usd:
        Expense.objects.create(site=site, date=sub.date, maintenance_type=incident.maintenance_type,
                               amount_usd=incident.cost_usd, description=f"Incident {incident.number}",
                               incident=incident, source=sub.source)


def _derive_preventive(sub, category, asset=None, zone=None, extra_categories=()):
    site = sub.site
    findings = [r for r in (sub.payload.get("maintenance") or []) if any((r or {}).values())]
    for cat in (category,) + tuple(extra_categories):
        wo = WorkOrder.objects.filter(submission=sub, category=cat).first() if cat == category else None
        if wo is None and cat == category:
            # Close the matching planned work order of the month, if any.
            wo = WorkOrder.objects.filter(
                site=site, kind="PREVENTIVE", category=cat, status=WorkOrder.Status.PLANNED, submission__isnull=True,
                planned_date__year=sub.date.year, planned_date__month=sub.date.month,
                **({"asset": asset} if asset else {}), **({"zone": zone} if zone and not asset else {}),
            ).order_by("planned_date").first()
        if cat != category:
            wo = WorkOrder.objects.filter(site=site, category=cat, title__endswith=f"[{sub.pk}]").first()
        title_asset = asset.code if asset else (zone.code if zone else "")
        defaults = dict(site=site, kind="PREVENTIVE", category=cat, asset=asset, zone=zone,
                        done_date=sub.date, status=WorkOrder.Status.DONE, findings=findings, source=sub.source)
        if wo is None:
            wo = WorkOrder(planned_date=sub.date, **defaults)
        else:
            for k, v in defaults.items():
                setattr(wo, k, v)
        if cat == category:
            wo.submission = sub
            wo.title = wo.title or f"Maintenance préventive {dict(WorkOrder.Category.choices)[cat]} {title_asset}".strip()
        else:
            wo.title = f"Maintenance préventive {dict(WorkOrder.Category.choices)[cat]} {title_asset} [{sub.pk}]"
        wo.save()


def derive_mp_pompe(sub):
    pump = _asset(sub.site, get_path(sub.payload, "general.pump"))
    _clear_owned(sub)
    for section in ("mechanical", "electrical", "performance"):
        _checks(sub, section, "state", asset=pump)
    _derive_preventive(sub, "POMPAGE", asset=pump)


def derive_mp_reservoir(sub):
    res = _asset(sub.site, get_path(sub.payload, "general.reservoir"))
    _clear_owned(sub)
    for section in ("structural", "sanitary"):
        _checks(sub, section, "answer", asset=res)
    _derive_preventive(sub, "RESERVOIR", asset=res)


def derive_mp_reseau(sub):
    zone = _zone(sub.site, get_path(sub.payload, "general.zone"))
    _clear_owned(sub)
    _checks(sub, "network", "answer", zone=zone, location_col="location")
    _checks(sub, "kiosks", "answer", zone=zone, location_col="location")
    has_bf = any(any((v or {}).values()) for v in (sub.payload.get("kiosks") or {}).values())
    _derive_preventive(sub, "RESEAU", zone=zone, extra_categories=("BF",) if has_bf else ())


DERIVERS = {
    FormType.POMPAGE: derive_pompage,
    FormType.STOCKAGE: derive_stockage,
    FormType.RESEAU_BF: derive_reseau,
    FormType.PANNE: derive_panne,
    FormType.MP_POMPE: derive_mp_pompe,
    FormType.MP_RESERVOIR: derive_mp_reservoir,
    FormType.MP_RESEAU: derive_mp_reseau,
}


@transaction.atomic
def derive(submission):
    """(Re)build every record that depends on `submission`."""
    if submission.status == FormSubmission.Status.REJECTED:
        undo(submission)
        return
    DERIVERS[submission.form_type](submission)


def undo(submission):
    _clear_owned(submission)
    Incident.objects.filter(submission=submission).delete()
    WorkOrder.objects.filter(submission=submission).update(status=WorkOrder.Status.PLANNED, done_date=None, submission=None)
    WorkOrder.objects.filter(title__endswith=f"[{submission.pk}]").delete()
    DailyReading.objects.filter(submission=submission).delete()
    # Other sheets of the same day still count: rebuild from the latest one.
    other = FormSubmission.objects.filter(site=submission.site, form_type=submission.form_type, date=submission.date).exclude(
        pk=submission.pk).exclude(status=FormSubmission.Status.REJECTED).order_by("-updated_at").first()
    if other is not None and submission.form_type in (FormType.POMPAGE, FormType.STOCKAGE, FormType.RESEAU_BF):
        DERIVERS[other.form_type](other)


__all__ = ["derive", "undo", "hours_between", "next_incident_number", "RecordSource", "AssetType"]
