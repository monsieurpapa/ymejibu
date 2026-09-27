# Migration des classeurs Excel

Comment les 5 classeurs sont importés, et comment relancer l'import.

## Principe

- Les classeurs sont ouverts **en lecture seule** (formules et valeurs calculées) ; ils ne sont jamais enregistrés.
- L'import est **idempotent** : le relancer ne crée pas de doublon (clés naturelles : codes d'actifs, de nœuds, de tronçons ; `source_ref` pour le reste).
- Chaque ligne importée garde `source_ref` (`fichier!feuille!cellule`) et `flags` (codes des anomalies).
- 63 **contrôles qualité** exécutables (`backend/importer/checks.py`) relisent les classeurs à chaque import et produisent le rapport [../data-quality-report.md](../data-quality-report.md) avec la preuve lue.

## Ce qui est importé

| Classeur / feuille | Devient | Traitement particulier |
|---|---|---|
| 1 — Prod&Stock | `Asset` (stations, pompes, réservoirs, unités de chloration et leurs équipements) | Identifiants stables générés ; « 2 Groupe motopompe » = 2 actifs ; capacité découpée en valeur + unité |
| 1 — Regul&tuy | `Node`, `PipeSegment` | Nœuds en texte selon le format affiché (1.10 ≠ 1.1) ; un tronçon par DN ; tronçons sans longueur ignorés |
| 1 — OrgRegu | `Fitting` (organes par nœud) | État en texte libre → nœud « Mauvais » + note |
| 1 — BF&Conn | `Asset` `KIOSK` / `PRIVATE_CONNECTION` | BF1 → BF01 ; coordonnées identiques signalées |
| 2 — Activités d'exploitation | `shared/forms.fr.json` (formulaires) | Pas de données : ce sont des modèles de fiches |
| 3 — Stock | `StockItem` (catalogue) | **Quantités non importées** (valeurs de test, contrôle S01) : faire un inventaire initial |
| 4 — Personnel | `Person`, `StaffingNeed` | Aucun compte de connexion créé |
| 5 — O&M KPI | `MonthlyAggregate`, `MonthlyBudget`, `Tariff` | Mois avant juillet = historique validé (à confirmer) ; juillet → mois en cours = provisoire ; mois futurs ignorés ; formules jamais importées |
| 5 — POMPES, STOCKAGE | `DailyReading` (9 juillet) | Ligne « CAPRARI » à 90 m³/h rattachée à la pompe SHIMGE (K18) |
| 5 — RESEAU | — | Non importée : données de test (K19) |
| 5 — Besoins et budget | `BudgetLine` (juillet) | Lignes non chiffrées signalées |
| 5 — Plan d'Action | `ActionPlanTask` | Tâches sans description ignorées ; `#REF!` signalé |

## Relancer l'import

```bash
docker compose exec backend python manage.py import_excel               # rapport → docs/data-quality-report.md
docker compose exec backend python manage.py import_excel --history-status provisional   # historique non fiable
```

Un relevé déjà saisi dans l'application pour le même jour et le même actif n'est jamais écrasé par l'import.

> Après la mise en service, la base devient la référence : ne plus modifier les classeurs pour y saisir des données.

## Lire le rapport qualité

- **Section 2** : chaque anomalie avec sa gravité, la preuve lue et le traitement appliqué. Colonne « KPI » = l'anomalie faussait un indicateur ; chacune a un test de non-régression (`backend/tests/test_excel_defects.py`).
- **Section 3.1** : correspondance libellé Excel → nouvel identifiant d'actif.
- **Sections 3.2 et 3.3** : lignes ignorées et lignes signalées.
- **Section 4** : décisions à prendre par l'équipe.
