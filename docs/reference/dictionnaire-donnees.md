<!-- Fichier généré par `python manage.py gen_docs` — ne pas modifier à la main. -->

# Dictionnaire de données

Toutes les tables de la plateforme, colonne par colonne. Vue d'ensemble et diagramme : [../data-model.md](../data-model.md).

Conventions : `null` = la colonne accepte l'absence de valeur ; les listes de valeurs autorisées sont données en code → libellé.

## `core` — Référentiel : sites, zones, actifs, réseau, personnel

### Asset

Table `core_asset`. Any physical equipment. Stable, human-readable ID in `code` (GO-PMP-001).

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule |
| `raw_label` | Char(255) |  | Libellé d'origine tel que saisi dans Excel |
| `flags` | JSON |  | Anomalies détectées à l'import (codes du rapport qualité) |
| `site` | FK → `Site` |  |  |
| `code` | Char(30) |  | unique |
| `name` | Char(200) |  |  |
| `type` | Char(30) |  | valeurs : `INTAKE` Captage, `PUMP` Groupe motopompe, `PUMP_STATION` Station de pompage, `CHLORINATION_UNIT` Unité de chloration, `DOSING_PUMP` Pompe doseuse, `TANK` Cuve / bac, `SOLAR_PANEL` Panneau solaire, `BATTERY` Batterie, `STORAGE_SITE` Site de stockage, `RESERVOIR` Réservoir, `KIOSK` Borne fontaine (kiosque), `PRIVATE_CONNECTION` Connexion privée, `GENSET` Groupe électrogène, `OTHER` Autre |
| `parent` | FK → `Asset` | oui |  |
| `zone` | FK → `Zone` | oui |  |
| `node` | FK → `Node` | oui |  |
| `latitude` | Decimal(10,7) | oui |  |
| `longitude` | Decimal(10,7) | oui |  |
| `altitude_m` | Decimal(8,2) | oui |  |
| `capacity_value` | Decimal(12,2) | oui |  |
| `capacity_unit` | Char(20) |  |  |
| `power_kw` | Decimal(8,2) | oui |  |
| `head_m` | Decimal(8,2) | oui |  |
| `specs` | Text |  |  |
| `condition` | Char(20) |  | valeurs : `GOOD` Bon, `FAIR` Moyen, `POOR` Mauvais, `OUT_OF_SERVICE` Hors service, `UNKNOWN` Inconnu |
| `install_date` | Date | oui |  |
| `built_by` | Char(120) |  |  |
| `om_documents` | Char(255) |  |  |
| `maintenance_frequency_days` | PositiveInteger | oui |  |
| `last_maintenance` | Date | oui |  |
| `next_maintenance` | Date | oui |  |
| `responsible` | FK → `Person` | oui |  |
| `attributes` | JSON |  | Attributs spécifiques au type (robinets, bénéficiaires, DN de raccordement…) |
| `active` | Boolean |  |  |

### Fitting

Table `core_fitting`. Valves, tees, reducers… counted per node (register sheet 3).

Unicité : (node, description)

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule |
| `raw_label` | Char(255) |  | Libellé d'origine tel que saisi dans Excel |
| `flags` | JSON |  | Anomalies détectées à l'import (codes du rapport qualité) |
| `node` | FK → `Node` |  |  |
| `description` | Char(160) |  |  |
| `dn` | PositiveInteger | oui |  |
| `quantity` | PositiveInteger |  |  |
| `condition` | Char(20) |  | valeurs : `GOOD` Bon, `FAIR` Moyen, `POOR` Mauvais, `OUT_OF_SERVICE` Hors service, `UNKNOWN` Inconnu |
| `note` | Text |  |  |

### Node

Table `core_node`. Network node. IDs are ALWAYS strings: "1.10" and "1.1" are different nodes.

