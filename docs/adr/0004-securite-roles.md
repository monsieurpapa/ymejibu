# ADR 0004 — Authentification, rôles et cloisonnement par site

**Statut :** accepté · **Date :** 2026-09-27

## Contexte

Les agents de terrain travaillent hors ligne sur des téléphones partagés ou personnels ; les responsables et bailleurs consultent au bureau. Les données (coûts, pannes, photos, personnel) ne doivent être vues que par les rôles concernés, et plusieurs réseaux doivent pouvoir cohabiter. La revue avant fusion a montré qu'un contrôle d'accès « par défaut ouvert en lecture » exposait les coûts et KPI aux techniciens et prestataires.

## Options étudiées

1. **Jeton DRF sans expiration + rôles en base** — simple, fonctionne hors ligne (le jeton reste valable entre deux connexions), révocable depuis l'administration.
2. JWT à courte durée + jeton de rafraîchissement — plus sûr en cas de vol, mais un agent resté hors ligne plusieurs jours devrait se reconnecter avec du réseau avant de pouvoir envoyer ses fiches.
3. Groupes/permissions Django par modèle — fin mais lourd à administrer pour une petite équipe.

## Décision

- Authentification par **jeton DRF** (`Authorization: Token …`) pour l'API ; session Django pour `/admin/`.
- Le **rôle** est porté par la fiche `Person` reliée au compte ; un compte sans rôle est refusé.
- Chaque vue déclare `read_roles` et `write_roles` (`core/permissions.py`) ; les données opérationnelles, coûts et KPI sont réservés à `DASHBOARD_ROLES` (responsables, SSE, bailleurs) ; les techniciens lisent le référentiel et leurs propres fiches.
- Chaque formulaire liste les rôles qui peuvent le remplir ; un agent ne modifie que ses fiches ; une fiche validée est verrouillée pour lui.
- Toutes les requêtes sont **filtrées par le site** de l'utilisateur, y compris la résolution des codes (`CodeRelatedField`).
- Les numéros de panne sont attribués par le serveur (compteur verrouillé), jamais par le téléphone.

## Conséquences

- Un téléphone perdu garde un accès valide jusqu'à la révocation de son jeton : procédure dans [../guides/exploitation.md](../guides/exploitation.md). Passer à des jetons expirants est inscrit en dette (architecture, R2).
- Les fiches en attente sont stockées en clair dans IndexedDB : exiger un verrouillage d'écran sur les téléphones.
- Toute nouvelle vue doit déclarer ses rôles et avoir un test de refus (voir [../reference/roles.md](../reference/roles.md)).
