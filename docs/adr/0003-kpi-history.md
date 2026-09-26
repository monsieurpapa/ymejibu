# ADR 0003 — Calcul des KPI et historique Excel

**Statut :** accepté · **Date :** 2026-09-27

## Décisions

1. **Aucune référence de cellule.** Les KPI sont calculés à partir des enregistrements, agrégés par date en base (`backend/kpi/service.py`). Les formules sont des fonctions pures testées (`backend/kpi/formulas.py`).
2. **Pas de donnée ≠ zéro.** Une valeur inconnue reste vide. Exemple : sans volume vendu, l'eau non facturée n'est pas affichée (l'ancien fichier affichait 100 % de pertes).
3. **Taux annuels = ratio des sommes**, jamais une moyenne de ratios.
4. **Historique mensuel** (`MonthlyAggregate`) importé de la feuille `O&M KPI` :
   - mois antérieurs au premier relevé journalier (juillet 2026) → `ACTUAL` : ils remplacent les quantités de base des fiches pour ce mois (à confirmer par l'équipe) ;
   - de juillet au mois en cours → `PROVISIONAL` : affichés pour comparaison, jamais utilisés (ils ne concordent pas avec les relevés journaliers) ;
   - mois futurs → non importés.
   Seules les **quantités de base** sont importées (heures d'arrêt, volumes, comptages, kWh, litres, coûts). Les valeurs issues de formules fausses (« réalisées = prévues − 5 », « 50 » pannes réparées, `/175+30`) ne le sont pas.
5. **Mois « avec données »** : un mois n'a de disponibilité que s'il a des enregistrements d'exploitation (relevés, pannes, ordres de travail, tests) ; un budget seul ne suffit pas.
6. **Cibles** (disponibilité 95 %, rendement 80 %, réparation 90 %, préventif 90 %, qualité 95 %) : valeurs par défaut dans `frontend/src/dashboard/KpiView.tsx`, à valider par le Responsable technique.
7. **Export** au format exact de la feuille `O&M KPI` (mêmes lignes, mêmes libellés, mois en C:N, année en O) pour les rapports aux bailleurs, plus une feuille « Lisez-moi » (sources et couverture par mois).