Unicité : (site, code)

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule |
| `raw_label` | Char(255) |  | Libellé d'origine tel que saisi dans Excel |
| `flags` | JSON |  | Anomalies détectées à l'import (codes du rapport qualité) |
| `site` | FK → `Site` |  |  |
| `code` | Char(40) |  |  |
| `kind` | Char(20) |  | valeurs : `JUNCTION` Nœud / chambre de vannes, `SOURCE` Source / lac, `PUMP_STATION` Station de pompage, `RESERVOIR_OUTLET` Sortie réservoir, `OUTFALL` Exutoire (trop-plein / vidange), `DELIVERY` Point de livraison (BF / CP) |
| `zone` | FK → `Zone` | oui |  |
| `latitude` | Decimal(10,7) | oui |  |
| `longitude` | Decimal(10,7) | oui |  |
| `condition` | Char(20) |  | valeurs : `GOOD` Bon, `FAIR` Moyen, `POOR` Mauvais, `OUT_OF_SERVICE` Hors service, `UNKNOWN` Inconnu |
| `note` | Text |  |  |

### Person

Table `core_person`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule |
| `raw_label` | Char(255) |  | Libellé d'origine tel que saisi dans Excel |
| `flags` | JSON |  | Anomalies détectées à l'import (codes du rapport qualité) |
| `site` | FK → `Site` |  |  |
| `user` | FK → `User` | oui | unique |
| `full_name` | Char(160) |  |  |
| `title` | Char(160) |  |  |
| `role` | Char(20) |  | valeurs : `RESP_TECH` Responsable technique, `ADJOINT` Responsable technique adjoint (opérations, stock, logistique), `ZONE_TECH` Technicien de zone, `PUMP_FOCAL` Point focal pompage, `STORAGE_FOCAL` Point focal stockage, `SSE` Responsable SSE, `DATA_OFFICER` Responsable base de données, `FUNDER` Bailleur (lecture seule), `CONTRACTOR` Prestataire (non permanent) |
| `duties` | Text |  |  |
| `zone` | FK → `Zone` | oui |  |
| `permanent` | Boolean |  |  |
| `contract_start` | Date | oui |  |
| `contract_end` | Date | oui |  |
| `active` | Boolean |  |  |

### PipeSegment

Table `core_pipesegment`.

Unicité : (site, code)

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule |
| `raw_label` | Char(255) |  | Libellé d'origine tel que saisi dans Excel |
| `flags` | JSON |  | Anomalies détectées à l'import (codes du rapport qualité) |
| `site` | FK → `Site` |  |  |
| `code` | Char(60) |  |  |
| `from_node` | FK → `Node` | oui |  |
| `to_node` | FK → `Node` |  |  |
| `dn` | PositiveInteger |  | Diamètre nominal (mm) |
| `material` | Char(40) |  |  |
| `length_m` | Decimal(10,2) |  |  |
| `role` | Char(20) |  | valeurs : `MAIN` Conduite principale, `OVERFLOW` Trop-plein / vidange, `SERVICE` Branchement BF / CP, `RISING` Refoulement |
| `condition` | Char(20) |  | valeurs : `GOOD` Bon, `FAIR` Moyen, `POOR` Mauvais, `OUT_OF_SERVICE` Hors service, `UNKNOWN` Inconnu |
| `note` | Text |  |  |

### Sequence

Table `core_sequence`. Gap-tolerant, never-reused counters (incident numbers). Incremented under a row lock.

Unicité : (site, name)

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `name` | Char(40) |  |  |
| `value` | PositiveInteger |  |  |

### Site

Table `core_site`. A water network operated by Yme Jibu (Goma Ouest is the first one).

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `code` | Char(10) |  | unique |
| `name` | Char(120) |  |  |
| `description` | Text |  |  |
| `timezone` | Char(64) |  |  |

### StaffingNeed

Table `core_staffingneed`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule |
| `raw_label` | Char(255) |  | Libellé d'origine tel que saisi dans Excel |
| `flags` | JSON |  | Anomalies détectées à l'import (codes du rapport qualité) |
| `site` | FK → `Site` |  |  |
| `title` | Char(160) |  |  |
| `duties` | Text |  |  |
| `headcount` | PositiveInteger | oui |  |
| `permanent` | Boolean | oui |  |
| `duration_value` | PositiveInteger | oui |  |
| `duration_unit` | Char(10) |  | Unité non précisée dans Excel : à confirmer |
| `start` | Date | oui |  |
| `end` | Date | oui |  |
| `comment` | Text |  |  |

