"""Offline sync protocol and derivation of submissions into records."""
import base64
import uuid
from decimal import Decimal

import pytest

from .conftest import panne_payload, pompage_payload, push
from core.models import Asset
from ops.models import DailyReading, Expense, FormSubmission, Incident, SafetyCheck, WaterQualityTest, WorkOrder
from stock.models import StockItem, StockMovement, balances

pytestmark = pytest.mark.django_db

ROWS = [{"pump": "TS-PMP-001", "start": "06:00", "stop": "10:00", "flow_m3h": 100, "pressure_bar": 5}]


def result(resp):
    assert resp.status_code == 200, resp.content
    return resp.json()["results"][0]


def test_create_update_conflict(client_for):
    c = client_for("pump")
    sid = uuid.uuid4()
    r = result(push(c, "POMPAGE", pompage_payload("2026-08-10", ROWS, kwh=40), sid))
    assert r["status"] == "created" and r["version"] == 1
    reading = DailyReading.objects.get(asset__code="TS-PMP-001", date="2026-08-10")
    assert reading.hours_run == 4 and reading.volume_m3 == 400  # 100 m³/h × 4 h
    assert DailyReading.objects.get(asset__code="TS-STP-001", date="2026-08-10").kwh == 40

    # Edit based on version 1 -> accepted, version 2, records rebuilt.
    rows = [dict(ROWS[0], stop="11:00")]
    r = result(push(c, "POMPAGE", pompage_payload("2026-08-10", rows, kwh=40), sid, base_version=1))
    assert r["status"] == "updated" and r["version"] == 2
    assert DailyReading.objects.get(asset__code="TS-PMP-001", date="2026-08-10").volume_m3 == 500

    # A second phone still on version 1 -> conflict with the server copy returned.
    r = result(push(c, "POMPAGE", pompage_payload("2026-08-10", ROWS, kwh=99), sid, base_version=1))
    assert r["status"] == "conflict" and r["server"]["version"] == 2
    # Same content re-sent (retry after a lost response) -> unchanged, not a conflict.
    r = result(push(c, "POMPAGE", pompage_payload("2026-08-10", rows, kwh=40), sid, base_version=1))
    assert r["status"] == "unchanged"
    # User chooses "keep mine" -> force.
    r = result(push(c, "POMPAGE", pompage_payload("2026-08-10", ROWS, kwh=99), sid, base_version=1, force=True))
    assert r["status"] == "updated" and r["version"] == 3


def test_two_shifts_same_day_are_summed(client_for):
    c = client_for("pump")
    result(push(c, "POMPAGE", pompage_payload("2026-08-11", ROWS, kwh=30)))
    result(push(c, "POMPAGE", pompage_payload("2026-08-11", [dict(ROWS[0], start="14:00", stop="16:00")], kwh=20)))
    reading = DailyReading.objects.get(asset__code="TS-PMP-001", date="2026-08-11")
    assert reading.hours_run == 6 and reading.volume_m3 == 600
    assert DailyReading.objects.get(asset__code="TS-STP-001", date="2026-08-11").kwh == 50


def test_validation_errors(client_for):
    c = client_for("pump")
    bad = pompage_payload("2026-08-12", [{"pump": "TS-PMP-001", "start": "06:00", "stop": "07:00", "flow_m3h": 9999}])
    bad["general"]["operator"] = ""
    r = result(push(c, "POMPAGE", bad))
    assert r["status"] == "invalid"
    fields = {e["field"] for e in r["errors"]}
    assert "general.operator" in fields and "pumps[0].flow_m3h" in fields
    assert not FormSubmission.objects.exists()


def test_wrong_asset_type_rejected(client_for):
    r = result(push(client_for("pump"), "POMPAGE", pompage_payload("2026-08-12", ROWS, station="TS-RES-001")))
    assert r["status"] == "invalid"


def test_roles(client_for):
    # A zone technician cannot file a pumping sheet; a funder cannot push at all.
    r = result(push(client_for("tech"), "POMPAGE", pompage_payload("2026-08-12", ROWS)))
    assert r["status"] == "forbidden"
    assert push(client_for("funder"), "POMPAGE", pompage_payload("2026-08-12", ROWS)).status_code == 403
    # Funders can read KPIs.
    assert client_for("funder").get("/api/kpi/?year=2026").status_code == 200
    # Only stock roles write stock movements.
    assert client_for("tech").post("/api/stock/movements/", {"item": "ART-T01", "date": "2026-08-01", "kind": "IN", "quantity": 5},
                                   format="json").status_code == 403
    assert client_for("adjoint").post("/api/stock/movements/", {"item": "ART-T01", "date": "2026-08-01", "kind": "IN", "quantity": 5},
                                      format="json").status_code == 201


def test_other_agent_cannot_overwrite(client_for, users):
    sid = uuid.uuid4()
    result(push(client_for("tech"), "PANNE", panne_payload("2026-08-13"), sid))
    r = result(push(client_for("pump"), "PANNE", panne_payload("2026-08-13"), sid, base_version=1))
    assert r["status"] == "forbidden"


