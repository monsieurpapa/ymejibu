# Rôles et droits d'accès

Les droits sont **vérifiés côté serveur** (`backend/core/permissions.py`). L'interface masque ce qui n'est pas autorisé, mais ce n'est pas elle qui protège les données.

## Principes

- Un compte de connexion (`User`) est relié à une fiche **Personne** (`Person`) qui porte le **rôle**, le **site** et éventuellement la **zone**. Un compte sans fiche Personne ne peut pas se connecter (sauf super-utilisateur).
- Toutes les données sont **limitées au site** de la personne. Un super-utilisateur choisit le site avec `?site=CODE`.
- Chaque vue déclare `read_roles` et `write_roles`. Par défaut : lecture pour tous les rôles, écriture pour les responsables.
- Chaque formulaire déclare les rôles qui peuvent le remplir (`roles` dans `shared/forms.fr.json`).
- Un agent ne modifie que **ses propres fiches** ; une fiche **validée** n'est plus modifiable que par un responsable.

## Groupes de rôles (code)

| Groupe | Rôles |
|---|---|
| `MANAGERS` | `RESP_TECH`, `ADJOINT`, `DATA_OFFICER` |
| `FIELD_ROLES` (envoi de fiches) | `ZONE_TECH`, `PUMP_FOCAL`, `STORAGE_FOCAL`, `SSE`, `CONTRACTOR` + `MANAGERS` |
| `STOCK_ROLES` (mouvements de stock) | `RESP_TECH`, `ADJOINT`, `DATA_OFFICER` |
| `DASHBOARD_ROLES` (KPI, coûts, pannes, relevés, stock, budget, plan) | `MANAGERS` + `FUNDER` + `SSE` |
| `STAFF_ROLES` (lecture des fiches) | tous sauf `FUNDER` |

## Matrice

| Ressource | Resp. technique / adjoint / données | SSE | Technicien de zone | Points focaux | Prestataire | Bailleur |
|---|---|---|---|---|---|---|
| Connexion, profil, référentiel hors ligne (`/api/reference/`) | L | L | L | L | L | L |
| Envoi de fiches (`/api/sync/push/`) | E | E (panne) | E (réseau, panne, préventif réseau) | E (leurs fiches) | E (panne, préventifs) | — |
| Fiches (`/api/submissions/`) | L + valider/rejeter | L (les siennes) | L (les siennes) | L (les siennes) | L (les siennes) | — |
| KPI, exports, carte, compteurs | L | L | — | — | — | L |
| Pannes, relevés, ordres de travail, tests qualité, dépenses | L/E | L | — | — | — | L |
| Stock (articles, mouvements, alertes) | L/E | L | — | — | — | L |
| Budget, tarifs, plan | L/E | L | — | — | — | L |
| Personnel, besoins en personnel | L/E | — | — | — | — | — |
| Actifs, nœuds, tronçons, zones, seuils | L/E | L | L | L | L | L |
| Gestion des utilisateurs (onglet **Utilisateurs**, `/api/users/`) | super administrateur seulement | | | | | |
| Administration Django (`/admin/`) | super administrateur seulement | | | | | |

L = lecture, E = écriture, — = refusé (HTTP 403).

## Formulaires par rôle

| Formulaire | Rôles |
|---|---|
| Pompage (`POMPAGE`) | `PUMP_FOCAL`, managers |
| Stockage (`STOCKAGE`) | `STORAGE_FOCAL`, managers |
| Réseau et BF (`RESEAU_BF`) | `ZONE_TECH`, managers |
| Rapport de panne (`PANNE`) | `ZONE_TECH`, `PUMP_FOCAL`, `STORAGE_FOCAL`, `SSE`, `CONTRACTOR`, managers |
| Préventif pompe (`MP_POMPE`) | `PUMP_FOCAL`, `CONTRACTOR`, managers |
| Préventif réservoir (`MP_RESERVOIR`) | `STORAGE_FOCAL`, `CONTRACTOR`, managers |
| Préventif réseau (`MP_RESEAU`) | `ZONE_TECH`, `CONTRACTOR`, managers |

Liste à jour générée : [formulaires.md](formulaires.md).

## Tests

Les droits sont couverts par `backend/tests/test_sync.py::test_roles` et `backend/tests/test_review_regressions.py::test_6_*`. Toute nouvelle vue doit déclarer ses `read_roles` et avoir un test de refus.