### Zone

Table `core_zone`.

Unicité : (site, code)

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `code` | Char(20) |  |  |
| `name` | Char(120) |  |  |

## `ops` — Exploitation : fiches, relevés, pannes, ordres de travail, qualité, dépenses

### Attachment

Table `ops_attachment`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `submission` | FK → `FormSubmission` | oui |  |
| `file` | File |  |  |
| `content_type` | Char(60) |  |  |
| `sha256` | Char(64) |  |  |
| `created_at` | DateTime |  |  |

### Complaint

Table `ops_complaint`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `source` | Char(10) |  | Origine de l'enregistrement — valeurs : `APP` Application, `IMPORT` Import Excel, `ADMIN` Saisie bureau |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule (import) |
| `flags` | JSON |  | Codes du rapport qualité concernant cet enregistrement |
| `created_at` | DateTime |  |  |
| `updated_at` | DateTime |  |  |
| `submission` | FK → `FormSubmission` |  |  |
| `zone` | FK → `Zone` | oui |  |
| `date` | Date |  |  |
| `nature` | Text |  |  |
| `location` | Char(200) |  |  |
| `action_taken` | Text |  |  |

### DailyReading

Table `ops_dailyreading`. One row per asset per day: pumps, reservoirs, kiosks (volume sold).

Unicité : (asset, date)

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `source` | Char(10) |  | Origine de l'enregistrement — valeurs : `APP` Application, `IMPORT` Import Excel, `ADMIN` Saisie bureau |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule (import) |
| `flags` | JSON |  | Codes du rapport qualité concernant cet enregistrement |
| `created_at` | DateTime |  |  |
| `updated_at` | DateTime |  |  |
| `asset` | FK → `Asset` |  |  |
| `date` | Date |  |  |
| `submission` | FK → `FormSubmission` | oui |  |
| `operator` | Char(160) |  |  |
| `hours_run` | Decimal(6,2) | oui |  |
| `pressure_bar` | Decimal(6,2) | oui |  |
| `pressure_in_bar` | Decimal(6,2) | oui |  |
| `pressure_out_bar` | Decimal(6,2) | oui |  |
| `flow_m3h` | Decimal(8,2) | oui |  |
| `current_a` | Decimal(8,2) | oui |  |
| `volume_m3` | Decimal(10,2) | oui | Pompe : volume pompé ; BF : volume vendu |
| `volume_in_m3` | Decimal(10,2) | oui |  |
| `volume_out_m3` | Decimal(10,2) | oui |  |
| `level_pct` | Decimal(5,1) | oui |  |
| `kwh` | Decimal(10,2) | oui |  |
| `fuel_l` | Decimal(10,2) | oui |  |
| `chlorine_g` | Decimal(10,2) | oui |  |
| `observations` | Text |  |  |

### Expense

Table `ops_expense`. Actual O&M spending — the single source for 'Dépense réelle' by maintenance type.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `source` | Char(10) |  | Origine de l'enregistrement — valeurs : `APP` Application, `IMPORT` Import Excel, `ADMIN` Saisie bureau |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule (import) |
| `flags` | JSON |  | Codes du rapport qualité concernant cet enregistrement |
| `created_at` | DateTime |  |  |
| `updated_at` | DateTime |  |  |
| `date` | Date |  |  |
| `maintenance_type` | Char(12) |  | valeurs : `ROUTINE` Exploitation de routine, `URGENT` Maintenance Urgente (MU), `CORRECTIVE` Maintenance Corrective (MC), `PREVENTIVE` Maintenance Préventive (MP), `SUPPORT` Autres activités de support |
| `amount_usd` | Decimal(12,2) |  |  |
| `description` | Char(255) |  |  |
| `incident` | FK → `Incident` | oui | unique |
| `work_order` | FK → `WorkOrder` | oui | unique |

### FormSubmission

