<!-- Fichier généré par `python manage.py gen_docs` — ne pas modifier à la main. -->

# Formulaires terrain

Les 7 fiches de l'application mobile, champ par champ. Source unique : `shared/forms.fr.json`, généré par `scripts/build_forms.py` (voir [../guides/modifier-un-formulaire.md](../guides/modifier-un-formulaire.md)).

Colonne « Ajouté » : champ absent de la fiche Excel d'origine, ajouté car nécessaire au calcul d'un indicateur.

| Formulaire | Code | Rôles autorisés |
|---|---|---|
| [Fiche journalière d'exploitation – Station de pompage](#pompage) | `POMPAGE` | PUMP_FOCAL, RESP_TECH, ADJOINT, DATA_OFFICER |
| [Fiche journalière d'exploitation – Stockage](#stockage) | `STOCKAGE` | STORAGE_FOCAL, RESP_TECH, ADJOINT, DATA_OFFICER |
| [Fiche journalière d'exploitation – Réseau et bornes fontaines](#reseau_bf) | `RESEAU_BF` | ZONE_TECH, RESP_TECH, ADJOINT, DATA_OFFICER |
| [Formulaire de rapport de panne](#panne) | `PANNE` | ZONE_TECH, PUMP_FOCAL, STORAGE_FOCAL, SSE, RESP_TECH, ADJOINT, DATA_OFFICER, CONTRACTOR |
| [Checklist – Maintenance préventive pompe](#mp_pompe) | `MP_POMPE` | PUMP_FOCAL, RESP_TECH, ADJOINT, DATA_OFFICER, CONTRACTOR |
| [Checklist – Maintenance préventive réservoir](#mp_reservoir) | `MP_RESERVOIR` | STORAGE_FOCAL, RESP_TECH, ADJOINT, DATA_OFFICER, CONTRACTOR |
| [Checklist – Maintenance préventive réseau](#mp_reseau) | `MP_RESEAU` | ZONE_TECH, RESP_TECH, ADJOINT, DATA_OFFICER, CONTRACTOR |

<a id="pompage"></a>

## Fiche journalière d'exploitation – Station de pompage (`POMPAGE`)

Source Excel : `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!1. Fiche journ_E&M_Pompage`.

### Informations générales — `general` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `station` | Nom de la station | asset | oui | actif : PUMP_STATION |  |
| `date` | Date | date | oui |  |  |
| `operator` | Opérateur | text | oui |  |  |
| `pump_specs` | Type de pompe et spécifications techniques | asset_specs |  | lecture seule |  |
| `energy_source` | Source d'énergie | enum |  | SNEL (réseau) / Groupe électrogène / Solaire / Mixte |  |

### Fonctionnement des pompes — `pumps` (tableau (lignes libres))

De 1 à 12 lignes.

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `time` | Heure | time |  |  |  |
| `pump` | Pompe N° | asset | oui | actif : PUMP |  |
| `start` | Heure démarrage | time | oui |  |  |
| `stop` | Heure arrêt | time | oui |  |  |
| `current_a` | Intensité (A) | number |  | 0 … 1000 |  |
| `pressure_bar` | Pression (bar) | number |  | 0 … 60 |  |
| `flow_m3h` | Débit (m³/h) | number |  | 0 … 400 |  |
| `volume_m3` | Volume pompé (m³) | number |  | 0 … 10000 | oui — Nécessaire au rendement du réseau. Si vide : débit × durée de fonctionnement. |
| `observations` | Observations | text |  |  |  |

### Contrôle technique — `technical` (liste de contrôle (lignes fixes))

Lignes : Roulement ; Vibrations ; Température moteur ; Fuite huile/eau ; Niveau carburant ; État tableau électrique ; État câblage

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `state` | État | enum |  | Bon / Mauvais |  |
| `observations` | Observations | text |  |  |  |

### Consommation énergétique — `energy` (liste de contrôle (lignes fixes))

Lignes : SNEL (kWh) ; Groupe électrogène (L)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `quantity` | Quantité consommée | number |  | 0 … 5000 |  |
| `start` | Heure démarrage | time |  |  |  |
| `stop` | Heure arrêt | time |  |  |  |
| `reading_time` | Heure (relevé) | time |  |  |  |
| `observation` | Observation | text |  |  |  |

### Qualité de l'eau — `quality` (liste de contrôle (lignes fixes))

Lignes : Qté chlore (g) ; Chlore résiduel (mg/L) ; Turbidité (NTU) ; Odeur/couleur anormale

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `value` | Valeur | number |  | 0 … 10000 |  |
| `acceptable` | Valeur acceptable | threshold |  | lecture seule |  |
| `conforme` | Conforme ? (oui/non) | enum |  | Oui / Non; calculé |  |
| `action` | Action corrective | text |  |  |  |

### Maintenance effectuée — `maintenance` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `maintenance_done` | Maintenance effectuée | textarea |  |  |  |

### Signature — `signature` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `operator_sign` | Opérateur | text |  |  |  |
| `manager_sign` | Responsable O&M | text |  |  |  |

<a id="stockage"></a>

## Fiche journalière d'exploitation – Stockage (`STOCKAGE`)

Source Excel : `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!2. Fiche journ_E&M_Stockage`.

### Informations générales — `general` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `reservoir` | Nom du réservoir | asset | oui | actif : RESERVOIR |  |
| `volume` | Volume | asset_capacity |  | lecture seule |  |
| `location` | Localisation | asset_location |  | lecture seule |  |
| `date` | Date | date | oui |  |  |
| `operator` | Nom de l'opérateur | text | oui |  |  |
| `service_start` | Heure de début de service | time |  |  |  |
| `service_end` | Heure de fin de service | time |  |  |  |

### Suivi opérationnel — `operations` (tableau (lignes libres))

De 0 à 24 lignes.

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `time` | Heure | time | oui |  |  |
| `level_pct` | Niveau du réservoir (%) | number |  | 0 … 100 |  |
| `level_m3` | Niveau du réservoir (m³) | number |  | 0 … 5000 |  |
| `flow_in_m3h` | Débit entrant (m³/h) | number |  | 0 … 500 |  |
| `flow_out_m3h` | Débit sortant (m³/h) | number |  | 0 … 500 |  |
| `pressure_bar` | Pression réseau (bar) | number |  | 0 … 60 |  |
| `observations` | Observations | text |  |  |  |

### Totaux journaliers — `daily` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `volume_in_m3` | Volume entrant journalier (m³) | number |  | 0 … 20000 | oui — Colonne de la feuille STOCKAGE (base KPI), absente de la fiche papier. |
| `volume_out_m3` | Volume sortant journalier (m³) | number |  | 0 … 20000 | oui — Colonne de la feuille STOCKAGE (base KPI), absente de la fiche papier. |
| `pressure_in_bar` | Pression entrée (bar) | number |  | 0 … 60 | oui — Colonne de la feuille STOCKAGE. |
| `pressure_out_bar` | Pression sortie (bar) | number |  | 0 … 60 | oui — Colonne de la feuille STOCKAGE. |

### Contrôle de sécurité et état physique — `safety` (liste de contrôle (lignes fixes))

Lignes : Présence de fuite ; État des vannes ; État du trop-plein ; État des échelles ; Présence d'intrusion ; État du couvercle ; Ventilation fonctionnelle

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `answer` | Oui / Non | enum |  | Oui / Non |  |
| `observations` | Observations | text |  |  |  |

### Qualité de l'eau — `quality` (liste de contrôle (lignes fixes))

Lignes : Qté chlore (g) ; Chlore résiduel (mg/L) ; Turbidité (NTU) ; Odeur/couleur anormale

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `value` | Valeur | number |  | 0 … 10000 |  |
| `acceptable` | Valeur acceptable | threshold |  | lecture seule |  |
| `conforme` | Conforme ? (oui/non) | enum |  | Oui / Non; calculé |  |
| `action` | Action corrective | text |  |  |  |

### Incidents ou anomalies observés — `incidents` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `incidents` | Incidents ou anomalies observés | textarea |  |  |  |

### Signature — `signature` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `operator_sign` | Opérateur | text |  |  |  |
| `supervisor_sign` | Superviseur | text |  |  |  |

<a id="reseau_bf"></a>

## Fiche journalière d'exploitation – Réseau et bornes fontaines (`RESEAU_BF`)

Source Excel : `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!3. Fiche journ_E&M_Rés&BF`.

> Le réseau est divisé en zones et chaque zone a son agent terrain, chargé d'identifier tout dysfonctionnement, fuite, etc.

### Informations générales — `general` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `zone` | Zone / Quartier | zone | oui |  |  |
| `date` | Date | date | oui |  |  |
| `agent` | Agent terrain | text | oui |  |  |
| `far_pressure_bar` | Pression à la BF la plus éloignée (bar) | number |  | 0 … 60 | oui — Colonne de la feuille RESEAU (base KPI). |

### Inspection du réseau — `network` (tableau (lignes libres))

De 0 à 30 lignes.

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `node` | Localisation (nœud du réseau) | node | oui |  |  |
| `reference` | Référence (repère) | text |  |  |  |
| `leak` | Fuite observée | enum |  | Oui / Non |  |
| `low_pressure` | Pression faible | enum |  | Oui / Non |  |
| `damaged` | Accessoires endommagés | text |  |  |  |
| `cause` | Cause probable du dommage | enum |  | Vandalisme et vol / Surpression / Tuyau mal enfoui / Connexion illégale / Mauvaise manipulation des accessoires par le technicien / Mauvaise qualité du tuyau … |  |
| `illegal` | Connexion illégale | enum |  | Oui / Non |  |
| `intervention` | Intervention réalisée | text |  |  |  |
| `observation` | Observation | text |  |  |  |

### Inspection des bornes fontaines — `kiosks` (tableau (lignes libres))

De 0 à 30 lignes.

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `kiosk` | N° BF | asset | oui | actif : KIOSK, PRIVATE_CONNECTION |  |
| `working` | Fonctionnelle ? (oui/non) | enum | oui | Oui / Non |  |
| `state` | État de la robinetterie / drainage / propreté | enum |  | Bon / Mauvais |  |
| `damaged` | Accessoires endommagés | text |  |  |  |
| `cause` | Cause probable du dommage | enum |  | Vandalisme et vol / Surpression / Tuyau mal enfoui / Connexion illégale / Mauvaise manipulation des accessoires par le technicien / Mauvaise qualité du tuyau … |  |
| `residual_chlorine` | Qualité – Chlore résiduel (mg/L) | number |  | 0 … 10 |  |
| `conforme` | Qualité conforme ? (oui/non) | enum |  | Oui / Non; calculé |  |
| `volume_sold_m3` | Volume vendu (m³) | number |  | 0 … 1000 | oui — Nécessaire pour l'eau facturée et l'eau non facturée (NRW). Colonne « Volume d'eau vendu » de la feuille RESEAU. |
| `action` | Action corrective | text |  |  |  |

### Plaintes communautaires reçues — `complaints` (tableau (lignes libres))

De 0 à 20 lignes.

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `nature` | Nature plainte | text | oui |  |  |
| `location` | Localisation | text |  |  |  |
| `action` | Action prise | text |  |  |  |

### Signature — `signature` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `agent_sign` | Agent terrain | text |  |  |  |
| `supervisor_sign` | Superviseur | text |  |  |  |

<a id="panne"></a>

## Formulaire de rapport de panne (`PANNE`)

Source Excel : `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!4. Fiche E&M_Rapp. Panne`.

> Toute panne doit être signalée immédiatement par un agent terrain et le rapport envoyé dans les 24 h après le signalement.

### Informations générales — `general` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `number` | Numéro incident | auto |  | lecture seule |  |
| `date` | Date | date | oui |  |  |
| `detected_time` | Heure détection | time | oui |  |  |
| `reported_by` | Rapporté par | text | oui |  |  |
| `zone` | Zone | zone |  |  |  |
| `node` | Localisation – Nœud | node |  |  |  |
| `location` | Localisation – Référence | text |  |  |  |
| `gps` | Position GPS | gps |  |  | oui — Position relevée par le téléphone. |

### Description de la panne — `description` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `incident_type` | Type de panne | enum | oui | Fuite / Rupture de conduite / Panne de pompe / Panne électrique / coupure / Vanne / accessoire défectueux / Borne fontaine endommagée … |  |
| `asset` | Infrastructure / actif concerné(e) | asset |  |  |  |
| `severity` | Gravité (Faible / Moyenne / Critique) | enum | oui | Faible / Moyenne / Critique |  |
| `service_interrupted` | Service interrompu ? (Oui / Non) | enum | oui | Oui / Non |  |
| `affected_zone` | Zone de la population affectée | text |  |  |  |
| `affected_population` | Population affectée (nombre de personnes) | integer |  | 0 … 500000 | oui — Permet de mesurer l'impact des pannes. |
| `downtime_cause` | Cause de l'arrêt du service | enum |  | Panne des pompes / Rupture des conduites / Coupure d'électricité / Maintenance programmée / Autre | oui — Répartition de la disponibilité (O&M KPI lignes 5-8). |
| `downtime_hours` | Durée d'arrêt du service (h) | number |  | 0 … 744 | oui — Disponibilité du réseau. Si vide : calculée de l'heure de détection à la fin d'intervention. |
| `photos` | Photos | photos |  |  | oui — Photos compressées sur le téléphone (max 3). |

### Analyse technique — `analysis` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `probable_cause` | Cause probable | enum | oui | Vandalisme et vol / Surpression / Tuyau mal enfoui / Connexion illégale / Mauvaise manipulation des accessoires par le technicien / Mauvaise qualité du tuyau … |  |
| `root_cause` | Cause racine identifiée | textarea |  |  |  |
| `damage` | Dommages observés | textarea |  |  |  |
| `risks` | Risques sécurité/santé | textarea |  |  |  |
| `nrw_cause` | Cause de perte d'eau (si perte) | enum |  | Fuites physiques sur les conduites / Ruptures de conduites / Débordements de réservoirs (trop-plein) / Purges du réseau / Vidanges / Eau utilisée pour le nettoyage des réservoirs … | oui — Analyse des causes de l'eau non facturée (O&M KPI lignes 36-48). |
| `estimated_loss_m3` | Volume d'eau perdu estimé (m³) | number |  | 0 … 100000 | oui — Eau non facturée. |

### Intervention réalisée — `intervention` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `maintenance_type` | Type : Maintenance Urgente (MU) ou Corrective (MC) | enum | oui | Maintenance Urgente (MU) / Maintenance Corrective (MC) |  |
| `start` | Heure début intervention | datetime |  |  |  |
| `end` | Heure fin intervention | datetime |  |  |  |
| `team` | Équipe / M.O mobilisée | textarea |  |  |  |
| `materials` | Matériels utilisés | textarea |  |  |  |
| `cost_usd` | Coût estimatif (USD) | number |  | 0 … 1000000 |  |
| `logistics` | Appui logistique | textarea |  |  |  |

### Pièces remplacées — `parts` (tableau (lignes libres))

De 0 à 20 lignes.

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `item` | Pièce (article du stock) | stock_item | oui |  |  |
| `quantity` | Quantité | number | oui | 0 … 100000 |  |

### Vérification après réparation — `verification` (liste de contrôle (lignes fixes))

Lignes : Pression rétablie ; Absence de fuite ; Rinçage de conduite ; Qualité eau vérifiée ; Service restauré

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `answer` | Conforme ? | enum |  | Oui / Non |  |
| `observation` | Observation | text |  |  |  |

### Leçons apprises / actions préventives — `lessons` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `worked` | Qu'est-ce qui a marché | textarea |  |  |  |
| `not_worked` | Qu'est-ce qui n'a pas marché | textarea |  |  |  |
| `constraint` | Contrainte | textarea |  |  |  |
| `preventive` | Actions préventives | textarea |  |  |  |
| `recommendation` | Recommandation | textarea |  |  |  |

### Validation — `validation` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `technician_sign` | Technicien | text |  |  |  |
| `manager_sign` | Responsable O&M | text |  |  |  |

<a id="mp_pompe"></a>

## Checklist – Maintenance préventive pompe (`MP_POMPE`)

Source Excel : `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!5. Checklist_Maint Prev_Pomp`.

### Informations — `general` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `station` | Station | asset | oui | actif : PUMP_STATION |  |
| `pump` | Pompe N° | asset | oui | actif : PUMP |  |
| `date` | Date inspection | date | oui |  |  |
| `technician` | Technicien | text | oui |  |  |

### Contrôle mécanique — `mechanical` (liste de contrôle (lignes fixes))

Lignes : Lubrification correcte ; Vibrations anormales ; Bruit anormal ; Alignement pompe-moteur ; État des roulements

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `state` | Bon / Mauvais | enum |  | Bon / Mauvais |  |
| `observations` | Observations / besoin en maintenance / échéance | text |  |  |  |

### Contrôle électrique — `electrical` (liste de contrôle (lignes fixes))

Lignes : Intensité normale ; État câblage ; Protection électrique fonctionnelle ; Mise à terre correcte

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `state` | Bon / Mauvais | enum |  | Bon / Mauvais |  |
| `observations` | Observation | text |  |  |  |

### Contrôle performance — `performance` (liste de contrôle (lignes fixes))

Lignes : Débit (m³/h) ; Pression (bar) ; Temps de fonctionnement (h) ; Consommation énergie (kWh)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `value` | Valeur | number |  | 0 … 100000 |  |
| `state` | Bon / Mauvais | enum |  | Bon / Mauvais |  |
| `observations` | Observation | text |  |  |  |

### Maintenance — `maintenance` (tableau (lignes libres))

De 0 à 10 lignes.

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `part` | Description de la partie concernée | text | oui |  |  |
| `materials` | Matériels / équipements en besoin | text |  |  |  |
| `labour` | MO en besoin | text |  |  |  |
| `cost_usd` | Coût estimatif (USD) | number |  | 0 … 1000000 |  |
| `due` | Échéance / date proposée de maintenance | date |  |  |  |

### Validation — `validation` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `technician_sign` | Technicien | text |  |  |  |
| `manager_sign` | Responsable O&M | text |  |  |  |

<a id="mp_reservoir"></a>

## Checklist – Maintenance préventive réservoir (`MP_RESERVOIR`)

Source Excel : `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!6. Checklist_Maint Prev_ Reserv`.

### Informations — `general` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `reservoir` | Réservoir | asset | oui | actif : RESERVOIR |  |
| `volume` | Volume | asset_capacity |  | lecture seule |  |
| `date` | Date inspection | date | oui |  |  |
| `technician` | Technicien | text | oui |  |  |

### Contrôles structurels — `structural` (liste de contrôle (lignes fixes))

Lignes : Présence fissures ; Présence fuite ; État clôture ; État ventilation ; Drainage autour du site ; Éclairage ; Autres à signaler

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `answer` | Conforme ? (oui/non) | enum |  | Oui / Non |  |
| `observations` | Observations | text |  |  |  |

### Contrôles sanitaires — `sanitary` (liste de contrôle (lignes fixes))

Lignes : Réservoir propre ; Absence contamination ; Chloration correcte ; Trop-plein fonctionnel

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `answer` | Conforme ? Oui/Non | enum |  | Oui / Non |  |
| `observations` | Observations | text |  |  |  |

### Maintenance — `maintenance` (tableau (lignes libres))

De 0 à 10 lignes.

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `part` | Description de la partie concernée | text | oui |  |  |
| `materials` | Matériels / équipements / MO en besoin | text |  |  |  |
| `cost_usd` | Coût estimatif (USD) | number |  | 0 … 1000000 |  |
| `due` | Échéance / date | date |  |  |  |

### Validation — `validation` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `technician_sign` | Technicien | text |  |  |  |
| `manager_sign` | Responsable O&M | text |  |  |  |

<a id="mp_reseau"></a>

## Checklist – Maintenance préventive réseau (`MP_RESEAU`)

Source Excel : `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!7. Checklist_Maint Prev_ Res`.

### Informations générales — `general` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `zone` | Zone / Quartier | zone | oui |  |  |
| `date` | Date | date | oui |  |  |
| `technician` | Technicien | text | oui |  |  |

### Inspection réseau — `network` (liste de contrôle (lignes fixes))

Lignes : Fuites détectées ; Tuyauterie correctement enfouie ; Pression correcte ; Chambre de vannes disponible ; Vannes opérationnelles ; Ventouses fonctionnelles ; Supports / blocs d'ancrage stables

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `answer` | Oui / Non | enum |  | Oui / Non |  |
| `location` | Localisation (nœuds) | text |  |  |  |
| `observation` | Observation | text |  |  |  |

### Contrôle bornes fontaines — `kiosks` (liste de contrôle (lignes fixes))

Lignes : Robinets fonctionnels ; Drainage correct ; Zone propre ; Absence stagnation

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `answer` | Oui / Non | enum |  | Oui / Non |  |
| `location` | Localisation (N° BF) | text |  |  |  |
| `observation` | Observation | text |  |  |  |

### Maintenance — `maintenance` (tableau (lignes libres))

De 0 à 10 lignes.

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `part` | Description de la partie concernée | text | oui |  |  |
| `materials` | Matériels / équipements / MO en besoin | text |  |  |  |
| `cost_usd` | Coût estimatif (USD) | number |  | 0 … 1000000 |  |
| `due` | Échéance / date | date |  |  |  |
| `observation` | Observation | text |  |  |  |

### Validation — `validation` (champs)

| Clé | Libellé | Type | Obligatoire | Contrôle | Ajouté |
|---|---|---|---|---|---|
| `technician_sign` | Technicien | text |  |  |  |
| `manager_sign` | Responsable O&M | text |  |  |  |

## Listes de valeurs

- **`bon_mauvais`** : `BON` Bon ; `MAUVAIS` Mauvais
- **`oui_non`** : `OUI` Oui ; `NON` Non
- **`gravite`** : `LOW` Faible ; `MEDIUM` Moyenne ; `CRITICAL` Critique
- **`source_energie`** : `SNEL` SNEL (réseau) ; `GENSET` Groupe électrogène ; `SOLAR` Solaire ; `MIXED` Mixte
- **`type_intervention`** : `URGENT` Maintenance Urgente (MU) ; `CORRECTIVE` Maintenance Corrective (MC)
- **`type_panne`** : `FUITE` Fuite ; `RUPTURE` Rupture de conduite ; `PANNE_POMPE` Panne de pompe ; `PANNE_ELEC` Panne électrique / coupure ; `VANNE` Vanne / accessoire défectueux ; `BF` Borne fontaine endommagée ; `QUALITE` Qualité de l'eau ; `AUTRE` Autre
- **`cause_panne`** : `VANDALISM` Vandalisme et vol ; `OVERPRESSURE` Surpression ; `SHALLOW_PIPE` Tuyau mal enfoui ; `ILLEGAL_CONNECTION` Connexion illégale ; `MISHANDLING` Mauvaise manipulation des accessoires par le technicien ; `POOR_PIPE_QUALITY` Mauvaise qualité du tuyau ; `POOR_BACKFILL` Mauvais remblai ; `GROUND_MOVEMENT` Mouvement de terrain ; `POOR_INSTALLATION` Mauvaise installation ; `WATER_HAMMER` Coup de bélier ; `FAULTY_CONNECTION` Connexion défectueuse ; `OTHER` Autre / non déterminée
- **`cause_arret`** : `PUMP_FAILURE` Panne des pompes ; `PIPE_BURST` Rupture des conduites ; `POWER_CUT` Coupure d'électricité ; `PLANNED_MAINTENANCE` Maintenance programmée ; `OTHER` Autre
- **`cause_perte_eau`** : `PIPE_LEAK` Fuites physiques sur les conduites ; `PIPE_BURST` Ruptures de conduites ; `RESERVOIR_OVERFLOW` Débordements de réservoirs (trop-plein) ; `NETWORK_FLUSH` Purges du réseau ; `DRAINING` Vidanges ; `RESERVOIR_CLEANING` Eau utilisée pour le nettoyage des réservoirs ; `FIREFIGHTING` Eau utilisée pour la lutte contre les incendies ; `ILLEGAL_BRANCH` Branchements illégaux ; `FAULTY_METER` Compteurs défectueux ; `MISCALIBRATED_METER` Compteurs mal calibrés ; `ILLEGAL_CONNECTION` Connexions illégales ; `READING_ERROR` Erreurs de relevé ; `UNBILLED_CONSUMPTION` Volumes consommés mais non facturés

## Corrections de libellés par rapport à Excel

- Fomulaire → Formulaire — `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!4. Fiche E&M_Rapp. Panne!B2`
- Recommendation → Recommandation — `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!4. Fiche E&M_Rapp. Panne!B43`
- Proprété → Propreté — `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!3. Fiche journ_E&M_Rés&BF!D22`
- intentifié → identifié ; disfonctionnement → dysfonctionnement — `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!3. Fiche journ_E&M_Rés&BF!B3`
- specifié → spécifié (parenthèse non fermée) — `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!3. Fiche journ_E&M_Rés&BF!B9`
- enfuie → enfouie — `2. ymejibu_E&M_Activités d'Exploitation_Goma Ouest_2026.xlsx!7. Checklist_Maint Prev_ Res!B10`
- Etat → État — `plusieurs feuilles`
