"""Generate shared/forms.fr.json — the single definition of the 7 field forms.

The definitions reproduce workbook 2 ("Activités d'Exploitation") field for
field. Obvious typos are corrected in labels (see `typo_fixes`). Fields that do
not exist in the Excel forms but are required to compute KPIs are marked
`"added": true` and carry a `note` explaining why; the PWA shows them with an
"ajouté" badge so the team can review them.

Run:  python3 scripts/build_forms.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "shared" / "forms.fr.json"

WB = "2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx"


def f(key, label, type_="text", **kw):
    d = {"key": key, "label": label, "type": type_}
    d.update(kw)
    return d


def added(field, note):
    field["added"] = True
    field["note"] = note
    return field


def rows(*labels_keys):
    return [{"key": k, "label": l} for k, l in labels_keys]


ENUMS = {
    "bon_mauvais": [{"value": "BON", "label": "Bon"}, {"value": "MAUVAIS", "label": "Mauvais"}],
    "oui_non": [{"value": "OUI", "label": "Oui"}, {"value": "NON", "label": "Non"}],
    "gravite": [
        {"value": "LOW", "label": "Faible"},
        {"value": "MEDIUM", "label": "Moyenne"},
        {"value": "CRITICAL", "label": "Critique"},
    ],
    "source_energie": [
        {"value": "SNEL", "label": "SNEL (réseau)"},
        {"value": "GENSET", "label": "Groupe électrogène"},
        {"value": "SOLAR", "label": "Solaire"},
        {"value": "MIXED", "label": "Mixte"},
    ],
    "type_intervention": [
        {"value": "URGENT", "label": "Maintenance Urgente (MU)"},
        {"value": "CORRECTIVE", "label": "Maintenance Corrective (MC)"},
    ],
    "type_panne": [
        {"value": "FUITE", "label": "Fuite"},
        {"value": "RUPTURE", "label": "Rupture de conduite"},
        {"value": "PANNE_POMPE", "label": "Panne de pompe"},
        {"value": "PANNE_ELEC", "label": "Panne électrique / coupure"},
        {"value": "VANNE", "label": "Vanne / accessoire défectueux"},
        {"value": "BF", "label": "Borne fontaine endommagée"},
        {"value": "QUALITE", "label": "Qualité de l'eau"},
        {"value": "AUTRE", "label": "Autre"},
    ],
    "cause_panne": [
        {"value": "VANDALISM", "label": "Vandalisme et vol"},
        {"value": "OVERPRESSURE", "label": "Surpression"},
        {"value": "SHALLOW_PIPE", "label": "Tuyau mal enfoui"},
        {"value": "ILLEGAL_CONNECTION", "label": "Connexion illégale"},
        {"value": "MISHANDLING", "label": "Mauvaise manipulation des accessoires par le technicien"},
        {"value": "POOR_PIPE_QUALITY", "label": "Mauvaise qualité du tuyau"},
        {"value": "POOR_BACKFILL", "label": "Mauvais remblai"},
        {"value": "GROUND_MOVEMENT", "label": "Mouvement de terrain"},
        {"value": "POOR_INSTALLATION", "label": "Mauvaise installation"},
        {"value": "WATER_HAMMER", "label": "Coup de bélier"},
        {"value": "FAULTY_CONNECTION", "label": "Connexion défectueuse"},
        {"value": "OTHER", "label": "Autre / non déterminée"},
    ],
    "cause_arret": [
        {"value": "PUMP_FAILURE", "label": "Panne des pompes"},
        {"value": "PIPE_BURST", "label": "Rupture des conduites"},
        {"value": "POWER_CUT", "label": "Coupure d'électricité"},
        {"value": "PLANNED_MAINTENANCE", "label": "Maintenance programmée"},
        {"value": "OTHER", "label": "Autre"},
    ],
    "cause_perte_eau": [
        {"value": "PIPE_LEAK", "label": "Fuites physiques sur les conduites"},
        {"value": "PIPE_BURST", "label": "Ruptures de conduites"},
        {"value": "RESERVOIR_OVERFLOW", "label": "Débordements de réservoirs (trop-plein)"},
        {"value": "NETWORK_FLUSH", "label": "Purges du réseau"},
        {"value": "DRAINING", "label": "Vidanges"},
        {"value": "RESERVOIR_CLEANING", "label": "Eau utilisée pour le nettoyage des réservoirs"},
        {"value": "FIREFIGHTING", "label": "Eau utilisée pour la lutte contre les incendies"},
        {"value": "ILLEGAL_BRANCH", "label": "Branchements illégaux"},
        {"value": "FAULTY_METER", "label": "Compteurs défectueux"},
        {"value": "MISCALIBRATED_METER", "label": "Compteurs mal calibrés"},
        {"value": "ILLEGAL_CONNECTION", "label": "Connexions illégales"},
        {"value": "READING_ERROR", "label": "Erreurs de relevé"},
        {"value": "UNBILLED_CONSUMPTION", "label": "Volumes consommés mais non facturés"},
    ],
}

QUALITY_ROWS = rows(
    ("chlorine_g", "Qté chlore (g)"),
    ("residual_chlorine", "Chlore résiduel (mg/L)"),
    ("turbidity", "Turbidité (NTU)"),
    ("odour_colour", "Odeur/couleur anormale"),
)
QUALITY_ROWS[-1]["valueEnum"] = "oui_non"  # answered Oui/Non instead of a number
QUALITY_COLUMNS = [
    f("value", "Valeur", "number", min=0, max=10000),
    f("acceptable", "Valeur acceptable", "threshold", readonly=True),
    f("conforme", "Conforme ? (oui/non)", "enum", enum="oui_non", computed=True),
    f("action", "Action corrective", "text"),
]


def signature(*who):
    return {"key": "signature", "title": "Signature", "kind": "fields",
            "fields": [f(k, l, "text") for k, l in who]}


FORMS = [
    {
        "type": "POMPAGE",
        "title": "Fiche journalière d'exploitation – Station de pompage",
        "source": f"{WB}!1. Fiche journ_E&M_Pompage",
        "roles": ["PUMP_FOCAL", "RESP_TECH", "ADJOINT", "DATA_OFFICER"],
        "scope": {"asset_field": "general.station"},
        "sections": [
            {"key": "general", "title": "Informations générales", "kind": "fields", "fields": [
                f("station", "Nom de la station", "asset", assetTypes=["PUMP_STATION"], required=True),
                f("date", "Date", "date", required=True),
                f("operator", "Opérateur", "text", required=True),
                f("pump_specs", "Type de pompe et spécifications techniques", "asset_specs", readonly=True),
                f("energy_source", "Source d'énergie", "enum", enum="source_energie"),
            ]},
            {"key": "pumps", "title": "Fonctionnement des pompes", "kind": "table", "minRows": 1, "maxRows": 12, "columns": [
                f("time", "Heure", "time"),
                f("pump", "Pompe N°", "asset", assetTypes=["PUMP"], parentFrom="general.station", required=True),
                f("start", "Heure démarrage", "time", required=True),
                f("stop", "Heure arrêt", "time", required=True),
                f("current_a", "Intensité (A)", "number", min=0, max=1000),
                f("pressure_bar", "Pression (bar)", "number", min=0, max=60),
                f("flow_m3h", "Débit (m³/h)", "number", min=0, max=400),
                added(f("volume_m3", "Volume pompé (m³)", "number", min=0, max=10000),
                      "Nécessaire au rendement du réseau. Si vide : débit × durée de fonctionnement."),
                f("observations", "Observations", "text"),
            ]},
            {"key": "technical", "title": "Contrôle technique", "kind": "checklist",
             "rows": rows(("bearing", "Roulement"), ("vibrations", "Vibrations"), ("motor_temp", "Température moteur"),
                          ("leak", "Fuite huile/eau"), ("fuel_level", "Niveau carburant"),
                          ("panel", "État tableau électrique"), ("cabling", "État câblage")),
             "columns": [f("state", "État", "enum", enum="bon_mauvais"), f("observations", "Observations", "text")]},
            {"key": "energy", "title": "Consommation énergétique", "kind": "checklist",
             "rows": [{"key": "snel", "label": "SNEL", "unit": "kWh"}, {"key": "genset", "label": "Groupe électrogène", "unit": "L"}],
             "columns": [
                 f("quantity", "Quantité consommée", "number", min=0, max=5000, unitFromRow=True),
                 f("start", "Heure démarrage", "time"),
                 f("stop", "Heure arrêt", "time"),
                 f("reading_time", "Heure (relevé)", "time", note="Libellé Excel « Heure » ambigu : interprété comme l'heure du relevé."),
                 f("observation", "Observation", "text"),
             ]},
            {"key": "quality", "title": "Qualité de l'eau", "kind": "checklist", "rows": QUALITY_ROWS, "columns": QUALITY_COLUMNS},
            {"key": "maintenance", "title": "Maintenance effectuée", "kind": "fields", "fields": [
                f("maintenance_done", "Maintenance effectuée", "textarea"),
            ]},
            signature(("operator_sign", "Opérateur"), ("manager_sign", "Responsable O&M")),
        ],
    },
    {
        "type": "STOCKAGE",
        "title": "Fiche journalière d'exploitation – Stockage",
        "source": f"{WB}!2. Fiche journ_E&M_Stockage",
        "roles": ["STORAGE_FOCAL", "RESP_TECH", "ADJOINT", "DATA_OFFICER"],
        "scope": {"asset_field": "general.reservoir"},
        "sections": [
            {"key": "general", "title": "Informations générales", "kind": "fields", "fields": [
                f("reservoir", "Nom du réservoir", "asset", assetTypes=["RESERVOIR"], required=True),
                f("volume", "Volume", "asset_capacity", readonly=True),
                f("location", "Localisation", "asset_location", readonly=True),
                f("date", "Date", "date", required=True),
                f("operator", "Nom de l'opérateur", "text", required=True),
                f("service_start", "Heure de début de service", "time"),
                f("service_end", "Heure de fin de service", "time"),
            ]},
            {"key": "operations", "title": "Suivi opérationnel", "kind": "table", "minRows": 0, "maxRows": 24, "columns": [
                f("time", "Heure", "time", required=True),
                f("level_pct", "Niveau du réservoir (%)", "number", min=0, max=100,
                  note="Excel : « Niveau (volume ou %) » — séparé en deux colonnes pour éviter de mélanger les unités."),
                f("level_m3", "Niveau du réservoir (m³)", "number", min=0, max=5000),
                f("flow_in_m3h", "Débit entrant (m³/h)", "number", min=0, max=500),
                f("flow_out_m3h", "Débit sortant (m³/h)", "number", min=0, max=500),
                f("pressure_bar", "Pression réseau (bar)", "number", min=0, max=60),
                f("observations", "Observations", "text"),
            ]},
            {"key": "daily", "title": "Totaux journaliers", "kind": "fields", "fields": [
                added(f("volume_in_m3", "Volume entrant journalier (m³)", "number", min=0, max=20000),
                      "Colonne de la feuille STOCKAGE (base KPI), absente de la fiche papier."),
                added(f("volume_out_m3", "Volume sortant journalier (m³)", "number", min=0, max=20000),
                      "Colonne de la feuille STOCKAGE (base KPI), absente de la fiche papier."),
                added(f("pressure_in_bar", "Pression entrée (bar)", "number", min=0, max=60), "Colonne de la feuille STOCKAGE."),
                added(f("pressure_out_bar", "Pression sortie (bar)", "number", min=0, max=60), "Colonne de la feuille STOCKAGE."),
            ]},
            {"key": "safety", "title": "Contrôle de sécurité et état physique", "kind": "checklist",
             "rows": rows(("leak", "Présence de fuite"), ("valves", "État des vannes"), ("overflow", "État du trop-plein"),
                          ("ladders", "État des échelles"), ("intrusion", "Présence d'intrusion"), ("cover", "État du couvercle"),
                          ("ventilation", "Ventilation fonctionnelle")),
             "columns": [f("answer", "Oui / Non", "enum", enum="oui_non"), f("observations", "Observations", "text")]},
            {"key": "quality", "title": "Qualité de l'eau", "kind": "checklist", "rows": QUALITY_ROWS, "columns": QUALITY_COLUMNS},
            {"key": "incidents", "title": "Incidents ou anomalies observés", "kind": "fields", "fields": [
                f("incidents", "Incidents ou anomalies observés", "textarea"),
            ]},
            signature(("operator_sign", "Opérateur"), ("supervisor_sign", "Superviseur")),
        ],
    },
    {
        "type": "RESEAU_BF",
        "title": "Fiche journalière d'exploitation – Réseau et bornes fontaines",
        "source": f"{WB}!3. Fiche journ_E&M_Rés&BF",
        "intro": "Le réseau est divisé en zones et chaque zone a son agent terrain, chargé d'identifier tout dysfonctionnement, fuite, etc.",
        "roles": ["ZONE_TECH", "RESP_TECH", "ADJOINT", "DATA_OFFICER"],
        "scope": {"zone_field": "general.zone"},
        "sections": [
            {"key": "general", "title": "Informations générales", "kind": "fields", "fields": [
                f("zone", "Zone / Quartier", "zone", required=True),
                f("date", "Date", "date", required=True),
                f("agent", "Agent terrain", "text", required=True),
                added(f("far_pressure_bar", "Pression à la BF la plus éloignée (bar)", "number", min=0, max=60),
                      "Colonne de la feuille RESEAU (base KPI)."),
            ]},
            {"key": "network", "title": "Inspection du réseau", "kind": "table", "minRows": 0, "maxRows": 30, "columns": [
                f("node", "Localisation (nœud du réseau)", "node", required=True),
                f("reference", "Référence (repère)", "text"),
                f("leak", "Fuite observée", "enum", enum="oui_non"),
                f("low_pressure", "Pression faible", "enum", enum="oui_non"),
                f("damaged", "Accessoires endommagés", "text"),
                f("cause", "Cause probable du dommage", "enum", enum="cause_panne"),
                f("illegal", "Connexion illégale", "enum", enum="oui_non"),
                f("intervention", "Intervention réalisée", "text"),
                f("observation", "Observation", "text"),
            ]},
            {"key": "kiosks", "title": "Inspection des bornes fontaines", "kind": "table", "minRows": 0, "maxRows": 30, "columns": [
                f("kiosk", "N° BF", "asset", assetTypes=["KIOSK", "PRIVATE_CONNECTION"], zoneFrom="general.zone", required=True),
                f("working", "Fonctionnelle ? (oui/non)", "enum", enum="oui_non", required=True),
                f("state", "État de la robinetterie / drainage / propreté", "enum", enum="bon_mauvais"),
                f("damaged", "Accessoires endommagés", "text"),
                f("cause", "Cause probable du dommage", "enum", enum="cause_panne"),
                f("residual_chlorine", "Qualité – Chlore résiduel (mg/L)", "number", min=0, max=10),
                f("conforme", "Qualité conforme ? (oui/non)", "enum", enum="oui_non", computed=True),
                added(f("volume_sold_m3", "Volume vendu (m³)", "number", min=0, max=1000),
                      "Nécessaire pour l'eau facturée et l'eau non facturée (NRW). Colonne « Volume d'eau vendu » de la feuille RESEAU."),
                f("action", "Action corrective", "text"),
            ]},
            {"key": "complaints", "title": "Plaintes communautaires reçues", "kind": "table", "minRows": 0, "maxRows": 20, "columns": [
                f("nature", "Nature plainte", "text", required=True),
                f("location", "Localisation", "text"),
                f("action", "Action prise", "text"),
            ]},
            signature(("agent_sign", "Agent terrain"), ("supervisor_sign", "Superviseur")),
        ],
    },
    {
        "type": "PANNE",
        "title": "Formulaire de rapport de panne",
        "source": f"{WB}!4. Fiche E&M_Rapp. Panne",
        "intro": "Toute panne doit être signalée immédiatement par un agent terrain et le rapport envoyé dans les 24 h après le signalement.",
        "roles": ["ZONE_TECH", "PUMP_FOCAL", "STORAGE_FOCAL", "SSE", "RESP_TECH", "ADJOINT", "DATA_OFFICER", "CONTRACTOR"],
        "scope": {"asset_field": "description.asset", "zone_field": "general.zone"},
        "sections": [
            {"key": "general", "title": "Informations générales", "kind": "fields", "fields": [
                f("number", "Numéro incident", "auto", readonly=True, note="Attribué par le serveur à la synchronisation."),
                f("date", "Date", "date", required=True),
                f("detected_time", "Heure détection", "time", required=True),
                f("reported_by", "Rapporté par", "text", required=True),
                f("zone", "Zone", "zone"),
                f("node", "Localisation – Nœud", "node"),
                f("location", "Localisation – Référence", "text"),
                added(f("gps", "Position GPS", "gps"), "Position relevée par le téléphone."),
            ]},
            {"key": "description", "title": "Description de la panne", "kind": "fields", "fields": [
                f("incident_type", "Type de panne", "enum", enum="type_panne", required=True),
                f("asset", "Infrastructure / actif concerné(e)", "asset"),
                f("severity", "Gravité (Faible / Moyenne / Critique)", "enum", enum="gravite", required=True),
                f("service_interrupted", "Service interrompu ? (Oui / Non)", "enum", enum="oui_non", required=True),
                f("affected_zone", "Zone de la population affectée", "text"),
                added(f("affected_population", "Population affectée (nombre de personnes)", "integer", min=0, max=500000),
                      "Permet de mesurer l'impact des pannes."),
                added(f("downtime_cause", "Cause de l'arrêt du service", "enum", enum="cause_arret"),
                      "Répartition de la disponibilité (O&M KPI lignes 5-8)."),
                added(f("downtime_hours", "Durée d'arrêt du service (h)", "number", min=0, max=744),
                      "Disponibilité du réseau. Si vide : calculée de l'heure de détection à la fin d'intervention."),
                f("photos", "Photos", "photos", added=True, note="Photos compressées sur le téléphone (max 3)."),
            ]},
            {"key": "analysis", "title": "Analyse technique", "kind": "fields", "fields": [
                f("probable_cause", "Cause probable", "enum", enum="cause_panne", required=True),
                f("root_cause", "Cause racine identifiée", "textarea"),
                f("damage", "Dommages observés", "textarea"),
                f("risks", "Risques sécurité/santé", "textarea"),
                added(f("nrw_cause", "Cause de perte d'eau (si perte)", "enum", enum="cause_perte_eau"),
                      "Analyse des causes de l'eau non facturée (O&M KPI lignes 36-48)."),
                added(f("estimated_loss_m3", "Volume d'eau perdu estimé (m³)", "number", min=0, max=100000), "Eau non facturée."),
            ]},
            {"key": "intervention", "title": "Intervention réalisée", "kind": "fields", "fields": [
                f("maintenance_type", "Type : Maintenance Urgente (MU) ou Corrective (MC)", "enum", enum="type_intervention", required=True),
                f("start", "Heure début intervention", "datetime"),
                f("end", "Heure fin intervention", "datetime"),
                f("team", "Équipe / M.O mobilisée", "textarea"),
                f("materials", "Matériels utilisés", "textarea"),
                f("cost_usd", "Coût estimatif (USD)", "number", min=0, max=1000000),
                f("logistics", "Appui logistique", "textarea"),
            ]},
            {"key": "parts", "title": "Pièces remplacées", "kind": "table", "minRows": 0, "maxRows": 20,
             "note": "Chaque pièce sortie du stock est déduite automatiquement du stock.", "columns": [
                 f("item", "Pièce (article du stock)", "stock_item", required=True),
                 f("quantity", "Quantité", "number", min=0, max=100000, required=True),
             ]},
            {"key": "verification", "title": "Vérification après réparation", "kind": "checklist",
             "rows": rows(("pressure", "Pression rétablie"), ("no_leak", "Absence de fuite"), ("flush", "Rinçage de conduite"),
                          ("quality", "Qualité eau vérifiée"), ("restored", "Service restauré")),
             "columns": [f("answer", "Conforme ?", "enum", enum="oui_non"), f("observation", "Observation", "text")]},
            {"key": "lessons", "title": "Leçons apprises / actions préventives", "kind": "fields", "fields": [
                f("worked", "Qu'est-ce qui a marché", "textarea"),
                f("not_worked", "Qu'est-ce qui n'a pas marché", "textarea"),
                f("constraint", "Contrainte", "textarea"),
                f("preventive", "Actions préventives", "textarea"),
                f("recommendation", "Recommandation", "textarea"),
            ]},
            {"key": "validation", "title": "Validation", "kind": "fields", "fields": [
                f("technician_sign", "Technicien", "text"), f("manager_sign", "Responsable O&M", "text"),
            ]},
        ],
    },
]

MAINT_COLUMNS_POMPE = [
    f("part", "Description de la partie concernée", "text", required=True),
    f("materials", "Matériels / équipements en besoin", "text"),
    f("labour", "MO en besoin", "text"),
    f("cost_usd", "Coût estimatif (USD)", "number", min=0, max=1000000),
    f("due", "Échéance / date proposée de maintenance", "date"),
]
MAINT_COLUMNS = [
    f("part", "Description de la partie concernée", "text", required=True),
    f("materials", "Matériels / équipements / MO en besoin", "text"),
    f("cost_usd", "Coût estimatif (USD)", "number", min=0, max=1000000),
    f("due", "Échéance / date", "date"),
]

FORMS += [
    {
        "type": "MP_POMPE",
        "title": "Checklist – Maintenance préventive pompe",
        "source": f"{WB}!5. Checklist_Maint Prev_Pomp",
        "roles": ["PUMP_FOCAL", "RESP_TECH", "ADJOINT", "DATA_OFFICER", "CONTRACTOR"],
        "scope": {"asset_field": "general.pump"},
        "sections": [
            {"key": "general", "title": "Informations", "kind": "fields", "fields": [
                f("station", "Station", "asset", assetTypes=["PUMP_STATION"], required=True),
                f("pump", "Pompe N°", "asset", assetTypes=["PUMP"], parentFrom="general.station", required=True),
                f("date", "Date inspection", "date", required=True),
                f("technician", "Technicien", "text", required=True),
            ]},
            {"key": "mechanical", "title": "Contrôle mécanique", "kind": "checklist",
             "rows": rows(("lubrication", "Lubrification correcte"), ("vibrations", "Vibrations anormales"), ("noise", "Bruit anormal"),
                          ("alignment", "Alignement pompe-moteur"), ("bearings", "État des roulements")),
             "columns": [f("state", "Bon / Mauvais", "enum", enum="bon_mauvais"),
                         f("observations", "Observations / besoin en maintenance / échéance", "text")]},
            {"key": "electrical", "title": "Contrôle électrique", "kind": "checklist",
             "rows": rows(("current", "Intensité normale"), ("cabling", "État câblage"),
                          ("protection", "Protection électrique fonctionnelle"), ("earthing", "Mise à terre correcte")),
             "columns": [f("state", "Bon / Mauvais", "enum", enum="bon_mauvais"), f("observations", "Observation", "text")]},
            {"key": "performance", "title": "Contrôle performance", "kind": "checklist",
             "rows": [{"key": "flow", "label": "Débit", "unit": "m³/h"}, {"key": "pressure", "label": "Pression", "unit": "bar"},
                      {"key": "hours", "label": "Temps de fonctionnement", "unit": "h"},
                      {"key": "energy", "label": "Consommation énergie", "unit": "kWh"}],
             "columns": [f("value", "Valeur", "number", min=0, max=100000, unitFromRow=True),
                         f("state", "Bon / Mauvais", "enum", enum="bon_mauvais"), f("observations", "Observation", "text")]},
            {"key": "maintenance", "title": "Maintenance", "kind": "table", "minRows": 0, "maxRows": 10, "columns": MAINT_COLUMNS_POMPE},
            {"key": "validation", "title": "Validation", "kind": "fields", "fields": [
                f("technician_sign", "Technicien", "text"), f("manager_sign", "Responsable O&M", "text")]},
        ],
    },
    {
        "type": "MP_RESERVOIR",
        "title": "Checklist – Maintenance préventive réservoir",
        "source": f"{WB}!6. Checklist_Maint Prev_ Reserv",
        "roles": ["STORAGE_FOCAL", "RESP_TECH", "ADJOINT", "DATA_OFFICER", "CONTRACTOR"],
        "scope": {"asset_field": "general.reservoir"},
        "sections": [
            {"key": "general", "title": "Informations", "kind": "fields", "fields": [
                f("reservoir", "Réservoir", "asset", assetTypes=["RESERVOIR"], required=True),
                f("volume", "Volume", "asset_capacity", readonly=True),
                f("date", "Date inspection", "date", required=True),
                f("technician", "Technicien", "text", required=True),
            ]},
            {"key": "structural", "title": "Contrôles structurels", "kind": "checklist",
             "rows": rows(("cracks", "Présence fissures"), ("leak", "Présence fuite"), ("fence", "État clôture"),
                          ("ventilation", "État ventilation"), ("drainage", "Drainage autour du site"), ("lighting", "Éclairage"),
                          ("other", "Autres à signaler")),
             "columns": [f("answer", "Conforme ? (oui/non)", "enum", enum="oui_non"), f("observations", "Observations", "text")]},
            {"key": "sanitary", "title": "Contrôles sanitaires", "kind": "checklist",
             "rows": rows(("clean", "Réservoir propre"), ("no_contamination", "Absence contamination"),
                          ("chlorination", "Chloration correcte"), ("overflow", "Trop-plein fonctionnel")),
             "columns": [f("answer", "Conforme ? Oui/Non", "enum", enum="oui_non"), f("observations", "Observations", "text")]},
            {"key": "maintenance", "title": "Maintenance", "kind": "table", "minRows": 0, "maxRows": 10, "columns": MAINT_COLUMNS},
            {"key": "validation", "title": "Validation", "kind": "fields", "fields": [
                f("technician_sign", "Technicien", "text"), f("manager_sign", "Responsable O&M", "text")]},
        ],
    },
    {
        "type": "MP_RESEAU",
        "title": "Checklist – Maintenance préventive réseau",
        "source": f"{WB}!7. Checklist_Maint Prev_ Res",
        "roles": ["ZONE_TECH", "RESP_TECH", "ADJOINT", "DATA_OFFICER", "CONTRACTOR"],
        "scope": {"zone_field": "general.zone"},
        "sections": [
            {"key": "general", "title": "Informations générales", "kind": "fields", "fields": [
                f("zone", "Zone / Quartier", "zone", required=True),
                f("date", "Date", "date", required=True),
                f("technician", "Technicien", "text", required=True),
            ]},
            {"key": "network", "title": "Inspection réseau", "kind": "checklist",
             "rows": rows(("leaks", "Fuites détectées"), ("buried", "Tuyauterie correctement enfouie"), ("pressure", "Pression correcte"),
                          ("chambers", "Chambre de vannes disponible"), ("valves", "Vannes opérationnelles"),
                          ("air_valves", "Ventouses fonctionnelles"), ("anchors", "Supports / blocs d'ancrage stables")),
             "columns": [f("answer", "Oui / Non", "enum", enum="oui_non"), f("location", "Localisation (nœuds)", "text"),
                         f("observation", "Observation", "text")]},
            {"key": "kiosks", "title": "Contrôle bornes fontaines", "kind": "checklist",
             "rows": rows(("taps", "Robinets fonctionnels"), ("drainage", "Drainage correct"), ("clean", "Zone propre"),
                          ("no_stagnation", "Absence stagnation")),
             "columns": [f("answer", "Oui / Non", "enum", enum="oui_non"), f("location", "Localisation (N° BF)", "text"),
                         f("observation", "Observation", "text")]},
            {"key": "maintenance", "title": "Maintenance", "kind": "table", "minRows": 0, "maxRows": 10,
             "columns": MAINT_COLUMNS + [f("observation", "Observation", "text")]},
            {"key": "validation", "title": "Validation", "kind": "fields", "fields": [
                f("technician_sign", "Technicien", "text"), f("manager_sign", "Responsable O&M", "text")]},
        ],
    },
]

TYPO_FIXES = {
    "Fomulaire → Formulaire": f"{WB}!4. Fiche E&M_Rapp. Panne!B2",
    "Recommendation → Recommandation": f"{WB}!4. Fiche E&M_Rapp. Panne!B43",
    "Proprété → Propreté": f"{WB}!3. Fiche journ_E&M_Rés&BF!D22",
    "intentifié → identifié ; disfonctionnement → dysfonctionnement": f"{WB}!3. Fiche journ_E&M_Rés&BF!B3",
    "specifié → spécifié (parenthèse non fermée)": f"{WB}!3. Fiche journ_E&M_Rés&BF!B9",
    "enfuie → enfouie": f"{WB}!7. Checklist_Maint Prev_ Res!B10",
    "Etat → État": "plusieurs feuilles",
}


def main():
    doc = {"version": 1, "language": "fr", "enums": ENUMS, "forms": FORMS, "typo_fixes": TYPO_FIXES}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({len(FORMS)} forms)")


if __name__ == "__main__":
    main()