Table `ops_formsubmission`. A field form exactly as filled on the phone (client-generated UUID).

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `source` | Char(10) |  | Origine de l'enregistrement — valeurs : `APP` Application, `IMPORT` Import Excel, `ADMIN` Saisie bureau |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule (import) |
| `flags` | JSON |  | Codes du rapport qualité concernant cet enregistrement |
| `created_at` | DateTime |  |  |
| `updated_at` | DateTime |  |  |
| `form_type` | Char(20) |  | valeurs : `POMPAGE` Fiche journalière — Station de pompage, `STOCKAGE` Fiche journalière — Stockage, `RESEAU_BF` Fiche journalière — Réseau et bornes fontaines, `PANNE` Rapport de panne / incident, `MP_POMPE` Checklist maintenance préventive — Pompe, `MP_RESERVOIR` Checklist maintenance préventive — Réservoir, `MP_RESEAU` Checklist maintenance préventive — Réseau |
| `date` | Date |  |  |
| `asset` | FK → `Asset` | oui |  |
| `zone` | FK → `Zone` | oui |  |
| `submitted_by` | FK → `User` | oui |  |
| `payload` | JSON |  |  |
| `status` | Char(12) |  | valeurs : `SUBMITTED` Soumis, `VALIDATED` Validé, `REJECTED` Rejeté |
| `version` | PositiveInteger |  |  |
| `client_updated_at` | DateTime | oui |  |
| `derivation_errors` | JSON |  |  |
| `assigned_number` | Char(30) |  | Numéro d'incident attribué par le serveur (jamais par le téléphone) |
| `derived_keys` | JSON |  | [code actif, date] des relevés alimentés par cette fiche |

### Incident

Table `ops_incident`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `source` | Char(10) |  | Origine de l'enregistrement — valeurs : `APP` Application, `IMPORT` Import Excel, `ADMIN` Saisie bureau |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule (import) |
| `flags` | JSON |  | Codes du rapport qualité concernant cet enregistrement |
| `created_at` | DateTime |  |  |
| `updated_at` | DateTime |  |  |
| `number` | Char(30) |  | unique |
| `submission` | FK → `FormSubmission` | oui | unique |
| `detected_at` | DateTime |  |  |
| `reported_by` | Char(160) |  |  |
| `asset` | FK → `Asset` | oui |  |
| `node` | FK → `Node` | oui |  |
| `zone` | FK → `Zone` | oui |  |
| `location_detail` | Char(255) |  |  |
| `latitude` | Decimal(10,7) | oui |  |
| `longitude` | Decimal(10,7) | oui |  |
| `description` | Text |  |  |
| `incident_type` | Char(120) |  |  |
| `severity` | Char(10) |  | valeurs : `LOW` Faible, `MEDIUM` Moyenne, `CRITICAL` Critique |
| `service_interrupted` | Boolean |  |  |
| `downtime_cause` | Char(25) |  | valeurs : `PUMP_FAILURE` Panne des pompes, `PIPE_BURST` Rupture des conduites, `POWER_CUT` Coupure d'électricité, `PLANNED_MAINTENANCE` Maintenance programmée, `OTHER` Autre |
| `downtime_hours` | Decimal(7,2) |  |  |
| `affected_zone` | Char(160) |  |  |
| `affected_population` | PositiveInteger | oui |  |
| `probable_cause` | Char(25) |  | valeurs : `VANDALISM` Vandalisme et vol, `OVERPRESSURE` Surpression, `SHALLOW_PIPE` Tuyau mal enfoui, `ILLEGAL_CONNECTION` Connexion illégale, `MISHANDLING` Mauvaise manipulation des accessoires par le technicien, `POOR_PIPE_QUALITY` Mauvaise qualité du tuyau, `POOR_BACKFILL` Mauvais remblai, `GROUND_MOVEMENT` Mouvement de terrain, `POOR_INSTALLATION` Mauvaise installation, `WATER_HAMMER` Coup de bélier, `FAULTY_CONNECTION` Connexion défectueuse, `OTHER` Autre / non déterminée |
| `root_cause` | Text |  |  |
| `nrw_cause` | Char(25) |  | valeurs : `PIPE_LEAK` Fuites physiques sur les conduites, `PIPE_BURST` Ruptures de conduites, `RESERVOIR_OVERFLOW` Débordements de réservoirs (trop-plein), `NETWORK_FLUSH` Purges du réseau, `DRAINING` Vidanges, `RESERVOIR_CLEANING` Eau utilisée pour le nettoyage des réservoirs, `FIREFIGHTING` Eau utilisée pour la lutte contre les incendies, `ILLEGAL_BRANCH` Branchements illégaux, `FAULTY_METER` Compteurs défectueux, `MISCALIBRATED_METER` Compteurs mal calibrés, `ILLEGAL_CONNECTION` Connexions illégales, `READING_ERROR` Erreurs de relevé, `UNBILLED_CONSUMPTION` Volumes consommés mais non facturés |
| `estimated_loss_m3` | Decimal(10,2) | oui |  |
| `maintenance_type` | Char(12) |  | valeurs : `ROUTINE` Exploitation de routine, `URGENT` Maintenance Urgente (MU), `CORRECTIVE` Maintenance Corrective (MC), `PREVENTIVE` Maintenance Préventive (MP), `SUPPORT` Autres activités de support |
| `intervention_start` | DateTime | oui |  |
| `intervention_end` | DateTime | oui |  |
| `team` | Text |  |  |
| `materials_used` | Text |  |  |
| `cost_usd` | Decimal(10,2) | oui |  |
| `status` | Char(12) |  | valeurs : `OPEN` Ouvert, `IN_PROGRESS` En cours, `CLOSED` Réparé / clôturé |
| `closed_at` | DateTime | oui |  |
| `verification` | JSON |  |  |
| `lessons` | JSON |  |  |

