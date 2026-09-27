# Journal des modifications

Toutes les modifications notables sont consignées ici. Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versions : [SemVer](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- Schéma OpenAPI (`/api/schema/`), documentation interactive (`/api/docs/`, `/api/redoc/`), fichier `docs/reference/openapi.yaml`.
- Commande `gen_docs` : dictionnaire de données, référence des formulaires et OpenAPI générés depuis le code (`--check` en CI).
- Documentation : architecture (arc42/C4), ADR 0004, références (KPI, rôles, configuration, commandes), guides d'exploitation et guides utilisateurs, CONTRIBUTING, SECURITY.
- Script `scripts/sauvegarde.sh` (base + photos).
- Intégration continue GitHub Actions (tests backend, documentation générée, compilation frontend).

### Modifié
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
