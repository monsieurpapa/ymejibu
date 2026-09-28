# Configuration

Toute la configuration passe par des **variables d'environnement** (principe « 12-factor ») lues dans `backend/config/settings.py`. Avec Docker Compose, elles se définissent dans un fichier `.env` à la racine (jamais commité) ou dans l'environnement du shell.

## Backend (Django)

| Variable | Défaut | Production | Rôle |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | clé de développement | **obligatoire**, 50+ caractères aléatoires | Signature des sessions et jetons CSRF |
| `DJANGO_DEBUG` | `1` en natif, `0` en Compose | `0` | Pages d'erreur détaillées (jamais en production) |
| `DJANGO_ALLOWED_HOSTS` | `*` | nom de domaine, ex. `em.ymejibu.org` | Hôtes acceptés |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | vide | `https://em.ymejibu.org` | Origines de confiance pour `/admin/` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | vide (même origine derrière nginx) | Serveur de développement Vite |
| `DB_ENGINE` | `postgres` | `postgres` | `sqlite` possible pour un essai rapide |
| `POSTGRES_HOST` | `localhost` | `db` (Compose) | |
| `POSTGRES_PORT` | `5432` | | |
| `POSTGRES_DB` | `ymejibu` | | |
| `POSTGRES_USER` | `ymejibu` | | |
| `POSTGRES_PASSWORD` | `ymejibu` | **obligatoire**, fort | |
| `MEDIA_ROOT` | `backend/media` | `/data/media` (volume) | Photos des pannes |
| `WORKBOOK_DIR` | racine du dépôt | `/workbooks` (Compose, lecture seule) | Dossier des 5 classeurs Excel |
| `DATA_QUALITY_REPORT` | `docs/data-quality-report.md` | `/reports/data-quality-report.md` | Rapport écrit par `import_excel` |
| `DJANGO_BEHIND_HTTPS_PROXY` | `0` | `1` | Derrière le proxy HTTPS (Caddy) : fait confiance à `X-Forwarded-Proto`, cookies `Secure` |
| `FORMS_DEFINITION_FILE` | `shared/forms.fr.json` | | Définitions des formulaires |

## Entrée du conteneur backend (`backend/docker-entrypoint.sh`)

| Variable | Défaut | Rôle |
|---|---|---|
| `IMPORT_ON_START` | `1` | Importe les classeurs au premier démarrage (base vide) ; ignoré ensuite |
| `DEMO_PASSWORD` | `demo-2026` dans `docker-compose.yml` (si la variable est absente) | Crée les comptes de démonstration ; `DEMO_PASSWORD=` (vide) dans `.env` les désactive. **Vide en production** (imposé par `deploy/docker-compose.prod.yml`) |

## Docker Compose (production, `deploy/`)

| Variable | Exemple | Rôle |
|---|---|---|
| `COMPOSE_FILE` | `docker-compose.yml:deploy/docker-compose.prod.yml` | Ajoute la surcouche de production (Caddy, journaux limités) à chaque `docker compose` |
| `DOMAIN` | `em.203-0-113-10.sslip.io` | Nom servi en HTTPS par Caddy (certificat Let's Encrypt automatique) |
| `WEB_BIND` | `127.0.0.1:8080` | Adresse de publication de nginx ; `8080` (défaut) l'expose sur toutes les interfaces, pour le poste de développement uniquement |

## Frontend

| Variable | Défaut | Rôle |
|---|---|---|
| `BACKEND_URL` | `http://127.0.0.1:8000` | Cible du relais `/api` pour `npm run dev` et `npm run preview` |
| `PW_CHROMIUM_PATH` | — | Chemin d'un Chromium existant pour les tests Playwright |

En production, le frontend compilé est servi par nginx (`frontend/nginx.conf`) qui relaie `/api`, `/admin`, `/static` et `/media` vers le backend : aucune variable n'est nécessaire.

## Paramètres métier (en base, modifiables dans `/admin/` ou via l'API)

| Paramètre | Table | Valeur initiale |
|---|---|---|
| Tarif électricité (USD/kWh) | `Tariff` | 0,25 (lu dans la formule `O&M KPI!C63`) |
| Prix du carburant (USD/L) | `Tariff` | 1,7 (lu dans `O&M KPI!C64`) |
| Seuils de qualité | `QualityThreshold` | voir [kpi.md](kpi.md#qualité-de-leau), à confirmer |
| Budget mensuel | `MonthlyBudget` | ligne 70 de `O&M KPI` |
| Seuils d'alerte de stock | `StockItem.min_threshold` | vides : à définir |
| Zones et affectations | `Zone`, `Asset.zone`, `Node.zone`, `Person.zone` | zones Z1–Z3 ; affectations à compléter |

## Exemple de `.env` de production

```dotenv
DJANGO_SECRET_KEY=remplacer-par-une-longue-chaine-aleatoire
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=em.ymejibu.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://em.ymejibu.org
POSTGRES_PASSWORD=remplacer-par-un-mot-de-passe-fort
DEMO_PASSWORD=
IMPORT_ON_START=1
```

Générer une clé : `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`.