### QualityThreshold

Table `ops_qualitythreshold`. Configurable acceptable range per parameter and sampling point type (or asset).

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `parameter` | Char(20) |  | valeurs : `RESIDUAL_CHLORINE` Chlore résiduel (mg/L), `TURBIDITY` Turbidité (NTU), `ODOUR_COLOUR` Odeur/couleur anormale, `LAB` Test laboratoire |
| `asset_type` | Char(30) |  | Vide = tous les points |
| `asset` | FK → `Asset` | oui |  |
| `min_value` | Decimal(8,3) | oui |  |
| `max_value` | Decimal(8,3) | oui |  |
| `note` | Char(255) |  |  |
| `to_confirm` | Boolean |  | Valeur par défaut à valider par le Responsable technique |

### SafetyCheck

Table `ops_safetycheck`. One checked item of a daily or preventive checklist.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `source` | Char(10) |  | Origine de l'enregistrement — valeurs : `APP` Application, `IMPORT` Import Excel, `ADMIN` Saisie bureau |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule (import) |
| `flags` | JSON |  | Codes du rapport qualité concernant cet enregistrement |
| `created_at` | DateTime |  |  |
| `updated_at` | DateTime |  |  |
| `submission` | FK → `FormSubmission` |  |  |
| `asset` | FK → `Asset` | oui |  |
| `zone` | FK → `Zone` | oui |  |
| `date` | Date |  |  |
| `item` | Char(120) |  |  |
| `ok` | Boolean | oui |  |
| `location` | Char(160) |  |  |
| `observation` | Text |  |  |

### WaterQualityTest

Table `ops_waterqualitytest`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `source` | Char(10) |  | Origine de l'enregistrement — valeurs : `APP` Application, `IMPORT` Import Excel, `ADMIN` Saisie bureau |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule (import) |
| `flags` | JSON |  | Codes du rapport qualité concernant cet enregistrement |
| `created_at` | DateTime |  |  |
| `updated_at` | DateTime |  |  |
| `submission` | FK → `FormSubmission` | oui |  |
| `asset` | FK → `Asset` | oui |  |
| `date` | Date |  |  |
| `parameter` | Char(20) |  | valeurs : `RESIDUAL_CHLORINE` Chlore résiduel (mg/L), `TURBIDITY` Turbidité (NTU), `ODOUR_COLOUR` Odeur/couleur anormale, `LAB` Test laboratoire |
| `value` | Decimal(10,3) | oui |  |
| `compliant` | Boolean | oui |  |
| `is_lab` | Boolean |  |  |
| `corrective_action` | Text |  |  |

