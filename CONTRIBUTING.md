# Contribuer

Merci de contribuer à la plateforme E&M Yme Jibu. Ce document décrit comment proposer un changement.

## Avant de commencer

- Lire le [README](README.md), l'[architecture](docs/architecture.md) et les [ADR](docs/adr/README.md).
- Un changement de comportement important (sécurité, synchronisation, calcul d'un KPI, modèle de données) commence par une **ADR** ou une discussion dans une *issue*.

## Environnement

```bash
# Backend (Python 3.11, PostgreSQL 16 local : utilisateur/mot de passe « ymejibu », droit CREATEDB)
cd backend && pip install -r requirements-dev.txt && python manage.py migrate
# Frontend (Node 22)
cd frontend && npm install
```

Détails : [README](README.md#développement-sans-docker), [docs/reference/commandes.md](docs/reference/commandes.md).

## Branches et commits

- `main` est toujours déployable. Travailler sur une branche : `feat/…`, `fix/…`, `docs/…`, `chore/…`.
- Messages de commit au format [Conventional Commits](https://www.conventionalcommits.org/fr/) : `feat(sync): …`, `fix(kpi): …`, `docs: …`.
- Un commit = un changement cohérent ; pas de fichiers générés oubliés (voir ci-dessous).
- **Ne jamais commiter** les classeurs Excel, un fichier `.env`, des sauvegardes ou des photos.

## Règles de code

| Domaine | Règle |
|---|---|
| Langue | Code, noms, commentaires techniques en anglais ; libellés, messages et documentation en français |
| Python | PEP 8, lignes ≤ 130 caractères, imports triés avec `isort` (configuration dans `backend/pyproject.toml`, vérifié en CI) |
| TypeScript | `strict` ; pas de `any` nouveau sans raison ; `npm run typecheck` sans erreur |
| KPI | Formule pure dans `kpi/formulas.py`, jamais de 0 à la place d'une donnée absente, test calculé à la main |
| API | Toute vue déclare `read_roles` / `write_roles` et a un test de refus ; documenter avec `@extend_schema` si ce n'est pas un `ModelViewSet` |
| Formulaires | Modifier `scripts/build_forms.py`, jamais `shared/forms.fr.json` à la main ; ne jamais renommer une clé ([guide](docs/guides/modifier-un-formulaire.md)) |
| Modèles | Toute modification → migration commitée + `python manage.py gen_docs` |

## Fichiers générés

Régénérer et commiter avec le changement qui les modifie :

| Fichier | Commande |
|---|---|
| `shared/forms.fr.json` | `python3 scripts/build_forms.py` |
| `docs/reference/dictionnaire-donnees.md`, `formulaires.md`, `openapi.yaml` | `cd backend && python manage.py gen_docs` |
| `docs/data-quality-report.md` | `python manage.py import_excel` (avec les classeurs) |

La CI échoue si la documentation générée n'est pas à jour.

## Tests

Voir la [stratégie de test](docs/tests.md). Avant d'ouvrir une *pull request* :

```bash
cd backend && python -m pytest && python manage.py gen_docs --check
cd ../frontend && npm run build && npx playwright test
```

## Pull request

- Remplir le modèle (`.github/pull_request_template.md`).
- Mettre à jour `CHANGELOG.md` (section « Non publié »).
- Une relecture au moins ; la CI doit être verte.

## Signaler une faille de sécurité

Pas d'*issue* publique : voir [SECURITY.md](SECURITY.md).
