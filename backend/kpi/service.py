"""Monthly and annual KPIs computed from operational records.

Base quantities (downtime hours, volumes, counts, costs…) come from records.
For months before the app went live, an imported MonthlyAggregate with status
ACTUAL replaces the record-based base quantity. Ratios are ALWAYS recomputed
from base quantities, so no spreadsheet formula (or formula bug) is carried over.
"""
import calendar
import datetime as dt
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractMonth
from django.utils import timezone

from . import formulas as F
from .models import MonthlyAggregate
from core.models import AssetType
from ops.models import (
    DailyReading,
    DowntimeCause,
    Expense,
    FailureCause,
    Incident,
    MaintenanceType,
    NRWCause,
    WaterQualityTest,
    WorkOrder,
)
from plan.models import BudgetLine, MonthlyBudget, Tariff

MONTHS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

DOWNTIME_KEYS = {
    DowntimeCause.PUMP_FAILURE: "downtime_pump",
    DowntimeCause.PIPE_BURST: "downtime_pipe",
    DowntimeCause.POWER_CUT: "downtime_power",
    DowntimeCause.PLANNED_MAINTENANCE: "downtime_planned",
    DowntimeCause.OTHER: "downtime_other",
}
PM_CATEGORIES = [c for c, _ in WorkOrder.Category.choices]
COST_KEYS = {
    MaintenanceType.URGENT: "cost_urgent",
    MaintenanceType.CORRECTIVE: "cost_corrective",
    MaintenanceType.PREVENTIVE: "cost_preventive",
    MaintenanceType.SUPPORT: "cost_support",
    MaintenanceType.ROUTINE: "cost_routine",
}

# Base quantities that may be overridden by historical ACTUAL aggregates.
BASE_METRICS = (
    list(DOWNTIME_KEYS.values())
    + ["incidents_reported", "incidents_closed", "volume_introduced", "volume_billed", "kwh", "fuel_l", "budget"]
    + [f"rca_{c}" for c in FailureCause.values]
    + [f"nrw_{c}" for c in NRWCause.values]
    + [f"pm_planned_{c}" for c in PM_CATEGORIES]
    + [f"pm_done_{c}" for c in PM_CATEGORIES]
    + list(COST_KEYS.values())
    + ["quality_field_total", "quality_field_compliant", "quality_lab_total", "quality_lab_compliant"]
)


def month_status(year, month, today):
    first = dt.date(year, month, 1)
    if first > today:
        return "future"
    last = dt.date(year, month, calendar.monthrange(year, month)[1])
    return "current" if last >= today else "closed"


def tariff(site, kind, on_date):
    t = Tariff.objects.filter(site=site, kind=kind, valid_from__lte=on_date).order_by("-valid_from").first()
    if t is None:
        t = Tariff.objects.filter(site=site, kind=kind).order_by("valid_from").first()
    return t.price_usd if t else None


def _by_month(qs, date_field, value=None, extra=None):
    """{month: aggregated value} for one year, grouped in the database."""
    qs = qs.annotate(m=ExtractMonth(date_field)).values("m", *(extra or []))
    qs = qs.annotate(v=Sum(value) if value else Count("pk"))
    return qs