### WorkOrder

Table `ops_workorder`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `source` | Char(10) |  | Origine de l'enregistrement — valeurs : `APP` Application, `IMPORT` Import Excel, `ADMIN` Saisie bureau |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule (import) |
| `flags` | JSON |  | Codes du rapport qualité concernant cet enregistrement |
| `created_at` | DateTime |  |  |
| `updated_at` | DateTime |  |  |
| `title` | Char(200) |  |  |
| `kind` | Char(12) |  | valeurs : `ROUTINE` Exploitation de routine, `URGENT` Maintenance Urgente (MU), `CORRECTIVE` Maintenance Corrective (MC), `PREVENTIVE` Maintenance Préventive (MP), `SUPPORT` Autres activités de support |
| `category` | Char(12) |  | valeurs : `CAPTAGE` Captage, `POMPAGE` Pompage, `RESERVOIR` Réservoir, `RESEAU` Réseau, `BF` Bornes-fontaines |
| `asset` | FK → `Asset` | oui |  |
| `zone` | FK → `Zone` | oui |  |
| `planned_date` | Date |  |  |
| `done_date` | Date | oui |  |
| `status` | Char(10) |  | valeurs : `PLANNED` Planifié, `DONE` Réalisé, `CANCELLED` Annulé |
| `origin` | Char(10) |  | valeurs : `PLAN` Plan annuel, `MANUAL` Saisie bureau, `CHECKLIST` Créé par une checklist (non planifié) |
| `submission` | FK → `FormSubmission` | oui | Checklist qui a clôturé (ou créé) cet ordre de travail |
| `incident` | FK → `Incident` | oui |  |
| `plan_task` | FK → `ActionPlanTask` | oui |  |
| `downtime_hours` | Decimal(7,2) |  |  |
| `cost_usd` | Decimal(10,2) | oui |  |
| `findings` | JSON |  | Besoins de maintenance relevés (partie, matériel, MO, coût, échéance) |

## `stock` — Stock : articles et grand livre des mouvements

### StockItem

Table `stock_stockitem`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `code` | Char(30) |  | unique |
| `category` | Char(20) |  | valeurs : `PERFORMANCE` Équipement pour l'amélioration des performances, `OM_TOOLS` Outils, matériel et pièces de rechange E&M, `PPE` Équipements de protection individuelle, `LOGISTICS` Logistique et déplacement, `CHEMICAL` Produits chimiques de traitement |
| `group` | Char(160) |  | Sous-rubrique Excel (ex. « 1. Distribution - Tuyaux ») |
| `name` | Char(200) |  |  |
| `unit` | Char(30) |  |  |
| `rented` | Boolean | oui |  |
| `min_threshold` | Decimal(12,2) | oui |  |
| `monthly_requirement` | Decimal(12,2) | oui |  |
| `additional_need` | Decimal(12,2) | oui |  |
| `notes` | Text |  |  |
| `source_ref` | Char(255) |  |  |
| `flags` | JSON |  |  |

### StockMovement

Table `stock_stockmovement`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | UUID |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `source` | Char(10) |  | Origine de l'enregistrement — valeurs : `APP` Application, `IMPORT` Import Excel, `ADMIN` Saisie bureau |
| `source_ref` | Char(255) |  | Origine Excel : fichier!feuille!cellule (import) |
| `flags` | JSON |  | Codes du rapport qualité concernant cet enregistrement |
| `created_at` | DateTime |  |  |
| `updated_at` | DateTime |  |  |
| `item` | FK → `StockItem` |  |  |
| `date` | Date |  |  |
| `kind` | Char(10) |  | valeurs : `OPENING` Stock initial, `IN` Entrée, `OUT` Sortie, `ADJUST` Ajustement d'inventaire |
| `quantity` | Decimal(12,2) |  | Toujours positive sauf pour ADJUST |
| `incident` | FK → `Incident` | oui |  |
| `work_order` | FK → `WorkOrder` | oui |  |
| `reference` | Char(200) |  |  |

