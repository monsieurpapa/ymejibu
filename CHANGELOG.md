# Journal des modifications

Toutes les modifications notables sont consignées ici. Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versions : [SemVer](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- Schéma OpenAPI (`/api/schema/`), documentation interactive (`/api/docs/`, `/api/redoc/`), fichier `docs/reference/openapi.yaml`.
- Commande `gen_docs` : dictionnaire de données, référence des formulaires et OpenAPI générés depuis le code (`--check` en CI).
- Documentation : architecture (arc42/C4), ADR 0004, références (KPI, rôles, configuration, commandes), guides d'exploitation et guides utilisateurs, CONTRIBUTING, SECURITY.
- Script `scripts/sauvegarde.sh` (base + photos).
- Intégration continue GitHub Actions (tests backend, documentation générée, compilation frontend).

- Interface : système de couleurs par type d'action (bleu = principal, vert = valider/enregistrer, rouge = rejeter/supprimer, orange = en attente), icônes par type de fiche et de maintenance (urgente, corrective, préventive, routine, support), mouvements de stock et états des fiches (bibliothèque `lucide-react`).
- Interface : barre d'application, écran d'accueil groupé (relevés, pannes, préventif), en-tête coloré des fiches, messages de confirmation, squelettes de chargement, onglets animés, transitions de page (View Transitions) ; animations désactivées si le système demande moins de mouvement. Contrastes vérifiés ≥ 4,5:1 en thème clair et sombre.

- Mise en production clé en main sur Hetzner (≈ 7–8 €/mois) : `deploy/hetzner-cloud-init.yaml` (pare-feu, SSH par clé, fail2ban, mises à jour automatiques), `deploy/install.sh` (Docker, swap, secrets générés, sauvegarde quotidienne), surcouche `deploy/docker-compose.prod.yml` avec Caddy (HTTPS automatique, HSTS), guide `docs/guides/deploiement-hetzner.md`.
- `DJANGO_BEHIND_HTTPS_PROXY` : cookies sécurisés et prise en compte de `X-Forwarded-Proto` derrière le proxy HTTPS.

### Corrigé
- `DEMO_PASSWORD=` vide dans `.env` ne désactivait pas les comptes de démonstration (la valeur par défaut `demo-2026` était reprise).

### Modifié
- Tableau de bord : le lien de retour s'appelle « Retour aux fiches terrain ».
- Les codes d'articles de stock sont préfixés par le site (`GO-ART-001`) pour permettre plusieurs réseaux.

## [0.1.0] — 2026-09-27

Première version de la plateforme, remplaçant les 5 classeurs Excel de Goma Ouest.

### Ajouté
- Modèle de données (référentiel, fiches, relevés, pannes, ordres de travail, qualité, stock en grand livre, budget, plan) et API REST avec rôles et cloisonnement par site.
- Import idempotent des classeurs avec 63 contrôles qualité et rapport `docs/data-quality-report.md`.
- Moteur de KPI calculé depuis les enregistrements ; export XLSX au format « O&M KPI » et CSV.
- Application mobile hors ligne en français (7 fiches, file d'attente, conflits, GPS, photos).
- Tableau de bord : indicateurs avec tendance et cible, carte, validation des fiches, stock, budget, plan annuel.
- Docker Compose (PostgreSQL, gunicorn, nginx) ; test de bout en bout hors ligne.

### Corrigé (revue avant fusion)
- Relevés périmés après modification ou rejet d'une fiche ; faux conflits et photos dupliquées au renvoi ; une fiche invalide bloquait l'envoi des autres ; taux préventif faussé par le rejet d'une checklist ; lecture des coûts et KPI ouverte à tous les rôles ; réutilisation des numéros de panne.

[Non publié]: https://github.com/monsieurpapa/ymejibu/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/monsieurpapa/ymejibu/releases/tag/v0.1.0
