# Stratégie de test

## Objectifs

1. Chaque indicateur est **juste** : formules vérifiées à la main.
2. Aucun défaut de l'ancien fichier Excel ne réapparaît : **un test par défaut**.
3. Le mode **hors ligne** ne perd ni ne duplique aucune fiche.
4. Les **droits** sont respectés : chaque refus attendu est testé.

## Pyramide

| Niveau | Où | Outil | Durée | Contenu |
|---|---|---|---|---|
| Unitaire | `backend/tests/test_formulas.py` | pytest | < 1 s | Formules pures (disponibilité, rendement, NRW, énergie, taux) avec valeurs calculées à la main en commentaire |
| Intégration | `backend/tests/test_kpi_service.py` | pytest + PostgreSQL | ~2 s | Jeu de données de mars entièrement connu → chaque KPI ; historique ; mois futurs ; budget seul |
| Intégration | `backend/tests/test_sync.py` | pytest + client API | ~15 s | Création, mise à jour, conflit, renvoi, validation, rôles, dérivation (relevés, panne, stock, dépense, qualité, préventif) |
| Non-régression | `backend/tests/test_review_regressions.py` | pytest | ~10 s | Les 7 défauts trouvés en revue avant fusion + corrections suivantes |
| Données réelles | `backend/tests/test_excel_defects.py`, `test_export.py` | pytest + les 5 classeurs | ~40 s | Import des vrais classeurs, un test par défaut Excel (codes K01…), idempotence, deuxième site, export au format « O&M KPI » |
| Bout en bout | `frontend/e2e/offline.spec.ts` | Playwright (Chromium, Pixel 5) | ~20 s | Fiche pompage + panne avec photo hors ligne → rechargement → reconnexion → envoi automatique → KPI d'août sur le tableau de bord |

Les tests sur données réelles sont **ignorés** (`skipped`) si les classeurs ne sont pas présents : les placer à la racine du dépôt ou définir `WORKBOOK_DIR`.

## Lancer les tests

```bash
# Backend : PostgreSQL local (utilisateur/mot de passe « ymejibu », droit CREATEDB)
cd backend
pip install -r requirements-dev.txt
python -m pytest                 # --create-db après un changement de migrations
WORKBOOK_DIR=/chemin/classeurs python -m pytest tests/test_excel_defects.py

# Documentation générée à jour
python manage.py gen_docs --check

# Frontend
cd ../frontend
npm run typecheck
npx playwright test              # crée la base ymejibu_e2e au préalable : createdb -O ymejibu ymejibu_e2e
```

## Règles pour les contributions

- Toute correction de bogue commence par un **test qui échoue**.
- Toute nouvelle formule de KPI a un test avec la valeur **calculée à la main** en commentaire.
- Toute nouvelle vue d'API a un test de **refus** pour au moins un rôle non autorisé.
- Toute modification de la synchronisation est vérifiée par le test de bout en bout.
- Les tests n'utilisent jamais les classeurs pour écrire : l'import est en lecture seule.

## Vérifications manuelles avant une version

- `docker compose up --build` sur une machine propre ; `/api/health/` ; connexion ; export XLSX ouvert dans Excel.
- Un vrai téléphone Android : installation, mode avion, fiche avec photo et GPS, retour du réseau.
