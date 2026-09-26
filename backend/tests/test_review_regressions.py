"""Regressions found in the pre-merge review (numbers match the review report)."""
import base64
import uuid

import pytest

from core.models import Role
from ops.models import Attachment, DailyReading, FormSubmission, Incident, WorkOrder
from ops.derive import derive
from stock.models import StockMovement

from .conftest import make_user, panne_payload, pompage_payload, push

pytestmark = pytest.mark.django_db

ROW = {"pump": "TS-PMP-001", "start": "06:00", "stop": "10:00", "flow_m3h": 100}
PNG = "data:image/png;base64," + base64.b64encode(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000")).decode()


def res(resp):
    assert resp.status_code == 200, resp.content
    return resp.json()["results"][0]


def vol(code, day):
    r = DailyReading.objects.filter(asset__code=code, date=day).first()
    return r.volume_m3 if r else None


def test_1_edit_date_or_rows_leaves_no_stale_reading(client_for):
    c = client_for("pump")
    sid = uuid.uuid4()
    two_pumps = [ROW, dict(ROW, pump="TS-PMP-002")]
    res(push(c, "POMPAGE", pompage_payload("2026-08-10", two_pumps, kwh=40), sid))
    assert vol("TS-PMP-001", "2026-08-10") == 400 and vol("TS-PMP-002", "2026-08-10") == 400
    # Same sheet, date corrected and second pump removed.
    res(push(c, "POMPAGE", pompage_payload("2026-08-11", [ROW], kwh=40), sid, base_version=1))
    assert vol("TS-PMP-001", "2026-08-10") is None and vol("TS-PMP-002", "2026-08-10") is None
    assert not DailyReading.objects.filter(asset__code="TS-STP-001", date="2026-08-10").exists()
    assert vol("TS-PMP-001", "2026-08-11") == 400 and vol("TS-PMP-002", "2026-08-11") is None


def test_2_rejecting_one_shift_keeps_the_other(client_for):
    c = client_for("pump")
    s1, s2 = uuid.uuid4(), uuid.uuid4()
    res(push(c, "POMPAGE", pompage_payload("2026-08-12", [ROW]), s1))  # 400
    res(push(c, "POMPAGE", pompage_payload("2026-08-12", [dict(ROW, start="14:00", stop="16:00")]), s2))  # 200
    assert vol("TS-PMP-001", "2026-08-12") == 600
    r = client_for("resp").patch(f"/api/submissions/{s1}/", {"status": "REJECTED"}, format="json")
    assert r.status_code == 200
    assert vol("TS-PMP-001", "2026-08-12") == 200
    client_for("resp").patch(f"/api/submissions/{s1}/", {"status": "SUBMITTED"}, format="json")
    assert vol("TS-PMP-001", "2026-08-12") == 600


def test_3_resend_after_lost_response_is_unchanged_and_photos_not_duplicated(client_for):
    c = client_for("tech")
    sid = uuid.uuid4()
    p = panne_payload("2026-08-13")
    p["description"]["photos"] = [PNG]
    res(push(c, "PANNE", p, sid))
    # Phone never got the answer: resends the original (no number, base64 photo, no base version).
    r = res(push(c, "PANNE", p, sid))
    assert r["status"] == "unchanged"
    # "Keep mine" on a real edit: photo stored once, not twice.
    p2 = panne_payload("2026-08-13")
    p2["description"]["photos"] = [PNG]
    p2["general"]["location"] = "près du marché"
    r = res(push(c, "PANNE", p2, sid, base_version=1))
    assert r["status"] == "updated"
    assert Attachment.objects.filter(submission_id=sid).count() == 1
    # Removing the photo deletes the attachment.
    p2["description"]["photos"] = []
    res(push(c, "PANNE", p2, sid, base_version=2))
    assert Attachment.objects.filter(submission_id=sid).count() == 0


def test_4_one_bad_sheet_does_not_block_the_batch(client_for):
    c = client_for("tech")
    bad = panne_payload("2026-08-14")
    bad["description"]["affected_population"] = "1500.0"
    good = panne_payload("2026-08-14")
    resp = c.post("/api/sync/push/", {"items": [
        {"id": str(uuid.uuid4()), "form_type": "PANNE", "payload": bad},
        {"id": str(uuid.uuid4()), "form_type": "PANNE", "payload": good},
    ]}, format="json")
    assert resp.status_code == 200
    statuses = [r["status"] for r in resp.json()["results"]]
    assert statuses == ["created", "created"]
    assert Incident.objects.filter(affected_population=1500).exists()


def test_4b_unexpected_error_is_reported_per_item(client_for, monkeypatch):
    import ops.api as api
    calls = {"n": 0}
    real = api.derive

    def flaky(sub):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return real(sub)

    monkeypatch.setattr(api, "derive", flaky)
    c = client_for("pump")
    resp = c.post("/api/sync/push/", {"items": [
        {"id": str(uuid.uuid4()), "form_type": "POMPAGE", "payload": pompage_payload("2026-08-15", [ROW])},
        {"id": str(uuid.uuid4()), "form_type": "POMPAGE", "payload": pompage_payload("2026-08-16", [ROW])},
    ]}, format="json")
    assert [r["status"] for r in resp.json()["results"]] == ["error", "created"]
    assert FormSubmission.objects.count() == 1  # the failed one was rolled back


def test_5_rejecting_unplanned_checklist_removes_its_work_order(client_for):
    sid = uuid.uuid4()
    payload = {"general": {"station": "TS-STP-001", "pump": "TS-PMP-001", "date": "2026-08-18", "technician": "T"},
               "mechanical": {"lubrication": {"state": "BON"}}}
    res(push(client_for("pump"), "MP_POMPE", payload, sid))
    assert WorkOrder.objects.get().origin == "CHECKLIST"
    client_for("resp").patch(f"/api/submissions/{sid}/", {"status": "REJECTED"}, format="json")
    assert not WorkOrder.objects.exists()


def test_5b_rejecting_checklist_reopens_planned_work_order(client_for, site):
    from core.models import Asset
    wo = WorkOrder.objects.create(site=site, title="MP", kind="PREVENTIVE", category="POMPAGE", origin="PLAN",
                                  asset=Asset.objects.get(code="TS-PMP-001"), planned_date="2026-08-02")
    sid = uuid.uuid4()
    payload = {"general": {"station": "TS-STP-001", "pump": "TS-PMP-001", "date": "2026-08-18", "technician": "T"}}
    res(push(client_for("pump"), "MP_POMPE", payload, sid))
    wo.refresh_from_db()
    assert wo.status == "DONE"
    client_for("resp").patch(f"/api/submissions/{sid}/", {"status": "REJECTED"}, format="json")
    wo.refresh_from_db()
    assert wo.status == "PLANNED" and wo.done_date is None and wo.submission is None


@pytest.mark.parametrize("path", ["/api/kpi/?year=2026", "/api/kpi/export.xlsx", "/api/expenses/", "/api/incidents/",
                                  "/api/readings/", "/api/plan/budget-lines/", "/api/stock/items/", "/api/people/"])
def test_6_field_roles_cannot_read_dashboard_data(site, path):
    from rest_framework.test import APIClient
    for role in (Role.ZONE_TECH, Role.CONTRACTOR, Role.PUMP_FOCAL):
        c = APIClient()
        c.force_authenticate(make_user(site, f"u-{role}-{uuid.uuid4().hex[:6]}", role))
        assert c.get(path).status_code == 403, (role, path)
    assert c.get("/api/reference/").status_code == 200  # but the phone still gets its reference data


def test_6b_funder_reads_kpis_not_people_or_raw_sheets(client_for):
    f = client_for("funder")
    assert f.get("/api/kpi/?year=2026").status_code == 200
    assert f.get("/api/people/").status_code == 403
    assert f.get("/api/submissions/").status_code == 403


def test_7_incident_numbers_never_reused(client_for):
    c = client_for("tech")
    a, b = uuid.uuid4(), uuid.uuid4()
    res(push(c, "PANNE", panne_payload("2026-08-20"), a))
    res(push(c, "PANNE", panne_payload("2026-08-21"), b))
    assert Incident.objects.get(submission_id=b).number == "TS-INC-2026-0002"
    client_for("resp").patch(f"/api/submissions/{b}/", {"status": "REJECTED"}, format="json")
    assert not StockMovement.objects.filter(reference="TS-INC-2026-0002").exists()
    res(push(c, "PANNE", panne_payload("2026-08-22")))
    assert Incident.objects.filter(number="TS-INC-2026-0003").exists()
    # Restoring the rejected report gives it back its own number.
    client_for("resp").patch(f"/api/submissions/{b}/", {"status": "SUBMITTED"}, format="json")
    assert Incident.objects.get(submission_id=b).number == "TS-INC-2026-0002"


def test_derive_is_idempotent(client_for):
    sid = uuid.uuid4()
    res(push(client_for("pump"), "POMPAGE", pompage_payload("2026-08-23", [ROW], kwh=10), sid))
    sub = FormSubmission.objects.get(pk=sid)
    before = list(DailyReading.objects.values_list("asset__code", "date", "volume_m3", "kwh"))
    derive(sub)
    derive(sub)
    assert list(DailyReading.objects.values_list("asset__code", "date", "volume_m3", "kwh")) == before


def test_phone_cannot_choose_incident_number(client_for):
    p = panne_payload("2026-08-24")
    p["general"]["number"] = "TS-INC-2026-9990"
    res(push(client_for("tech"), "PANNE", p))
    assert Incident.objects.get().number == "TS-INC-2026-0001"


def test_changing_pump_on_checklist_gives_planned_order_back(client_for, site):
    from core.models import Asset
    wo = WorkOrder.objects.create(site=site, title="MP P1", kind="PREVENTIVE", category="POMPAGE", origin="PLAN",
                                  asset=Asset.objects.get(code="TS-PMP-001"), planned_date="2026-08-02")
    sid = uuid.uuid4()
    payload = {"general": {"station": "TS-STP-001", "pump": "TS-PMP-001", "date": "2026-08-18", "technician": "T"}}
    res(push(client_for("pump"), "MP_POMPE", payload, sid))
    payload["general"]["pump"] = "TS-PMP-002"
    res(push(client_for("pump"), "MP_POMPE", payload, sid, base_version=1))
    wo.refresh_from_db()
    assert wo.asset.code == "TS-PMP-001" and wo.status == "PLANNED"
    new = WorkOrder.objects.get(submission_id=sid)
    assert new.asset.code == "TS-PMP-002" and new.origin == "CHECKLIST" and new.status == "DONE"


def test_database_error_is_retried_not_failed(client_for, monkeypatch):
    from django.db import OperationalError
    import ops.api as api

    def down(*a, **k):
        raise OperationalError("server closed the connection")

    monkeypatch.setattr(api, "derive", down)
    r = res(push(client_for("pump"), "POMPAGE", pompage_payload("2026-08-25", [ROW])))
    assert r["status"] == "retry"
