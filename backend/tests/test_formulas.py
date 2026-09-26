"""Hand-checked KPI formulas (values computed on paper, see comments)."""
from decimal import Decimal

import pytest

from kpi import formulas as F


def test_hours_in_month():
    assert F.hours_in_month(2026, 1) == 744  # 31 × 24
    assert F.hours_in_month(2026, 2) == 672  # 28 × 24 (2026 is not a leap year)
    assert F.hours_in_month(2026, 4) == 720


def test_availability():
    # March: 744 h, 22 h of downtime -> 722 / 744 = 0.970430…
    assert F.availability(744, 22) == Decimal(722) / Decimal(744)
    assert round(float(F.availability(744, 22)), 6) == 0.970430
    assert F.availability(744, 0) == 1
    assert F.availability(744, 800) == 0  # clamped, never negative
    assert F.availability(0, 5) is None
    assert F.availability(744, None) is None


def test_efficiency_and_nrw():
    # 240 m³ sold out of 300 m³ pumped -> 80 % efficiency, 60 m³ NRW
    assert F.network_efficiency(240, 300) == Decimal("0.8")
    assert F.nrw_m3(300, 240) == 60
    # Unknown billed volume: no NRW figure at all (not "100 % loss")
    assert F.nrw_m3(300, None) is None
    assert F.network_efficiency(None, 300) is None


def test_energy():
    # 150 kWh × 0.25 + 30 L × 1.7 = 37.5 + 51 = 88.5 USD ; / 300 m³ = 0.295 USD/m³
    cost = F.energy_cost(150, Decimal("0.25"), 30, Decimal("1.7"))
    assert cost == Decimal("88.5")
    assert F.intensity(cost, 300) == Decimal("0.295")
    assert F.intensity(150, 300) == Decimal("0.5")  # kWh/m³
    assert F.intensity(30, 300) == Decimal("0.1")  # L/m³
    assert F.energy_cost(None, Decimal("0.25"), None, Decimal("1.7")) is None
    assert F.energy_cost(150, None, None, None) is None  # no tariff -> no cost


def test_rates():
    assert F.repair_rate(2, 3) == Decimal(2) / Decimal(3)
    assert F.completion_rate(3, 4) == Decimal("0.75")
    assert F.completion_rate(0, 0) is None
    assert F.variance(1000, 1200) == -200
    assert F.share(100, 1000) == Decimal("0.1")
    assert F.compliance_rate(4, 5) == Decimal("0.8")


@pytest.mark.parametrize("value,expected", [(Decimal("0.123456"), 0.1235), (None, None)])
def test_round(value, expected):
    assert F.round_or_none(value) == expected
