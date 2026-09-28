# Référence des indicateurs (KPI)

Définition de chaque indicateur calculé par `backend/kpi/service.py` (quantités de base) et `backend/kpi/formulas.py` (formules). Les clés sont celles de l'API `GET /api/kpi/` (`months[].values` et `annual`) et de l'export.

## Règles générales

1. **Aucune référence de cellule** : tout est recalculé à partir des enregistrements.
2. **Pas de donnée = vide** (`null`), jamais 0 ni 100 %.
3. **Mois futurs** : toutes les valeurs sont vides, sauf le budget prévu (c'est un plan).
4. **Historique Excel** : pour un mois, une quantité de base importée avec le statut `ACTUAL` remplace celle des fiches ; les ratios sont toujours recalculés. `PROVISIONAL` = affiché pour comparaison uniquement ([ADR 0003](../adr/0003-kpi-history.md)).
5. **Annuel** = somme des quantités de base des mois disposant de données ; **ratio des sommes**, jamais moyenne des ratios.
6. **Un mois a des données** s'il a au moins un enregistrement d'exploitation (relevé, panne, ordre de travail, test qualité) ou un historique `ACTUAL` ; un budget seul ne suffit pas.

## Disponibilité du réseau

| Clé | Définition | Source |
|---|---|---|
| `period_hours` | Jours du mois × 24 | calendrier |
| `downtime_pump` | Heures d'arrêt, cause « Panne des pompes » | `Incident.downtime_hours` si `service_interrupted` |
| `downtime_pipe` | Heures d'arrêt, cause « Rupture des conduites » | idem |
| `downtime_power` | Heures d'arrêt, cause « Coupure d'électricité » | idem |
| `downtime_planned` | Heures d'arrêt, « Maintenance programmée » | idem + `WorkOrder.downtime_hours` des ordres réalisés |
| `downtime_other` | Autres causes | idem |
| `downtime_total` | Somme des 5 lignes ci-dessus | |
| `operating_hours` | `period_hours − downtime_total` | |
| `availability` | `(period_hours − downtime_total) / period_hours`, borné à [0 ; 1] | |

Les heures d'arrêt de plusieurs pannes simultanées s'additionnent (convention de l'ancien fichier).

## Pannes

| Clé | Définition |
|---|---|
| `incidents_reported` | Nombre de pannes détectées dans le mois |
| `incidents_closed` | Parmi elles, pannes clôturées (« Service restauré = Oui ») |
| `repair_rate` | `incidents_closed / incidents_reported` — **seulement pour les mois issus du registre des pannes** (l'historique Excel n'a pas de nombre de réparations fiable) |
| `rca_<CAUSE>` | Nombre de pannes par cause probable (11 causes : `VANDALISM`, `OVERPRESSURE`, `SHALLOW_PIPE`, `ILLEGAL_CONNECTION`, `MISHANDLING`, `POOR_PIPE_QUALITY`, `POOR_BACKFILL`, `GROUND_MOVEMENT`, `POOR_INSTALLATION`, `WATER_HAMMER`, `FAULTY_CONNECTION`, + `OTHER`) |
| `rca_total` | Somme des pannes par cause |
| `rca_share_<CAUSE>` (annuel) | `rca_<CAUSE> / rca_total` |

## Rendement et eau non facturée

| Clé | Définition | Source |
|---|---|---|
| `volume_introduced` | Eau introduite (m³) = somme des volumes pompés | `DailyReading.volume_m3` des actifs `PUMP` (débit × durée si le volume n'est pas saisi) |
| `volume_billed` | Eau facturée (m³) = somme des volumes vendus | `DailyReading.volume_m3` des `KIOSK` et `PRIVATE_CONNECTION` |
| `efficiency` | `volume_billed / volume_introduced` | vide si l'un des deux est inconnu |
| `nrw_m3` | `volume_introduced − volume_billed` | vide si le volume vendu est inconnu |
| `nrw_rate` | `nrw_m3 / volume_introduced` | |
| `nrw_<CAUSE>` | Nombre d'événements de perte d'eau par cause (13 causes) | `Incident.nrw_cause` |
| `nrw_events` | Somme des événements de perte | |

## Maintenance préventive

| Clé | Définition |
|---|---|
| `pm_planned_<CAT>` | Ordres de travail préventifs planifiés dans le mois (date prévue), catégorie `CAPTAGE`, `POMPAGE`, `RESERVOIR`, `RESEAU`, `BF` ; annulés exclus |
| `pm_done_<CAT>` | Parmi eux, ordres réalisés |
| `pm_planned_total`, `pm_done_total` | Sommes |
| `pm_rate` | `pm_done_total / pm_planned_total` ; vide si les réalisations ne sont pas connues (historique Excel) |

Une checklist préventive sans ordre planifié crée un ordre « réalisé » compté à la fois prévu et réalisé. Générer les ordres du mois depuis le plan annuel : `python manage.py plan_work_orders --month AAAA-MM`.

## Énergie

| Clé | Définition |
|---|---|
| `kwh`, `fuel_l` | Somme des kWh et litres des relevés du mois (pompes et station) |
| `price_kwh`, `price_fuel` | Tarif valable au 1er du mois (`Tariff`) |
| `cost_electricity` | `kwh × price_kwh` |
| `cost_fuel` | `fuel_l × price_fuel` |
| `energy_cost` | `cost_electricity + cost_fuel` |
| `kwh_per_m3` | `kwh / volume_introduced` |
| `fuel_l_per_m3` | `fuel_l / volume_introduced` |
| `electricity_cost_per_m3`, `fuel_cost_per_m3`, `energy_cost_per_m3` | coût / `volume_introduced` |

## Coûts d'exploitation et de maintenance

| Clé | Définition | Source |
|---|---|---|
| `budget` | Budget prévu du mois | `MonthlyBudget`, sinon somme des lignes `BudgetLine` chiffrées |
| `cost_urgent`, `cost_corrective`, `cost_preventive`, `cost_support`, `cost_routine` | Dépenses réelles par type | `Expense` (alimenté par le coût des pannes, ou saisi au bureau) |
| `actual_total` | Urgente + corrective + préventive + support | |
| `budget_variance` | `actual_total − budget` (négatif = sous le budget) | |
| `share_urgent` … `share_support` | Part de chaque type dans `actual_total` | |

## Qualité de l'eau

| Clé | Définition |
|---|---|
| `quality_field_total`, `quality_field_compliant` | Mesures de terrain (chlore résiduel, turbidité, odeur/couleur) et mesures conformes |
| `quality_lab_total`, `quality_lab_compliant` | Tests de laboratoire |
| `quality_rate` | Mesures conformes / mesures (terrain + laboratoire) |

La conformité est calculée avec le seuil le plus précis (`QualityThreshold` : actif > type d'actif > site). Valeurs par défaut, **à confirmer** : chlore résiduel 0,2–0,5 mg/L aux bornes fontaines, 0,2–1,0 mg/L ailleurs ; turbidité ≤ 5 NTU.

## Couverture

`months[].coverage.pump_reading_days` : nombre de jours du mois ayant au moins un relevé de pompe. Le tableau de bord l'affiche pour le mois en cours, afin qu'un mois partiel ne soit pas lu comme un mois complet.

## Cibles du tableau de bord

Valeurs par défaut (à valider), définies dans `backend/kpi/catalog.py` : ce catalogue (titres, formats, cibles, répartitions) est servi par `GET /api/kpi/` (`catalog`) et utilisé à la fois par le tableau de bord et par le rapport PDF (`GET /api/kpi/report.pdf?year=AAAA[&month=M]`, `backend/kpi/report_pdf.py`), qui affichent donc toujours les mêmes libellés et cibles :

| Indicateur | Cible |
|---|---|
| Disponibilité | ≥ 95 % |
| Rendement | ≥ 80 % |
| Taux de réparation | ≥ 90 % |
| Maintenance préventive | ≥ 90 % |
| Conformité qualité | ≥ 95 % |
| Écart budgétaire | ≤ 0 |

## Correspondance avec la feuille Excel « O&M KPI »

L'export XLSX (`/api/kpi/export.xlsx`) reprend exactement les lignes 4 à 88 de la feuille ; la correspondance ligne → clé est dans `backend/kpi/export.py` (`LAYOUT`). Différences volontaires avec l'ancien fichier :

| Ligne | Ancien calcul | Nouveau calcul |
|---|---|---|
| 10 (mars) | `744 − arrêt de février` | `744 − arrêt de mars` |
| 11 | janvier–juin figé | mois disposant de données |
| 15–16 | 50 saisi en dur | pannes clôturées / signalées (registre) |
| 33 | janvier seulement | chaque mois |
| 56–57 | prévues − 5 | ordres réalisés |
| 62, 66 | `/175+30` | ÷ volume pompé |
| 68 | `/(volume+175+30)` | ÷ volume pompé |
| 75 | sans la ligne 74 | inclut les activités de support |
| 81–88 | vide | calculé |