def record_bases(site, year):
    """{month: {metric: Decimal|int|None}} from operational records only."""
    out = defaultdict(dict)

    # Downtime (incidents with service interruption + planned maintenance stops).
    for r in _by_month(Incident.objects.filter(site=site, detected_at__year=year, service_interrupted=True),
                       "detected_at", "downtime_hours", ["downtime_cause"]):
        key = DOWNTIME_KEYS.get(r["downtime_cause"] or "OTHER", "downtime_other")
        out[r["m"]][key] = out[r["m"]].get(key, Decimal(0)) + (r["v"] or 0)
    for r in _by_month(WorkOrder.objects.filter(site=site, status=WorkOrder.Status.DONE, done_date__year=year,
                                                downtime_hours__gt=0), "done_date", "downtime_hours"):
        out[r["m"]]["downtime_planned"] = out[r["m"]].get("downtime_planned", Decimal(0)) + r["v"]

    # Incidents, repairs, root causes, NRW causes.
    inc = Incident.objects.filter(site=site, detected_at__year=year)
    for r in _by_month(inc, "detected_at"):
        out[r["m"]]["incidents_reported"] = r["v"]
    for r in _by_month(inc.filter(status=Incident.Status.CLOSED), "detected_at"):
        out[r["m"]]["incidents_closed"] = r["v"]
    for r in _by_month(inc.exclude(probable_cause=""), "detected_at", extra=["probable_cause"]):
        out[r["m"]][f"rca_{r['probable_cause']}"] = r["v"]
    for r in _by_month(inc.exclude(nrw_cause=""), "detected_at", extra=["nrw_cause"]):
        out[r["m"]][f"nrw_{r['nrw_cause']}"] = r["v"]

    # Volumes and energy.
    rd = DailyReading.objects.filter(site=site, date__year=year)
    for r in _by_month(rd.filter(asset__type=AssetType.PUMP, volume_m3__isnull=False), "date", "volume_m3"):
        out[r["m"]]["volume_introduced"] = r["v"]
    for r in _by_month(rd.filter(asset__type__in=[AssetType.KIOSK, AssetType.PRIVATE_CONNECTION], volume_m3__isnull=False),
                       "date", "volume_m3"):
        out[r["m"]]["volume_billed"] = r["v"]
    for r in _by_month(rd.filter(kwh__isnull=False), "date", "kwh"):
        out[r["m"]]["kwh"] = r["v"]
    for r in _by_month(rd.filter(fuel_l__isnull=False), "date", "fuel_l"):
        out[r["m"]]["fuel_l"] = r["v"]
    for r in rd.filter(asset__type=AssetType.PUMP).annotate(m=ExtractMonth("date")).values("m").annotate(
            n=Count("date", distinct=True)):
        out[r["m"]]["_pump_days"] = r["n"]

    # Preventive maintenance: planned vs done, by category.
    wo = WorkOrder.objects.filter(site=site, kind=MaintenanceType.PREVENTIVE, planned_date__year=year).exclude(
        status=WorkOrder.Status.CANCELLED)
    for r in _by_month(wo, "planned_date", extra=["category"]):
        out[r["m"]][f"pm_planned_{r['category']}"] = r["v"]
    for r in _by_month(wo.filter(status=WorkOrder.Status.DONE), "planned_date", extra=["category"]):
        out[r["m"]][f"pm_done_{r['category']}"] = r["v"]

    # Budget and actual spending.
    for b in MonthlyBudget.objects.filter(site=site, month__year=year):
        out[b.month.month]["budget"] = b.amount_usd
    for line in BudgetLine.objects.filter(site=site, month__year=year):
        m = line.month.month
        if line.total_usd is not None and not MonthlyBudget.objects.filter(site=site, month=line.month).exists():
            out[m]["budget"] = out[m].get("budget", Decimal(0)) + line.total_usd
    for r in _by_month(Expense.objects.filter(site=site, date__year=year), "date", "amount_usd", ["maintenance_type"]):
        out[r["m"]][COST_KEYS[r["maintenance_type"]]] = r["v"]

    # Water quality.
    q = WaterQualityTest.objects.filter(site=site, date__year=year, compliant__isnull=False)
    for lab, prefix in ((False, "quality_field"), (True, "quality_lab")):
        for r in q.filter(is_lab=lab).annotate(m=ExtractMonth("date")).values("m").annotate(
                t=Count("pk"), c=Count("pk", filter=Q(compliant=True))):
            out[r["m"]][f"{prefix}_total"] = r["t"]
            out[r["m"]][f"{prefix}_compliant"] = r["c"]
    return out