## `plan` — Planification : tarifs, budget, plan d'action

### ActionPlanTask

Table `plan_actionplantask`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `year` | PositiveInteger |  |  |
| `code` | Char(20) |  |  |
| `section` | Char(160) |  |  |
| `title` | Char(200) |  |  |
| `frequency` | Char(10) |  | valeurs : `DAILY` Journalière, `WEEKLY` Hebdomadaire, `MONTHLY` Mensuelle, `PERIODIC` Trimestrielle / semestrielle / annuelle |
| `asset` | FK → `Asset` | oui |  |
| `start` | Date | oui |  |
| `end` | Date | oui |  |
| `duration_days` | PositiveInteger | oui |  |
| `scheduled_dates` | JSON |  | Jours cochés dans le calendrier (ISO) |
| `progress_pct` | Decimal(5,1) | oui |  |
| `status_note` | Char(200) |  |  |
| `comment` | Text |  |  |
| `order` | PositiveInteger |  |  |
| `source_ref` | Char(255) |  |  |
| `flags` | JSON |  |  |

### BudgetLine

Table `plan_budgetline`.

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `month` | Date |  | 1er jour du mois budgété |
| `category` | Char(20) |  | valeurs : `STAFF` Besoin en personnel, `LOGISTICS` Besoin logistique, `TOOLS` Besoin en outils et équipements, `MATERIALS` Besoin en matériels et matériaux, `ENERGY` Besoin énergie, `COMMUNICATION` Besoin en communication, `OTHER` Autre |
| `activity` | Char(200) |  |  |
| `purpose` | Text |  |  |
| `maintenance_type` | Char(12) |  | valeurs : `ROUTINE` Exploitation de routine, `URGENT` Maintenance Urgente (MU), `CORRECTIVE` Maintenance Corrective (MC), `PREVENTIVE` Maintenance Préventive (MP), `SUPPORT` Autres activités de support |
| `unit` | Char(20) |  |  |
| `quantity` | Decimal(12,2) | oui |  |
| `unit_price_usd` | Decimal(12,2) | oui |  |
| `responsible` | Char(160) |  |  |
| `supplier` | Char(160) |  |  |
| `start` | Date | oui |  |
| `end` | Date | oui |  |
| `source_ref` | Char(255) |  |  |
| `flags` | JSON |  |  |

### MonthlyBudget

Table `plan_monthlybudget`. Monthly O&M envelope ('Budget prévu (USD)', O&M KPI row 70).

Unicité : (site, month)

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `month` | Date |  |  |
| `amount_usd` | Decimal(12,2) |  |  |
| `source_ref` | Char(255) |  |  |

### Tariff

Table `plan_tariff`. Dated unit prices. The KPI engine uses the tariff valid on the 1st of each month.

Unicité : (site, kind, valid_from)

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `kind` | Char(12) |  | valeurs : `ELECTRICITY` Électricité (USD/kWh), `FUEL` Carburant (USD/L) |
| `price_usd` | Decimal(8,4) |  |  |
| `valid_from` | Date |  |  |
| `source_ref` | Char(255) |  |  |

## `kpi` — Historique mensuel importé d'Excel

### MonthlyAggregate

Table `kpi_monthlyaggregate`. Monthly totals recorded before the app existed (imported from `O&M KPI`). Only rows with status ACTUAL override the values computed from records. PROVISIONAL rows are shown for comparison but never used in KPIs. Placeholder values (future months) are not imported at all.

Unicité : (site, month, metric)

| Colonne | Type | Null | Description |
|---|---|---|---|
| `id` | BigAuto |  | clé primaire |
| `site` | FK → `Site` |  |  |
| `month` | Date |  |  |
| `metric` | Char(60) |  |  |
| `value` | Decimal(14,4) |  |  |
| `status` | Char(12) |  | valeurs : `ACTUAL` Historique validé (mois clos), `PROVISIONAL` Provisoire — non utilisé dans les KPI |
| `source_ref` | Char(255) |  |  |
| `note` | Char(255) |  |  |

