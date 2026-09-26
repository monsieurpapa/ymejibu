"""KPI engine on a small known dataset. Expected values computed by hand in comments."""
import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from core.models import Asset
from kpi.models import MonthlyAggregate
from kpi.service import compute_year
from ops.models import DailyReading, Expense, Incident, WaterQualityTest, WorkOrder
from plan.models import MonthlyBudget

from .conftest import TODAY

pytestmark = pytest.mark.django_db


def at(day, hour=8):
    return timezone.make_aware(dt.datetime.combine(day, dt.time(hour, 0)))


@pytest.fixture
def march(site):
    A = {a.code: a for a in Asset.objects.filter(site=site)}
    d = dt.date(2026, 3, 10)
    for n, (cause, hours, status) in enumerate([("PUMP_FAILURE", 10, "CLOSED"), ("PIPE_BURST", 4, "OPEN"), ("POWER_CUT", 6, "CLOSED")]):
        Incident.objects.create(site=site, number=f"T-{n}", detected_at=at(d), service_interrupted=True, downtime_cause=cause,
                                downtime_hours=hours, status=status, probable_cause="VANDALISM" if n == 0 else "OVERPRESSURE",
                                nrw_cause="PIPE_LEAK" if n == 1 else "")
    WorkOrder.objects.create(site=site, title="MP pompe", kind="PREVENTIVE", category="POMPAGE", planned_date=d, done_date=d,
                             status="DONE", downtime_hours=2)
    WorkOrder.objects.create(site=site, title="MP pompe 2", kind="PREVENTIVE", category="POMPAGE", planned_date=d, done_date=d, status="DONE")
    WorkOrder.objects.create(site=site, title="MP réservoir", kind="PREVENTIVE", category="RESERVOIR", planned_date=d, done_date=d, status="DONE")
    WorkOrder.objects.create(site=site, title="MP réseau", kind="PREVENTIVE", category="RESEAU", planned_date=d, status="PLANNED")
    for k, (vol, sold) in enumerate([(100, 90), (120, 60), (80, 90)]):
        day = dt.date(2026, 3, 1 + k)
        DailyReading.objects.create(site=site, asset=A["TS-PMP-001"], date=day, volume_m3=vol)
        DailyReading.objects.create(site=site, asset=A["TS-STP-001"], date=day, kwh=50, fuel_l=10)
        DailyReading.objects.create(site=site, asset=A["TS-BF-01"], date=day, volume_m3=sold)
    for mt, amount in [("URGENT", 100), ("CORRECTIVE", 200), ("PREVENTIVE", 300), ("SUPPORT", 400)]:
        Expense.objects.create(site=site, date=d, maintenance_type=mt, amount_usd=amount)
    MonthlyBudget.objects.create(site=site, month=dt.date(2026, 3, 1), amount_usd=1200)
    for compliant in (True, True, True, False):
        WaterQualityTest.objects.create(site=site, date=d, parameter="RESIDUAL_CHLORINE", value=Decimal("0.3"), compliant=compliant)
    WaterQualityTest.objects.create(site=site, date=d, parameter="LAB", compliant=True, is_lab=True)
    return site


def month(result, m):
    return result["months"][m - 1]["values"]


def test_march_hand_checked(march):
    r = compute_year(march, 2026, today=TODAY)
    v = month(r, 3)
    # Downtime: 10 (pump) + 4 (pipe) + 6 (power) + 2 (planned WO) = 22 h ; 744 h in March
    assert v["downtime_pump"] == 10 and v["downtime_pipe"] == 4 and v["downtime_power"] == 6 and v["downtime_planned"] == 2
    assert v["downtime_total"] == 22
    assert v["operating_hours"] == 722
    assert round(float(v["availability"]), 6) == 0.970430  # 722 / 744
    # 3 incidents, 2 closed
    assert v["incidents_reported"] == 3 and v["incidents_closed"] == 2
    assert round(float(v["repair_rate"]), 4) == 0.6667
    assert v["rca_VANDALISM"] == 1 and v["rca_OVERPRESSURE"] == 2 and v["rca_total"] == 3
    # Volumes: pumped 300, sold 240 -> 80 %, NRW 60 m³ (20 %)
    assert v["volume_introduced"] == 300 and v["volume_billed"] == 240
    assert v["efficiency"] == Decimal("0.8") and v["nrw_m3"] == 60 and v["nrw_rate"] == Decimal("0.2")
    assert v["nrw_events"] == 1
    # Energy: 150 kWh, 30 L -> 37.5 + 51 = 88.5 USD -> 0.295 USD/m³ ; 0.5 kWh/m³ ; 0.1 L/m³
    assert v["kwh"] == 150 and v["fuel_l"] == 30
    assert v["cost_electricity"] == Decimal("37.5") and v["cost_fuel"] == Decimal("51")
    assert v["energy_cost"] == Decimal("88.5") and v["energy_cost_per_m3"] == Decimal("0.295")
    assert v["kwh_per_m3"] == Decimal("0.5") and v["fuel_l_per_m3"] == Decimal("0.1")
    # Preventive maintenance: 4 planned, 3 done
    assert v["pm_planned_total"] == 4 and v["pm_done_total"] == 3 and v["pm_rate"] == Decimal("0.75")
    # Costs: 1000 spent vs 1200 budget
    assert v["actual_total"] == 1000 and v["budget_variance"] == -200
    assert v["share_urgent"] == Decimal("0.1") and v["share_support"] == Decimal("0.4")
    # Quality: 3/4 field + 1/1 lab = 4/5
    assert v["quality_rate"] == Decimal("0.8")


def test_annual_is_ratio_of_sums(march):
    r = compute_year(march, 2026, today=TODAY)
    a = r["annual"]
    # Only March has data: annual availability = March availability (not diluted by empty months)
    assert round(float(a["availability"]), 6) == 0.970430
    assert a["efficiency"] == Decimal("0.8")
    assert a["rca_share_OVERPRESSURE"] == Decimal(2) / Decimal(3)


def test_empty_and_future_months_have_no_values(march):
    r = compute_year(march, 2026, today=TODAY)
    feb = month(r, 2)
    assert feb["availability"] is None and feb["efficiency"] is None and feb["nrw_m3"] is None
    assert r["months"][9]["status"] == "future"
    assert month(r, 10)["availability"] is None


def test_history_actual_overrides_provisional_ignored(site):
    MonthlyAggregate.objects.create(site=site, month=dt.date(2026, 1, 1), metric="downtime_pump", value=8, status="ACTUAL")
    MonthlyAggregate.objects.create(site=site, month=dt.date(2026, 1, 1), metric="volume_introduced", value=600, status="ACTUAL")
    MonthlyAggregate.objects.create(site=site, month=dt.date(2026, 1, 1), metric="volume_billed", value=495, status="ACTUAL")
    MonthlyAggregate.objects.create(site=site, month=dt.date(2026, 7, 1), metric="volume_introduced", value=999, status="PROVISIONAL")
    r = compute_year(site, 2026, today=TODAY)
    jan = r["months"][0]
    assert jan["sources"]["volume_introduced"] == "historique"
    assert month(r, 1)["availability"] == Decimal(736) / Decimal(744)
    assert month(r, 1)["nrw_m3"] == 105
    assert month(r, 1)["repair_rate"] is None  # no incident log for January
    jul = r["months"][6]
    assert jul["values"]["volume_introduced"] is None  # provisional value not used
    assert jul["provisional"]["volume_introduced"] == 999