def compute_year(site, year, today=None):
    today = today or timezone.localdate()
    records = record_bases(site, year)
    aggregates = defaultdict(dict)
    provisional = defaultdict(dict)
    for a in MonthlyAggregate.objects.filter(site=site, month__year=year):
        target = aggregates if a.status == MonthlyAggregate.Status.ACTUAL else provisional
        target[a.month.month][a.metric] = a.value
    price_kwh_cache = {}

    months = []
    for m in range(1, 13):
        status = month_status(year, m, today)
        base, source = {}, {}
        rec, agg = records.get(m, {}), aggregates.get(m, {})
        for key in BASE_METRICS:
            if key in agg:
                base[key], source[key] = agg[key], "historique"
            elif key in rec:
                base[key], source[key] = rec[key], "fiches"
            else:
                base[key], source[key] = None, None
        # "budget" is a plan: known even for future months.
        # Budget and spending alone do not make an operational month: availability etc. need field records.
        non_operational = {"budget", *COST_KEYS.values()}
        has_data = any(k not in non_operational for k in agg) or any(
            k not in non_operational and not k.startswith("_") for k in rec) or bool(rec.get("_pump_days"))
        if status == "future":
            base = {k: (v if k == "budget" else None) for k, v in base.items()}
            has_data = False

        k = dict(base)
        period = F.hours_in_month(year, m)
        downtime_values = [base[v] for v in DOWNTIME_KEYS.values()]
        downtime_total = sum((F.dec(v) for v in downtime_values if v is not None), Decimal(0)) if has_data else None
        k["period_hours"] = period
        k["downtime_total"] = downtime_total
        k["operating_hours"] = period - downtime_total if downtime_total is not None else None
        k["availability"] = F.availability(period, downtime_total) if has_data else None

        # Closure is only known for incidents logged in the app (the Excel history has no monthly repair count).
        k["repair_rate"] = (F.repair_rate(base["incidents_closed"] or 0, base["incidents_reported"])
                            if source["incidents_reported"] == "fiches" else None)
        k["efficiency"] = F.network_efficiency(base["volume_billed"], base["volume_introduced"])
        k["nrw_m3"] = F.nrw_m3(base["volume_introduced"], base["volume_billed"])
        k["nrw_rate"] = F.ratio(k["nrw_m3"], base["volume_introduced"])
        nrw_counts = [base[f"nrw_{c}"] for c in NRWCause.values if base[f"nrw_{c}"] is not None]
        k["nrw_events"] = sum(nrw_counts) if nrw_counts else None
        rca_counts = [base[f"rca_{c}"] for c in FailureCause.values if base[f"rca_{c}"] is not None]
        k["rca_total"] = sum(rca_counts) if rca_counts else None

        planned = [base[f"pm_planned_{c}"] for c in PM_CATEGORIES if base[f"pm_planned_{c}"] is not None]
        done = [base[f"pm_done_{c}"] for c in PM_CATEGORIES if base[f"pm_done_{c}"] is not None]
        k["pm_planned_total"] = sum(planned) if planned else None
        planned_from_records = any(source[f"pm_planned_{c}"] == "fiches" for c in PM_CATEGORIES)
        k["pm_done_total"] = sum(done) if done else (0 if planned_from_records else None)
        k["pm_rate"] = F.completion_rate(k["pm_done_total"], k["pm_planned_total"]) if k["pm_done_total"] is not None else None

        first = dt.date(year, m, 1)
        if m not in price_kwh_cache:
            price_kwh_cache[m] = (tariff(site, Tariff.Kind.ELECTRICITY, first), tariff(site, Tariff.Kind.FUEL, first))
        p_kwh, p_fuel = price_kwh_cache[m]
        k["price_kwh"], k["price_fuel"] = p_kwh, p_fuel
        k["cost_electricity"] = F.dec(base["kwh"]) * p_kwh if base["kwh"] is not None and p_kwh is not None else None
        k["cost_fuel"] = F.dec(base["fuel_l"]) * p_fuel if base["fuel_l"] is not None and p_fuel is not None else None
        k["energy_cost"] = F.energy_cost(base["kwh"], p_kwh, base["fuel_l"], p_fuel)
        k["kwh_per_m3"] = F.intensity(base["kwh"], base["volume_introduced"])
        k["fuel_l_per_m3"] = F.intensity(base["fuel_l"], base["volume_introduced"])
        k["electricity_cost_per_m3"] = F.intensity(k["cost_electricity"], base["volume_introduced"])
        k["fuel_cost_per_m3"] = F.intensity(k["cost_fuel"], base["volume_introduced"])
        k["energy_cost_per_m3"] = F.intensity(k["energy_cost"], base["volume_introduced"])

        costs = [base[c] for c in ("cost_urgent", "cost_corrective", "cost_preventive", "cost_support") if base[c] is not None]
        k["actual_total"] = sum(costs) if costs else None
        k["budget_variance"] = F.variance(k["actual_total"], base["budget"])
        for key in ("urgent", "corrective", "preventive", "support"):
            k[f"share_{key}"] = F.share(base[f"cost_{key}"], k["actual_total"]) if base[f"cost_{key}"] is not None else None

        qt = (base["quality_field_total"] or 0) + (base["quality_lab_total"] or 0)
        qc = (base["quality_field_compliant"] or 0) + (base["quality_lab_compliant"] or 0)
        k["quality_rate"] = F.compliance_rate(qc, qt) if qt else None

        if status == "future":
            k = {key: (val if key in ("budget", "period_hours", "price_kwh", "price_fuel") else None) for key, val in k.items()}
        months.append({
            "month": m,
            "label": MONTHS_FR[m - 1],
            "status": status,
            "has_data": has_data,
            "coverage": {"pump_reading_days": rec.get("_pump_days", 0), "days": calendar.monthrange(year, m)[1]},
            "sources": {key: s for key, s in source.items() if s},
            "provisional": {key: float(v) for key, v in provisional.get(m, {}).items()},
            "values": k,
        })

    return {"year": year, "site": site.code, "today": today.isoformat(), "months": months, "annual": annual(months)}


