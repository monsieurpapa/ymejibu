# Commandes

## Commandes de gestion Django

À lancer depuis `backend/` (`python manage.py …`) ou dans le conteneur (`docker compose exec backend python manage.py …`).

| Commande | Rôle | Options |
|---|---|---|
| `migrate` | Crée / met à jour les tables | |
| `import_excel` | Importe les 5 classeurs (idempotent) et écrit le rapport qualité | `--dir` dossier des classeurs · `--year 2026` · `--today AAAA-MM-JJ` · `--history-status actual\|provisional` · `--site-code GO` · `--site-name "Goma Ouest"` · `--report chemin.md` |
| `create_demo_users` | Un compte de démonstration par rôle, relié au personnel importé | `--password` (obligatoire) · `--site GO` |
| `plan_work_orders` | Crée les ordres de travail préventifs planifiés d'un mois à partir du plan annuel (idempotent) | `--month AAAA-MM` (obligatoire) · `--site GO` |
| `gen_docs` | Régénère la documentation de référence (dictionnaire de données, formulaires, OpenAPI) | `--check` : échoue si un fichier est périmé (CI) |
| `spectacular` | Exporte le schéma OpenAPI | `--file schema.yaml --validate` |
| `createsuperuser` | Crée un administrateur | |
| `changepassword <identifiant>` | Change un mot de passe | |
| `drf_create_token <identifiant>` | Crée un jeton d'API | `-r` pour le régénérer (révoque l'ancien) |
| `collectstatic` | Rassemble les fichiers statiques de l'administration | fait dans l'image Docker |

## Scripts

| Script | Rôle |
|---|---|
| `scripts/build_forms.py` | Génère `shared/forms.fr.json` (définition des 7 formulaires) |
| `scripts/e2e-backend.sh` | Démarre un backend jetable pour le test de bout en bout (base `ymejibu_e2e`) |
| `backend/docker-entrypoint.sh` | Entrée du conteneur : attente de PostgreSQL, migrations, import au premier démarrage, comptes de démonstration |

## Frontend (`frontend/`)

| Commande | Rôle |
|---|---|
| `npm install` | Dépendances |
| `npm run dev` | Serveur de développement (http://localhost:5173, relaie `/api` vers `BACKEND_URL`) |
| `npm run build` | Vérification TypeScript + compilation dans `dist/` (service worker inclus) |
| `npm run preview` | Sert `dist/` sur le port 4173 |
| `npm run typecheck` | Vérification TypeScript seule |
| `npx playwright test` | Test de bout en bout hors ligne |

## Docker Compose

| Commande | Rôle |
|---|---|
| `docker compose up --build -d` | Construit et démarre (http://localhost:8080) |
| `docker compose ps` | État des services |
| `docker compose logs -f backend` | Journaux du backend |
| `docker compose exec backend python manage.py …` | Commande de gestion dans le conteneur |
| `docker compose down` | Arrête (les données restent dans les volumes `pgdata` et `media`) |
| `docker compose down -v` | Arrête **et supprime les données** — irréversible |
