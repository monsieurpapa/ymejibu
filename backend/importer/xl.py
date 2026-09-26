"""Read-only access to the five source workbooks."""
import datetime as dt
import re
import warnings
from functools import cached_property
from pathlib import Path

import openpyxl

WORKBOOK_PATTERNS = {
    "assets": "1.*Registre des Actifs*.xlsx",
    "forms": "2.*Activit*Exploitation*.xlsx",
    "stock": "3.*Stock*.xlsx",
    "staff": "4.*Personnel*.xlsx",
    "kpi": "5.*KPI*.xlsx",
}
SHORT = {"assets": "Classeur 1 (Registre des actifs)", "forms": "Classeur 2 (Activités d'exploitation)",
         "stock": "Classeur 3 (Stock)", "staff": "Classeur 4 (Personnel)", "kpi": "Classeur 5 (Base KPI)"}


class Workbooks:
    """Opens each workbook twice: formulas and cached values. Never saves."""

    def __init__(self, directory):
        self.dir = Path(directory)
        self.paths = {}
        for key, pattern in WORKBOOK_PATTERNS.items():
            found = sorted(self.dir.glob(pattern))
            if not found:
                raise FileNotFoundError(f"Classeur introuvable ({pattern}) dans {self.dir}")
            self.paths[key] = found[0]
        self._f, self._v = {}, {}

    def name(self, key):
        return self.paths[key].name

    def _load(self, key, data_only):
        cache = self._v if data_only else self._f
        if key not in cache:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # read_only=False so merged ranges and number formats are available.
                cache[key] = openpyxl.load_workbook(self.paths[key], data_only=data_only)
        return cache[key]

    def f(self, key, sheet):
        """Worksheet with formulas."""
        return self._load(key, False)[sheet]

    def v(self, key, sheet):
        """Worksheet with cached values."""
        return self._load(key, True)[sheet]

    def ref(self, key, sheet, cell):
        return f"{self.name(key)}!{sheet}!{cell}"


def clean(value):
    """Strip strings; whitespace-only strings become None."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


PLACEHOLDER_RE = re.compile(r"^\d+\.?\s*$")


def is_placeholder(value):
    """Numbered empty slots like '3.' or '4. '."""
    return isinstance(value, str) and bool(PLACEHOLDER_RE.match(value))


def strip_number(label):
    """'1. Tuyaux PEHD DN 110' -> 'Tuyaux PEHD DN 110'."""
    if not isinstance(label, str):
        return label
    return re.sub(r"^\s*\d+\s*[.)]\s*", "", label).strip()


def node_code(cell):
    """Node IDs as strings, respecting the displayed number format.

    A float 1.1 displayed with format '0.00' is node "1.10" (see the comment
    'au Noeud 1.10' next to it); with 'General' it is node "1.1".
    """
    v = cell.value
    if v is None:
        return None
    if isinstance(v, (int, float)):
        fmt = cell.number_format or "General"
        m = re.fullmatch(r"0\.(0+)", fmt)
        if m:
            return f"{v:.{len(m.group(1))}f}"
        return f"{v:g}"
    return str(v).strip()


def parse_gps(text):
    """'Long: 29.15\\nLat: -1.63\\nAlt: 1500' -> (lat, lon, alt) floats or None."""
    if not isinstance(text, str):
        return None, None, None
    def grab(label):
        m = re.search(label + r"\s*:\s*(-?\d+(?:[.,]\d+)?)", text, re.I)
        return float(m.group(1).replace(",", ".")) if m else None
    return grab("Lat"), grab("Long"), grab("Alt")


CAPACITY_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(m3\s*/\s*h(?:r)?|m3|l\s*/\s*h(?:r)?|l\b|kwh|w\b)", re.I)
UNIT_MAP = {"m3/hr": "m3/h", "m3/h": "m3/h", "m3": "m3", "l/hr": "L/h", "l/h": "L/h", "l": "L", "kwh": "kWh", "w": "W"}


def parse_capacity(text):
    if not isinstance(text, str):
        return None, ""
    m = CAPACITY_RE.search(text)
    if not m:
        return None, ""
    unit = re.sub(r"\s", "", m.group(2).lower())
    return float(m.group(1).replace(",", ".")), UNIT_MAP.get(unit, unit)


MONTHS_FR = {"janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
             "aout": 8, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12}


def parse_month_year(text):
    """'Septembre 2026' -> date(2026, 9, 1)."""
    if isinstance(text, dt.datetime):
        return text.date()
    if not isinstance(text, str):
        return None
    m = re.search(r"([A-Za-zéû]+)\s+(\d{4})", text)
    if not m or m.group(1).lower() not in MONTHS_FR:
        return None
    return dt.date(int(m.group(2)), MONTHS_FR[m.group(1).lower()], 1)


def is_formula(value):
    return isinstance(value, str) and value.startswith("=")
