# Politique de sécurité

## Signaler une vulnérabilité

Ne pas ouvrir d'*issue* publique. Écrire au Responsable technique de Yme Jibu (adresse communiquée aux contributeurs) ou utiliser la fonction **Security → Report a vulnerability** du dépôt GitHub. Indiquer : la version ou le commit, les étapes pour reproduire, l'impact estimé.

Engagement : accusé de réception sous 5 jours ouvrés, correctif ou mesure de contournement sous 30 jours pour une faille grave.

## Versions prises en charge

| Version | Correctifs de sécurité |
|---|---|
| dernière version publiée | oui |
| versions antérieures | non : mettre à jour |

## Mesures en place

- HTTPS obligatoire en production ; `DJANGO_DEBUG=0` ; secrets en variables d'environnement, jamais dans Git.
- Authentification par jeton individuel ; droits vérifiés côté serveur par rôle ; données cloisonnées par site ([ADR 0004](docs/adr/0004-securite-roles.md), [rôles](docs/reference/roles.md)).
- Validation serveur de chaque fiche (types, plages, listes, existence des actifs) ; taille des photos limitée.
- Numéros de panne attribués par le serveur ; fiches validées verrouillées pour les agents.
- Classeurs Excel ouverts en lecture seule.

## Limites connues

| Limite | Mesure |
|---|---|
| Les jetons n'expirent pas | Supprimer le jeton d'un téléphone perdu dans `/admin/` |
| Fiches en attente non chiffrées sur le téléphone | Verrouillage d'écran obligatoire sur les téléphones |
| Pas de limitation des tentatives de connexion | Limiter au reverse proxy (ex. `rate_limit` Caddy, `limit_req` nginx) |
| Photos servies par Django sous des noms aléatoires, sans contrôle d'accès | Ne pas photographier de personnes ni de documents |
| Comptes de démonstration à mot de passe commun | `DEMO_PASSWORD` vide en production |
