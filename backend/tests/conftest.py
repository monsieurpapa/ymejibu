import datetime as dt
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models import Asset, AssetType, Node, Person, Role, Site, Zone
from ops.models import QualityParameter, QualityThreshold
from plan.models import Tariff
from stock.models import StockItem

WORKBOOKS_PRESENT = all(
    any(Path(settings.WORKBOOK_DIR).glob(p))
    for p in ("1.*Registre*.xlsx", "2.*Exploitation*.xlsx", "3.*Stock*.xlsx", "4.*Personnel*.xlsx", "5.*KPI*.xlsx")
)
needs_workbooks = pytest.mark.skipif(not WORKBOOKS_PRESENT, reason="Classeurs Excel absents")

TODAY = dt.date(2026, 9, 27)


@pytest.fixture
def site(db):
    """A small, fully known test network (independent of the Excel files)."""
    s = Site.objects.create(code="TS", name="Test")
    z1 = Zone.objects.create(site=s, code="Z1", name="Zone 1")
    station = Asset.objects.create(site=s, code="TS-STP-001", name="Station", type=AssetType.PUMP_STATION)
    Asset.objects.create(site=s, code="TS-PMP-001", name="Pompe A", type=AssetType.PUMP, parent=station, capacity_value=100)
    Asset.objects.create(site=s, code="TS-PMP-002", name="Pompe B", type=AssetType.PUMP, parent=station, capacity_value=90)
    Asset.objects.create(site=s, code="TS-RES-001", name="Réservoir", type=AssetType.RESERVOIR, capacity_value=300, capacity_unit="m3")
    Asset.objects.create(site=s, code="TS-BF-01", name="BF01", type=AssetType.KIOSK, zone=z1)
    Asset.objects.create(site=s, code="TS-BF-02", name="BF02", type=AssetType.KIOSK, zone=z1)
    Node.objects.create(site=s, code="1.1", zone=z1)
    Node.objects.create(site=s, code="1.10", zone=z1)
    StockItem.objects.create(site=s, code="ART-T01", name="Manchon DN110", unit="Pièce", category="PERFORMANCE", min_threshold=2)
    Tariff.objects.create(site=s, kind=Tariff.Kind.ELECTRICITY, price_usd=Decimal("0.25"), valid_from=dt.date(2026, 1, 1))
    Tariff.objects.create(site=s, kind=Tariff.Kind.FUEL, price_usd=Decimal("1.7"), valid_from=dt.date(2026, 1, 1))
    QualityThreshold.objects.create(site=s, parameter=QualityParameter.RESIDUAL_CHLORINE, asset_type="", min_value=Decimal("0.2"),
                                    max_value=Decimal("1.0"))
    QualityThreshold.objects.create(site=s, parameter=QualityParameter.RESIDUAL_CHLORINE, asset_type=AssetType.KIOSK,
                                    min_value=Decimal("0.2"), max_value=Decimal("0.5"))
    return s


def make_user(site, username, role, zone=None):
    user = get_user_model().objects.create_user(username=username, password="x")
    Person.objects.create(site=site, user=user, title=username, role=role, zone=zone)
    return user


@pytest.fixture
def users(site):
    z1 = Zone.objects.get(site=site, code="Z1")
    return {
        "resp": make_user(site, "resp", Role.RESP_TECH),
        "pump": make_user(site, "pump", Role.PUMP_FOCAL),
        "tech": make_user(site, "tech", Role.ZONE_TECH, z1),
        "funder": make_user(site, "funder", Role.FUNDER),
        "adjoint": make_user(site, "adjoint", Role.ADJOINT),
    }


@pytest.fixture
def client_for(users):
    def make(name):
        c = APIClient()
        c.force_authenticate(users[name])
        return c
    return make


def pompage_payload(date, rows, station="TS-STP-001", kwh=None, fuel=None, residual=None):
    return {
        "general": {"station": station, "date": date, "operator": "Opérateur test", "energy_source": "SNEL"},
        "pumps": rows,
        "technical": {"bearing": {"state": "BON"}},
        "energy": {"snel": {"quantity": kwh}, "genset": {"quantity": fuel}},
        "quality": {"residual_chlorine": {"value": residual}} if residual is not None else {},
    }


def panne_payload(date, **over):
    p = {
        "general": {"date": date, "detected_time": "08:00", "reported_by": "Agent", "zone": "Z1", "node": "1.10",
                    "gps": {"lat": -1.64, "lon": 29.17}},
        "description": {"incident_type": "RUPTURE", "severity": "CRITICAL", "service_interrupted": "OUI",
                        "downtime_cause": "PIPE_BURST", "downtime_hours": 5},
        "analysis": {"probable_cause": "VANDALISM", "nrw_cause": "PIPE_BURST"},
        "intervention": {"maintenance_type": "URGENT", "start": f"{date}T09:00", "end": f"{date}T13:00", "cost_usd": 120},
        "parts": [{"item": "ART-T01", "quantity": 3}],
        "verification": {"restored": {"answer": "OUI"}},
    }
    for k, v in over.items():
        p[k] = v
    return p


def push(client, form_type, payload, sub_id=None, base_version=None, force=False):
    item = {"id": str(sub_id or uuid.uuid4()), "form_type": form_type, "payload": payload,
            "client_updated_at": "2026-09-01T10:00:00+02:00"}
    if base_version is not None:
        item["base_version"] = base_version
    if force:
        item["force"] = True
    resp = client.post("/api/sync/push/", {"items": [item]}, format="json")
    return resp