def _sum(months, key):
    vals = [F.dec(mm["values"][key]) for mm in months if mm["values"].get(key) is not None]
    return sum(vals, Decimal(0)) if vals else None


def annual(months):
    """Annual figures: sums of base quantities, ratios of sums (never averages of ratios)."""
    with_data = [m for m in months if m["has_data"]]
    a = {}
    for key in BASE_METRICS + ["downtime_total", "nrw_events", "rca_total", "pm_planned_total", "pm_done_total",
                               "cost_electricity", "cost_fuel", "energy_cost", "actual_total"]:
        if key == "budget":
            a[key] = _sum(months, key)
        else:
            a[key] = _sum(with_data, key)
    a["period_hours"] = sum((F.dec(m["values"]["period_hours"]) for m in with_data), Decimal(0)) if with_data else None
    a["availability"] = F.availability(a["period_hours"], a["downtime_total"]) if with_data else None
    a["operating_hours"] = a["period_hours"] - a["downtime_total"] if a["period_hours"] is not None and a["downtime_total"] is not None else None
    # Repair rate only over months whose incidents come from the incident log.
    log_months = [m for m in with_data if m["values"].get("repair_rate") is not None]
    a["repair_rate"] = F.repair_rate(_sum(log_months, "incidents_closed") or 0, _sum(log_months, "incidents_reported")) if log_months else None
    both = [m for m in with_data if m["values"]["volume_introduced"] is not None and m["values"]["volume_billed"] is not None]
    a["efficiency"] = F.network_efficiency(_sum(both, "volume_billed"), _sum(both, "volume_introduced")) if both else None
    a["nrw_m3"] = F.nrw_m3(_sum(both, "volume_introduced"), _sum(both, "volume_billed")) if both else None
    a["nrw_rate"] = F.ratio(a["nrw_m3"], _sum(both, "volume_introduced")) if both else None
    pm = [m for m in with_data if m["values"]["pm_rate"] is not None]
    a["pm_rate"] = F.completion_rate(_sum(pm, "pm_done_total"), _sum(pm, "pm_planned_total")) if pm else None
    en = [m for m in with_data if m["values"]["volume_introduced"] is not None]
    a["kwh_per_m3"] = F.intensity(_sum([m for m in en if m["values"]["kwh"] is not None], "kwh"),
                                  _sum([m for m in en if m["values"]["kwh"] is not None], "volume_introduced"))
    a["fuel_l_per_m3"] = F.intensity(_sum([m for m in en if m["values"]["fuel_l"] is not None], "fuel_l"),
                                     _sum([m for m in en if m["values"]["fuel_l"] is not None], "volume_introduced"))
    ec = [m for m in en if m["values"]["energy_cost"] is not None]
    a["energy_cost_per_m3"] = F.intensity(_sum(ec, "energy_cost"), _sum(ec, "volume_introduced")) if ec else None
    spent = [m for m in with_data if m["values"]["actual_total"] is not None]
    a["budget_variance"] = F.variance(_sum(spent, "actual_total"), _sum(spent, "budget")) if spent else None
    for key in ("urgent", "corrective", "preventive", "support"):
        a[f"share_{key}"] = F.share(_sum(spent, f"cost_{key}"), _sum(spent, "actual_total")) if spent else None
    qt = (a["quality_field_total"] or 0) + (a["quality_lab_total"] or 0)
    qc = (a["quality_field_compliant"] or 0) + (a["quality_lab_compliant"] or 0)
    a["quality_rate"] = F.compliance_rate(qc, qt) if qt else None
    # Root-cause shares over the year.
    if a["rca_total"]:
        for c in FailureCause.values:
            a[f"rca_share_{c}"] = F.share(a[f"rca_{c}"], a["rca_total"]) if a[f"rca_{c}"] is not None else None
    if a["nrw_events"]:
        for c in NRWCause.values:
            a[f"nrw_share_{c}"] = F.share(a[f"nrw_{c}"], a["nrw_events"]) if a[f"nrw_{c}"] is not None else None
    return a


def to_json(result):
    """Decimals -> floats for the API."""
    def conv(d):
        return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in d.items()}
    out = dict(result)
    out["months"] = [dict(m, values=conv(m["values"])) for m in result["months"]]
    out["annual"] = conv(result["annual"])
    return out
