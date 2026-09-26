"""One test per Excel defect that distorted a KPI (codes from docs/data-quality-report.md).

Each test imports the real workbooks, then proves the platform does NOT
reproduce the defect. Expected values are recomputed by hand from the raw
inputs of the `O&M KPI` sheet (listed in each comment).
"""
import datetime as dt
from decimal import Decimal

import pytest
from django.conf import settings

from core.models import Asset, Node, PipeSegment
from importer.checks import run_all
from importer.loaders import import_all
from importer.xl import Workbooks
from kpi.models import MonthlyAggregate
from kpi.service import compute_year
from ops.models import DailyReading
from stock.models import StockMovement

from .conftest import TODAY, needs_workbooks, pompage_payload, push

pytestmark = [pytest.mark.django_db, needs_workbooks]


@pytest.fixture
def go(db):
    wb = Workbooks(settings.WORKBOOK_DIR)
    site, log = import_all(wb, 2026, TODAY)
    return site


def kpis(site):
    return compute_year(site, 2026, today=TODAY)


def v(result, month):
    return result["months"][month - 1]["values"]


def test_k01_k02_availability_uses_each_months_own_downtime(go):
    # Downtime Jan–Jun (rows 5-8): 24, 18, 14 (E5 blank), 31, 18, 19 = 124 h over 4344 h.
    # Excel shows 0.970534 because E10 subtracts February (18) instead of March (14).
    r = kpis(go)
    assert v(r, 3)["downtime_total"] == 14
    assert v(r, 3)["operating_hours"] == 730  # 744 − 14, Excel E10 shows 726
    months = [m for m in r["months"][:6]]
    operating = sum(m["values"]["operating_hours"] for m in months)
    period = sum(m["values"]["period_hours"] for m in months)
    assert operating == 4220 and period == 4344
    assert round(float(Decimal(operating) / Decimal(period)), 6) == 0.971455
    assert round(float(v(r, 3)["availability"]), 6) == round(730 / 744, 6)


def test_k03_repair_rate_is_not_hardcoded(go):
    # Excel: 50 / 139 = 0.3597 with 50 typed in. No repair log exists for Jan–Jun: no figure is invented.
    r = kpis(go)
    assert all(v(r, m)["repair_rate"] is None for m in range(1, 7))
    assert not MonthlyAggregate.objects.filter(metric="incidents_closed").exists()


def test_k04_done_is_not_planned_minus_five(go):
    r = kpis(go)
    assert v(r, 1)["pm_planned_total"] == 12  # 2 + 4 + 2 + 2 + 2
    assert v(r, 1)["pm_done_total"] is None and v(r, 1)["pm_rate"] is None  # Excel: 7 / 12 = 0.583


def test_k05_fuel_and_cost_per_m3_divide_by_volume(go):
    r = kpis(go)
    jan = v(r, 1)
    # Fuel intensity: 225 L / 600 m³ = 0.375 L/m³ (Excel C62: 225/175+30 = 31.29)
    assert jan["fuel_l_per_m3"] == Decimal(225) / Decimal(600)
    # Energy cost: (234.5833 × 0.25 + 225 × 1.7) / 600 = (58.6458 + 382.5) / 600 = 0.73524 USD/m³ (Excel C68: 0.548)
    assert round(float(jan["energy_cost_per_m3"]), 5) == 0.73524
    # Fuel cost per m³: 382.5 / 600 = 0.6375 (Excel C66: 32.19)
    assert jan["fuel_cost_per_m3"] == Decimal("382.5") / Decimal(600)


def test_k06_k07_july_totals_sum_every_day(go, client_for_go):
    # Imported: 9 July, CAPRARI 2 h × 180 m³/h = 360 m³ and SHIMGE 3 h × 90 = 270 m³.
    r = kpis(go)
    assert v(r, 7)["volume_introduced"] == 630
    assert r["months"][6]["sources"]["volume_introduced"] == "fiches"
    # A new day in July adds to the month (Excel kept reading only 9 July).
    c = client_for_go
    rows = [{"pump": "GO-PMP-001", "start": "06:00", "stop": "08:00", "flow_m3h": 180}]
    res = push(c, "POMPAGE", pompage_payload("2026-07-20", rows, station="GO-STP-001", kwh=100)).json()["results"][0]
    assert res["status"] == "created", res
    r = kpis(go)
    assert v(r, 7)["volume_introduced"] == 990  # 630 + 360
    assert v(r, 7)["kwh"] == 318  # 218 (9 July, both pumps) + 100


