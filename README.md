# Yme Jibu — Plateforme d'Exploitation & Maintenance (E&M)

Plateforme hors ligne d'abord pour l'exploitation et la maintenance du réseau d'eau potable **Goma Ouest** (Mugunga–Lac Vert, RDC). Elle remplace les 5 classeurs Excel historiques :

- **application mobile (PWA) en français** : les 7 fiches terrain, utilisables une journée entière sans réseau ;
- **API** Django REST documentée (OpenAPI), avec rôles et cloisonnement par site ;
- **moteur de KPI** calculé à partir des enregistrements (plus aucune référence de cellule) ;
- **tableau de bord** : indicateurs avec tendance et cible, carte, validation des fiches, stock, budget, plan annuel, export au format « O&M KPI » ;
- **import Excel** idempotent avec **rapport qualité** : [docs/data-quality-report.md](docs/data-quality-report.md).

Les classeurs Excel ne sont jamais modifiés (lecture seule) et ne sont pas versionnés dans Git.

## Démarrage rapide (Docker)

Prérequis : Docker et Docker Compose ; les 5 classeurs `.xlsx` à la racine du dépôt.

```bash
docker compose up --build
```

Ouvrir <http://localhost:8080>. Au premier démarrage, le backend applique les migrations, importe les classeurs (rapport dans `docs/data-quality-report.md`) et crée des **comptes de démonstration** — un par rôle, mot de passe `demo-2026` : `resp`, `adjoint`, `tech1`, `tech2`, `pompage`, `stockage`, `sse`, `donnees`, `bailleur`.

| URL | Contenu |
|---|---|
| <http://localhost:8080/> | Application terrain et tableau de bord |
| <http://localhost:8080/api/docs/> | Documentation interactive de l'API (Swagger) |
| <http://localhost:8080/api/redoc/> | Documentation de l'API (ReDoc) |
| <http://localhost:8080/admin/> | Administration (super-utilisateur : `docker compose exec backend python manage.py createsuperuser`) |

> Production : suivre [docs/guides/deploiement.md](docs/guides/deploiement.md) (HTTPS obligatoire, secrets, **aucun compte de démonstration**) ; recette automatisée pour un serveur Hetzner à ≈ 7–8 €/mois : [docs/guides/deploiement-hetzner.md](docs/guides/deploiement-hetzner.md).

## Documentation

Index complet : **[docs/README.md](docs/README.md)**.

| Vous êtes… | Commencez par |
|---|---|
| Technicien, point focal | [Guide terrain](docs/utilisateurs/guide-terrain.md) |
| Responsable, bailleur | [Guide des responsables](docs/utilisateurs/guide-responsable.md) · [Définition des KPI](docs/reference/kpi.md) |
| Administrateur système | [Déploiement](docs/guides/deploiement.md) · [Sauvegarde](docs/guides/sauvegarde-restauration.md) · [Exploitation](docs/guides/exploitation.md) |
| Développeur | [Architecture](docs/architecture.md) · [Modèle de données](docs/data-model.md) · [ADR](docs/adr/README.md) · [Contribuer](CONTRIBUTING.md) |

## Développement sans Docker

Prérequis : Python 3.11, Node 22, PostgreSQL 16 (utilisateur/mot de passe/base `ymejibu`, droit `CREATEDB`).

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py import_excel                       # voir docs/reference/commandes.md
python manage.py create_demo_users --password demo-2026
python manage.py runserver                          # http://localhost:8000

# Frontend (autre terminal)
cd frontend
npm install
npm run dev                                         # http://localhost:5173 (relaie /api vers :8000)
```

## Tests

```bash
cd backend && python -m pytest                      # formules, KPI, synchro, droits, import réel, défauts Excel, export
python manage.py gen_docs --check                   # documentation générée à jour
cd ../frontend && npx playwright test               # bout en bout : fiches hors ligne → synchro → KPI
```

Stratégie et règles : [docs/tests.md](docs/tests.md). La CI (`.github/workflows/ci.yml`) exécute les tests backend, la vérification de la documentation générée et la compilation du frontend.

## Arborescence

```
backend/        Django : core (référentiel, rôles), ops (fiches, dérivation, synchro), stock, plan, kpi, importer, tests/
frontend/       PWA React/TypeScript : pages terrain, formulaires, file d'attente hors ligne, tableau de bord, e2e/
shared/         forms.fr.json — définition unique des 7 fiches (générée par scripts/build_forms.py)
scripts/        build_forms.py, e2e-backend.sh, sauvegarde.sh
docs/           architecture, modèle de données, ADR, guides, références (dont fichiers générés)
docker-compose.yml
```

## Contribuer, sécurité, versions

- [CONTRIBUTING.md](CONTRIBUTING.md) — branches, commits, règles de code, fichiers générés, *pull requests*
- [SECURITY.md](SECURITY.md) — signaler une vulnérabilité, limites connues
- [CHANGELOG.md](CHANGELOG.md) — journal des modifications

## Licence

À définir par Yme Jibu (aucun fichier `LICENSE` pour l'instant : le code n'est pas encore sous licence libre).
