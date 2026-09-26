"""Pure KPI formulas. No database access, no Excel cell references.

Every function returns None when the inputs do not allow an honest answer
(missing data, division by zero) instead of silently returning 0 or 100 %.
"""
import calendar
from decimal import ROUND_HALF_UP, Decimal

D0 = Decimal(0)


def dec(v):
    if v is None:
        return None
    return v if isinstance(v, Decimal) else Decimal(str(v))


def hours_in_month(year, month):
    return Decimal(calendar.monthrange(year, month)[1] * 24)


def ratio(num, den):
    num, den = dec(num), dec(den)
    if num is None or den is None or den == 0:
        return None
    return num / den


def availability(period_hours, downtime_hours):
    """(period hours − downtime hours) / period hours."""
    period, down = dec(period_hours), dec(downtime_hours)
    if period is None or period <= 0 or down is None:
        return None
    down = min(max(down, D0), period)
    return (period - down) / period


def network_efficiency(billed_m3, introduced_m3):
    """Rendement = eau facturée / eau introduite. None if either volume is unknown."""
    return ratio(billed_m3, introduced_m3)


def nrw_m3(introduced_m3, billed_m3):
    """Eau non facturée = introduite − facturée. None if billed volume is unknown (never '100 % loss')."""
    introduced, billed = dec(introduced_m3), dec(billed_m3)
    if introduced is None or billed is None:
        return None
    return introduced - billed


def intensity(quantity, volume_m3):
    """kWh/m³, L/m³, USD/m³ … = quantity / volume pumped."""
    return ratio(quantity, volume_m3)


def energy_cost(kwh, price_kwh, fuel_l, price_fuel):
    """(kWh × tariff) + (L × fuel price). Missing consumption counts as 0 only if the other is known."""
    kwh, fuel = dec(kwh), dec(fuel_l)
    if kwh is None and fuel is None:
        return None
    total = D0
    if kwh is not None:
        if price_kwh is None:
            return None
        total += kwh * dec(price_kwh)
    if fuel is not None:
        if price_fuel is None:
            return None
        total += fuel * dec(price_fuel)
    return total


def repair_rate(closed, reported):
    return ratio(closed, reported)


def completion_rate(done, planned):
    return ratio(done, planned)


def variance(actual, budget):
    actual, budget = dec(actual), dec(budget)
    if actual is None or budget is None:
        return None
    return actual - budget


def share(part, total):
    return ratio(part, total)


def compliance_rate(compliant, total):
    return ratio(compliant, total)


def round_or_none(v, places=4):
    if v is None:
        return None
    q = Decimal(1).scaleb(-places)
    return float(dec(v).quantize(q, rounding=ROUND_HALF_UP))