def test_k08_august_uses_august_records(go, client_for_go):
    rows = [{"pump": "GO-PMP-002", "start": "06:00", "stop": "10:00", "flow_m3h": 90}]
    push(client_for_go, "POMPAGE", pompage_payload("2026-08-03", rows, station="GO-STP-001"))
    r = kpis(go)
    assert v(r, 8)["volume_introduced"] == 360
    assert v(r, 7)["volume_introduced"] == 630  # July unchanged


def test_k09_nrw_not_100_percent_without_sales(go):
    r = kpis(go)
    assert v(r, 7)["volume_billed"] is None
    assert v(r, 7)["nrw_m3"] is None and v(r, 7)["efficiency"] is None  # Excel: NRW = 630 (100 %)


def test_k10_future_months_not_imported_and_provisional_ignored(go):
    assert not MonthlyAggregate.objects.filter(month__gte=dt.date(2026, 10, 1)).exists()
    assert set(MonthlyAggregate.objects.filter(month__gte=dt.date(2026, 7, 1)).values_list("status", flat=True)) == {"PROVISIONAL"}
    r = kpis(go)
    assert r["months"][8]["provisional"]["volume_introduced"] == 620  # shown for comparison…
    assert v(r, 9)["volume_introduced"] is None  # …never used
    assert all(v(r, m)["availability"] is None for m in (10, 11, 12))


def test_k11_nrw_every_month(go):
    r = kpis(go)
    # Feb: 700 − 595 = 105 ; Jun: 660 − 555 = 105 (Excel only computes January)
    assert v(r, 2)["nrw_m3"] == 105 and v(r, 6)["nrw_m3"] == 105
    assert round(float(r["annual"]["efficiency"]), 6) == round((495 + 595 + 645 + 640 + 595 + 555) / (600 + 700 + 750 + 745 + 700 + 660), 6)


def test_k13_total_spending_includes_support(go):
    r = kpis(go)
    jan = v(r, 1)
    assert jan["actual_total"] == 3189 + 2576 + 1557  # support not recorded for January
    assert jan["budget_variance"] == 3189 + 2576 + 1557 - 5580


def test_a02_node_110_distinct_from_11(go):
    assert Node.objects.filter(site=go, code="1.1").exists() and Node.objects.filter(site=go, code="1.10").exists()
    assert PipeSegment.objects.filter(site=go, code="1.8>1.10#DN160", length_m=Decimal("74")).exists()
    assert PipeSegment.objects.filter(site=go, code="SR>1.1#DN160").exists()


def test_a01_a13_stable_ids_and_one_asset_per_pump(go):
    pumps = Asset.objects.filter(site=go, type="PUMP").order_by("code")
    assert [p.code for p in pumps] == ["GO-PMP-001", "GO-PMP-002", "GO-PMP-003"]
    assert "CAPRARI" in pumps[0].name and all("SHIMGE" in p.name for p in pumps[1:])
    assert pumps[0].parent.code == "GO-STP-001"


def test_k18_row5_reading_goes_to_shimge(go):
    r = DailyReading.objects.get(asset__code="GO-PMP-002", date="2026-07-09")
    assert r.flow_m3h == 90 and "K18" in r.flags
    assert DailyReading.objects.get(asset__code="GO-PMP-001", date="2026-07-09").volume_m3 == 360


def test_k19_autofilled_reseau_not_imported(go):
    assert not DailyReading.objects.filter(site=go, asset__type="KIOSK").exists()


def test_s01_s03_no_placeholder_stock_quantities(go):
    assert not StockMovement.objects.exists()


def test_importer_is_idempotent(go):
    from core.models import Asset as A
    counts = (A.objects.count(), Node.objects.count(), PipeSegment.objects.count(), MonthlyAggregate.objects.count(),
              DailyReading.objects.count())
    import_all(Workbooks(settings.WORKBOOK_DIR), 2026, TODAY)
    assert counts == (A.objects.count(), Node.objects.count(), PipeSegment.objects.count(), MonthlyAggregate.objects.count(),
                      DailyReading.objects.count())


def test_every_kpi_check_fires_on_original_workbooks():
    findings, errors = run_all(Workbooks(settings.WORKBOOK_DIR))
    assert not errors
    codes = {f.code for f in findings}
    for code in ["A02", "K01", "K03", "K04", "K05", "K06", "K07", "K08", "K09", "K10", "K11", "K13", "K18", "K19", "S01", "S03"]:
        assert code in codes


# ------------------------------------------------------------------ fixtures

@pytest.fixture
def client_for_go(go):
    from rest_framework.test import APIClient

    from core.models import Role
    from .conftest import make_user

    user = make_user(go, "pompage_go", Role.PUMP_FOCAL)
    c = APIClient()
    c.force_authenticate(user)
    return c
