# Documentation

La documentation est organisée selon le modèle **Diátaxis** : chaque document répond à un besoin précis. Elle est écrite en français ; le code et l'API sont en anglais.

## Utiliser la plateforme

| Document | Pour qui |
|---|---|
| [Guide terrain](utilisateurs/guide-terrain.md) | Techniciens de zone, points focaux pompage et stockage |
| [Guide des responsables](utilisateurs/guide-responsable.md) | Responsable technique, adjoint, responsable données, SSE, bailleurs |

## Guides pratiques (« comment faire… »)

| Tâche | Document |
|---|---|
| Déployer en production (HTTPS) | [guides/deploiement.md](guides/deploiement.md) |
| Sauvegarder et restaurer | [guides/sauvegarde-restauration.md](guides/sauvegarde-restauration.md) |
| Surveiller le serveur, résoudre un incident | [guides/exploitation.md](guides/exploitation.md) |
| Créer, modifier, désactiver un compte | [guides/gestion-utilisateurs.md](guides/gestion-utilisateurs.md) |
| Mettre à jour vers une nouvelle version | [guides/mise-a-jour.md](guides/mise-a-jour.md) |
| Modifier un formulaire terrain | [guides/modifier-un-formulaire.md](guides/modifier-un-formulaire.md) |
| Ajouter un nouveau réseau | [guides/ajouter-un-site.md](guides/ajouter-un-site.md) |
| Comprendre et relancer l'import Excel | [guides/migration-excel.md](guides/migration-excel.md) |

## Référence

| Sujet | Document |
|---|---|
| Indicateurs : définitions et formules | [reference/kpi.md](reference/kpi.md) |
| Rôles et droits | [reference/roles.md](reference/roles.md) |
| Variables d'environnement et paramètres | [reference/configuration.md](reference/configuration.md) |
| Commandes et scripts | [reference/commandes.md](reference/commandes.md) |
| API REST (OpenAPI 3) | [reference/openapi.yaml](reference/openapi.yaml) · en ligne : `/api/docs/` (Swagger) et `/api/redoc/` |
| Dictionnaire de données *(généré)* | [reference/dictionnaire-donnees.md](reference/dictionnaire-donnees.md) |
| Formulaires terrain *(généré)* | [reference/formulaires.md](reference/formulaires.md) |
| Rapport qualité des données Excel *(généré)* | [data-quality-report.md](data-quality-report.md) |

Les documents marqués *(généré)* sont produits par le code (`python manage.py gen_docs`, `import_excel`) : ne pas les modifier à la main.

## Comprendre (explications)

| Sujet | Document |
|---|---|
| Architecture (arc42, C4), risques, glossaire | [architecture.md](architecture.md) |
| Modèle de données et flux « formulaire → KPI » | [data-model.md](data-model.md) |
| Décisions d'architecture | [adr/README.md](adr/README.md) |
| Stratégie de test | [tests.md](tests.md) |

## Projet

[README](../README.md) · [Contribuer](../CONTRIBUTING.md) · [Journal des modifications](../CHANGELOG.md) · [Sécurité](../SECURITY.md) · [Suivi des tâches](../TASKS.md)
