"""What the indicators screen and the PDF report show: one catalogue, served by /api/kpi/.

Keeping titles, formats, targets and breakdown labels here (instead of in the
React code) guarantees the dashboard and the PDF always say the same thing.
Default targets are to be confirmed by the Responsable technique (docs/reference/kpi.md).
"""
from ops.models import DowntimeCause, FailureCause, NRWCause, WorkOrder

# key, title, format, target (value, label, better) or None, help
KPIS = [
    {"key": "availability", "title": "Disponibilité du réseau", "fmt": "pct",
     "target": {"value": 0.95, "label": "cible 95 %", "better": "up"}, "help": "(heures du mois − heures d'arrêt) / heures du mois"},
    {"key": "efficiency", "title": "Rendement du réseau", "fmt": "pct",
     "target": {"value": 0.8, "label": "cible 80 %", "better": "up"}, "help": "eau facturée / eau introduite"},
    {"key": "nrw_m3", "title": "Eau non facturée", "fmt": "m3", "target": None, "better": "down", "help": "eau introduite − eau facturée"},
    {"key": "repair_rate", "title": "Taux de réparation des pannes", "fmt": "pct",
     "target": {"value": 0.9, "label": "cible 90 %", "better": "up"}, "help": "pannes clôturées / pannes signalées (registre des pannes)"},
    {"key": "pm_rate", "title": "Taux de maintenance préventive", "fmt": "pct",
     "target": {"value": 0.9, "label": "cible 90 %", "better": "up"}, "help": "ordres de travail préventifs réalisés / planifiés"},
    {"key": "quality_rate", "title": "Conformité de la qualité de l'eau", "fmt": "pct",
     "target": {"value": 0.95, "label": "cible 95 %", "better": "up"}, "help": "mesures conformes / mesures (chlore résiduel, turbidité, laboratoire)"},
    {"key": "energy_cost_per_m3", "title": "Coût énergétique par m³", "fmt": "usd3", "target": None, "better": "down",
     "help": "(kWh × tarif + litres × prix) / m³ pompés"},
    {"key": "kwh_per_m3", "title": "Intensité électrique", "fmt": "dec3", "target": None, "better": "down", "help": "kWh / m³ pompés"},
    {"key": "budget_variance", "title": "Écart budgétaire", "fmt": "usd",
     "target": {"value": 0, "label": "budget", "better": "down"}, "help": "dépenses réelles − budget prévu (négatif = sous le budget)"},
    {"key": "incidents_reported", "title": "Pannes signalées", "fmt": "int", "target": None, "better": "down", "help": "nombre de pannes par mois"},
]
for _k in KPIS:
    _k.setdefault("better", (_k["target"] or {}).get("better"))

TABLE_ROWS = [
    ("volume_introduced", "Eau introduite", "m3"),
    ("volume_billed", "Eau facturée", "m3"),
    ("nrw_m3", "Eau non facturée", "m3"),
    ("efficiency", "Rendement", "pct"),
    ("downtime_total", "Heures d'arrêt", "h"),
    ("availability", "Disponibilité", "pct"),
    ("incidents_reported", "Pannes signalées", "int"),
    ("incidents_closed", "Pannes réparées", "int"),
    ("repair_rate", "Taux de réparation", "pct"),
    ("pm_planned_total", "Maintenances préventives prévues", "int"),
    ("pm_done_total", "Maintenances préventives réalisées", "int"),
    ("pm_rate", "Taux de maintenance préventive", "pct"),
    ("kwh", "Électricité (kWh)", "int"),
    ("fuel_l", "Carburant (L)", "int"),
    ("energy_cost_per_m3", "Coût énergétique / m³", "usd3"),
    ("budget", "Budget prévu", "usd"),
    ("actual_total", "Dépense réelle", "usd"),
    ("budget_variance", "Écart budgétaire", "usd"),
    ("quality_rate", "Conformité qualité", "pct"),
]

DOWNTIME_ITEMS = [
    ("downtime_pump", DowntimeCause.PUMP_FAILURE.label),
    ("downtime_pipe", DowntimeCause.PIPE_BURST.label),
    ("downtime_power", DowntimeCause.POWER_CUT.label),
    ("downtime_planned", DowntimeCause.PLANNED_MAINTENANCE.label),
    ("downtime_other", DowntimeCause.OTHER.label),
]

# Breakdowns shown in the monthly detail (bars of the month's base quantities).
BREAKDOWNS = [
    {"key": "downtime", "title": "Heures d'arrêt par cause", "fmt": "h", "items": DOWNTIME_ITEMS},
    {"key": "rca", "title": "Pannes par cause racine", "fmt": "int", "items": [(f"rca_{c}", lbl) for c, lbl in FailureCause.choices]},
    {"key": "nrw", "title": "Pertes d'eau par cause", "fmt": "int", "items": [(f"nrw_{c}", lbl) for c, lbl in NRWCause.choices]},
    {"key": "costs", "title": "Dépenses par type de maintenance", "fmt": "usd", "items": [
        ("cost_urgent", "Maintenance urgente (MU)"), ("cost_corrective", "Maintenance corrective (MC)"),
        ("cost_preventive", "Maintenance préventive (MP)"), ("cost_routine", "Exploitation de routine"),
        ("cost_support", "Activités de support")]},
]

# Key figures of the month (label, key, format), grouped.
FIGURES = [
    ("Eau et pertes", [("Eau introduite", "volume_introduced", "m3"), ("Eau facturée", "volume_billed", "m3"),
                       ("Eau non facturée", "nrw_m3", "m3"), ("Taux d'eau non facturée", "nrw_rate", "pct"),
                       ("Événements de perte d'eau", "nrw_events", "int")]),
    ("Fonctionnement", [("Heures du mois", "period_hours", "h"), ("Heures d'arrêt", "downtime_total", "h"),
                        ("Heures de fonctionnement", "operating_hours", "h"), ("Pannes signalées", "incidents_reported", "int"),
                        ("Pannes réparées", "incidents_closed", "int")]),
    ("Énergie", [("Électricité", "kwh", "kwh"), ("Carburant", "fuel_l", "l"), ("Coût électricité", "cost_electricity", "usd"),
                 ("Coût carburant", "cost_fuel", "usd"), ("Coût énergétique total", "energy_cost", "usd")]),
    ("Budget", [("Budget prévu", "budget", "usd"), ("Dépense réelle", "actual_total", "usd"), ("Écart", "budget_variance", "usd")]),
    ("Qualité de l'eau", [("Tests terrain", "quality_field_total", "int"), ("dont conformes", "quality_field_compliant", "int"),
                          ("Analyses laboratoire", "quality_lab_total", "int"), ("dont conformes", "quality_lab_compliant", "int")]),
]

PM_CATEGORIES = list(WorkOrder.Category.choices)


def as_json():
    return {
        "kpis": KPIS,
        "table_rows": [{"key": k, "label": lbl, "fmt": f} for k, lbl, f in TABLE_ROWS],
        "breakdowns": [dict(b, items=[{"key": k, "label": lbl} for k, lbl in b["items"]]) for b in BREAKDOWNS],
        "figures": [{"title": t, "items": [{"label": lbl, "key": k, "fmt": f} for lbl, k, f in items]} for t, items in FIGURES],
        "pm_categories": [{"key": k, "label": lbl} for k, lbl in PM_CATEGORIES],
    }
