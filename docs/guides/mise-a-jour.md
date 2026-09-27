# Mettre à jour la plateforme

## Procédure

```bash
cd /opt/ymejibu
./scripts/sauvegarde.sh                        # 1. toujours sauvegarder avant
git fetch --tags && git checkout v0.2.0        # 2. version cible (lire CHANGELOG.md)
docker compose up --build -d                   # 3. reconstruit ; les migrations s'appliquent au démarrage
docker compose logs --tail 50 backend          # 4. vérifier : pas d'erreur de migration
curl -s https://em.ymejibu.org/api/health/     # 5. {"status": "ok"}
```

Les téléphones reçoivent la nouvelle version de l'application automatiquement : le service worker se met à jour à la prochaine ouverture avec du réseau (le fichier `sw.js` n'est jamais mis en cache par nginx). Les fiches en attente sur les téléphones ne sont pas touchées.

## Revenir en arrière

```bash
git checkout v0.1.0
docker compose up --build -d
```

Si la nouvelle version contenait des migrations de base de données, un retour arrière du code ne suffit pas : restaurer la sauvegarde faite à l'étape 1 ([sauvegarde-restauration.md](sauvegarde-restauration.md)).

## Changements de formulaires

Une nouvelle version peut ajouter des champs aux fiches. Les anciennes fiches restent lisibles tant qu'aucune clé n'est renommée ni supprimée (règle de [modifier-un-formulaire.md](modifier-un-formulaire.md)). Prévenir les agents des nouveaux champs.
