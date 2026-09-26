"""Load and validate field-form payloads against shared/forms.fr.json.

Payload shape (identical on the phone and on the server):
    fields section    -> {"general": {"date": "2026-08-10", ...}}
    table section     -> {"pumps": [{"pump": "GO-PMP-001", ...}, ...]}
    checklist section -> {"technical": {"bearing": {"state": "BON", ...}, ...}}
"""
import datetime as dt
import json
from decimal import Decimal, InvalidOperation
from functools import lru_cache

from django.conf import settings

from core.models import Asset, Node, Zone


@lru_cache(maxsize=1)
def definitions():
    with open(settings.FORMS_DEFINITION_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def form_def(form_type):
    for form in definitions()["forms"]:
        if form["type"] == form_type:
            return form
    raise KeyError(form_type)


def get_path(payload, path):
    section, _, field = path.partition(".")
    return (payload.get(section) or {}).get(field)


def to_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError(f"nombre invalide : {value!r}")


def to_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def to_time(value):
    if value in (None, ""):
        return None
    h, m = str(value).split(":")[:2]
    return dt.time(int(h), int(m))


def to_datetime(value):
    if value in (None, ""):
        return None
    return dt.datetime.fromisoformat(str(value))


class Validator:
    def __init__(self, site, payload, form_type):
        self.site = site
        self.payload = payload or {}
        self.form = form_def(form_type)
        self.enums = {k: {o["value"] for o in v} for k, v in definitions()["enums"].items()}
        self.errors = []

    def err(self, where, msg):
        self.errors.append({"field": where, "message": msg})

    def check_value(self, where, spec, value):
        if value in (None, "", []):
            if spec.get("required"):
                self.err(where, "Champ obligatoire")
            return
        t = spec["type"]
        try:
            if t in ("number", "integer"):
                num = to_decimal(value)
                if t == "integer" and num != num.to_integral_value():
                    self.err(where, "Nombre entier attendu")
                if "min" in spec and num < Decimal(str(spec["min"])):
                    self.err(where, f"Valeur trop petite (min {spec['min']})")
                if "max" in spec and num > Decimal(str(spec["max"])):
                    self.err(where, f"Valeur trop grande (max {spec['max']})")
            elif t == "date":
                to_date(value)
            elif t == "time":
                to_time(value)
            elif t == "datetime":
                to_datetime(value)
            elif t == "enum":
                if value not in self.enums[spec["enum"]]:
                    self.err(where, f"Valeur non autorisée : {value}")
            elif t == "asset":
                qs = Asset.objects.filter(site=self.site, code=value)
                if spec.get("assetTypes"):
                    qs = qs.filter(type__in=spec["assetTypes"])
                if not qs.exists():
                    self.err(where, f"Actif inconnu ou de mauvais type : {value}")
            elif t == "zone":
                if not Zone.objects.filter(site=self.site, code=value).exists():
                    self.err(where, f"Zone inconnue : {value}")
            elif t == "node":
                if not Node.objects.filter(site=self.site, code=str(value)).exists():
                    self.err(where, f"Nœud inconnu : {value}")
            elif t == "stock_item":
                from stock.models import StockItem

                if not StockItem.objects.filter(site=self.site, code=value).exists():
                    self.err(where, f"Article de stock inconnu : {value}")
            elif t == "gps":
                lat, lon = float(value["lat"]), float(value["lon"])
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    self.err(where, "Coordonnées GPS invalides")
        except (ValueError, TypeError, KeyError) as exc:
            self.err(where, str(exc))

    def validate(self):
        for section in self.form["sections"]:
            data = self.payload.get(section["key"])
            kind = section["kind"]
            if kind == "fields":
                data = data or {}
                for spec in section["fields"]:
                    if spec.get("readonly"):
                        continue
                    self.check_value(f"{section['key']}.{spec['key']}", spec, data.get(spec["key"]))
            elif kind == "table":
                data = data or []
                if not isinstance(data, list):
                    self.err(section["key"], "Liste attendue")
                    continue
                if len(data) < section.get("minRows", 0):
                    self.err(section["key"], f"Au moins {section['minRows']} ligne(s)")
                if len(data) > section.get("maxRows", 1000):
                    self.err(section["key"], f"Au plus {section['maxRows']} lignes")
                for i, row in enumerate(data):
                    for spec in section["columns"]:
                        self.check_value(f"{section['key']}[{i}].{spec['key']}", spec, (row or {}).get(spec["key"]))
            elif kind == "checklist":
                data = data or {}
                for row in section["rows"]:
                    values = data.get(row["key"]) or {}
                    for spec in section["columns"]:
                        if spec.get("readonly") or spec.get("computed"):
                            continue
                        if spec["key"] == "value" and row.get("valueEnum"):
                            spec = dict(spec, type="enum", enum=row["valueEnum"])
                        self.check_value(f"{section['key']}.{row['key']}.{spec['key']}", spec, values.get(spec["key"]))
        # Cross-field rules.
        general = self.payload.get("general") or {}
        date = general.get("date")
        if date:
            try:
                if to_date(date) > dt.date.today() + dt.timedelta(days=1):
                    self.err("general.date", "Date dans le futur")
            except ValueError:
                pass
        return self.errors


def validate_payload(site, form_type, payload):
    return Validator(site, payload, form_type).validate()
