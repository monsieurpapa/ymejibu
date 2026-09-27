# Décisions d'architecture (ADR)

Une ADR (*Architecture Decision Record*) consigne une décision structurante : son contexte, la décision, ses conséquences. On n'efface jamais une ADR : si une décision change, on en écrit une nouvelle qui **remplace** l'ancienne, et on met à jour le statut de celle-ci.

| N° | Titre | Statut |
|---|---|---|
| [0001](0001-stack.md) | Pile technique (Django, PostgreSQL, React PWA, Docker Compose ; pas de PostGIS pour l'instant) | Accepté |
| [0002](0002-offline-sync.md) | Formulaires pilotés par définitions et synchronisation hors ligne | Accepté |
| [0003](0003-kpi-history.md) | Calcul des KPI et historique Excel | Accepté |
| [0004](0004-securite-roles.md) | Authentification, rôles et cloisonnement par site | Accepté |

Nouvelle ADR : copier [template.md](template.md) en `NNNN-titre-court.md`, l'ajouter à ce tableau, la faire relire dans la *pull request*.