def test_incident_derivation_stock_and_expense(client_for, site):
    tiny_png = "data:image/png;base64," + base64.b64encode(
        bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000")).decode()
    p = panne_payload("2026-08-14")
    p["description"]["photos"] = [tiny_png]
    r = result(push(client_for("tech"), "PANNE", p))
    assert r["status"] == "created"
    inc = Incident.objects.get()
    assert inc.number == "TS-INC-2026-0001"
    assert r["server"]["payload"]["general"]["number"] == inc.number
    assert inc.status == "CLOSED" and inc.downtime_hours == 5 and inc.downtime_cause == "PIPE_BURST"
    assert inc.node.code == "1.10" and inc.latitude == Decimal("-1.64")
    # Parts replaced leave the stock (S03): balance -3, below threshold -> alert.
    mv = StockMovement.objects.get()
    assert mv.kind == "OUT" and mv.quantity == 3 and mv.incident == inc
    item = StockItem.objects.get(code="ART-T01")
    assert balances(site)[item.id] == -3
    assert client_for("resp").get("/api/stock/alerts/").json()[0]["code"] == "ART-T01"
    # Actual spending recorded once, by maintenance type.
    assert Expense.objects.get().amount_usd == 120 and Expense.objects.get().maintenance_type == "URGENT"
    # Photo stored as an attachment, not kept as base64 in the payload.
    photos = FormSubmission.objects.get().payload["description"]["photos"]
    assert photos and "attachment" in photos[0]
    # Second incident gets the next number; re-deriving keeps number and does not duplicate stock/expense.
    result(push(client_for("tech"), "PANNE", panne_payload("2026-08-15")))
    assert Incident.objects.filter(number="TS-INC-2026-0002").exists()
    sub = FormSubmission.objects.get(incident=inc)
    from ops.derive import derive
    derive(sub)
    assert StockMovement.objects.filter(incident=inc).count() == 1 and Expense.objects.filter(incident=inc).count() == 1


def test_downtime_computed_when_blank(client_for):
    p = panne_payload("2026-08-16")
    del p["description"]["downtime_hours"]
    result(push(client_for("tech"), "PANNE", p))
    # detected 08:00, intervention end 13:00 -> 5 h
    assert Incident.objects.get().downtime_hours == 5


def test_network_form_billed_volume_and_quality(client_for):
    payload = {
        "general": {"zone": "Z1", "date": "2026-08-17", "agent": "Agent"},
        "network": [{"node": "1.1", "leak": "OUI", "cause": "VANDALISM"}],
        "kiosks": [{"kiosk": "TS-BF-01", "working": "OUI", "residual_chlorine": 0.3, "volume_sold_m3": 12.5},
                   {"kiosk": "TS-BF-02", "working": "NON", "residual_chlorine": 0.8, "volume_sold_m3": 4}],
        "complaints": [{"nature": "Coupure", "location": "BF02"}],
    }
    r = result(push(client_for("tech"), "RESEAU_BF", payload))
    assert r["status"] == "created"
    assert DailyReading.objects.get(asset__code="TS-BF-01").volume_m3 == Decimal("12.5")
    tests = {t.asset.code: t.compliant for t in WaterQualityTest.objects.all()}
    assert tests == {"TS-BF-01": True, "TS-BF-02": False}  # kiosk range 0.2–0.5 mg/L
    assert SafetyCheck.objects.filter(item="network[0]", ok=False).exists()


def test_preventive_checklist_closes_planned_work_order(client_for, site):
    pump = Asset.objects.get(code="TS-PMP-001")
    wo = WorkOrder.objects.create(site=site, title="MP", kind="PREVENTIVE", category="POMPAGE", asset=pump,
                                  planned_date="2026-08-05", status="PLANNED")
    payload = {"general": {"station": "TS-STP-001", "pump": "TS-PMP-001", "date": "2026-08-18", "technician": "T"},
               "mechanical": {"lubrication": {"state": "BON"}, "vibrations": {"state": "MAUVAIS", "observations": "roulement"}},
               "maintenance": [{"part": "Roulement", "cost_usd": 80, "due": "2026-09-01"}]}
    r = result(push(client_for("pump"), "MP_POMPE", payload))
    assert r["status"] == "created"
    wo.refresh_from_db()
    assert wo.status == "DONE" and str(wo.done_date) == "2026-08-18" and wo.findings[0]["part"] == "Roulement"
    assert WorkOrder.objects.count() == 1


def test_reference_bundle_etag(client_for):
    c = client_for("tech")
    r = c.get("/api/reference/")
    assert r.status_code == 200 and r.json()["forms"]["forms"][0]["type"] == "POMPAGE"
    assert c.get("/api/reference/", HTTP_IF_NONE_MATCH=r["ETag"]).status_code == 304


def test_manager_rejects_submission(client_for):
    result(push(client_for("pump"), "POMPAGE", pompage_payload("2026-08-19", ROWS)))
    sub = FormSubmission.objects.get()
    r = client_for("resp").patch(f"/api/submissions/{sub.id}/", {"status": "REJECTED"}, format="json")
    assert r.status_code == 200
    assert not DailyReading.objects.filter(date="2026-08-19", asset__code="TS-PMP-001").exists()
