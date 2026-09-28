# Sauvegarder et restaurer

Deux éléments contiennent des données : la base **PostgreSQL** (volume `pgdata`) et les **photos** (volume `media`). Le code et les classeurs Excel se retrouvent dans Git et chez Yme Jibu.

| Objectif | Valeur conseillée |
|---|---|
| Fréquence | Quotidienne (nuit) + avant chaque mise à jour |
| Conservation | 14 sauvegardes quotidiennes + 12 mensuelles |
| Emplacement | Hors du serveur (autre machine, stockage objet), chiffré |
| Test de restauration | Une fois par trimestre |

## Sauvegarder

```bash
cd /opt/ymejibu
STAMP=$(date +%Y%m%d-%H%M)
mkdir -p /var/backups/ymejibu

# Base de données (format compressé de pg_dump)
docker compose exec -T db pg_dump -U ymejibu -d ymejibu -Fc > /var/backups/ymejibu/db-$STAMP.dump

# Photos
docker run --rm -v ymejibu_media:/data:ro -v /var/backups/ymejibu:/backup alpine \
  tar czf /backup/media-$STAMP.tar.gz -C /data .
```

Le nom du volume (`ymejibu_media`) dépend du nom du dossier : le vérifier avec `docker volume ls`.

Tâche planifiée (`crontab -e`, tous les jours à 2 h) :

```cron
0 2 * * * cd /opt/ymejibu && ./scripts/sauvegarde.sh >> /var/log/ymejibu-backup.log 2>&1
```

(`scripts/sauvegarde.sh` contient les commandes ci-dessus plus la copie hors site et la suppression des anciennes sauvegardes, à adapter à l'hébergement.)

## Restaurer

> La restauration **remplace** les données actuelles. Arrêter le backend pour qu'aucune fiche n'arrive pendant l'opération.

```bash
cd /opt/ymejibu
docker compose stop backend web

# Base
docker compose exec -T db dropdb -U ymejibu ymejibu
docker compose exec -T db createdb -U ymejibu ymejibu
docker compose exec -T db pg_restore -U ymejibu -d ymejibu --no-owner < /var/backups/ymejibu/db-AAAAMMJJ-HHMM.dump

# Photos
docker run --rm -v ymejibu_media:/data -v /var/backups/ymejibu:/backup alpine \
  sh -c "rm -rf /data/* && tar xzf /backup/media-AAAAMMJJ-HHMM.tar.gz -C /data"

IMPORT_ON_START=0 docker compose up -d
curl -s http://127.0.0.1:8080/api/health/
```

`IMPORT_ON_START=0` évite tout nouvel import Excel (de toute façon ignoré si la base contient déjà un site).

## Après une restauration

Les téléphones gardent leurs fiches en attente et les renverront. Une fiche envoyée **après** la date de la sauvegarde, puis perdue par la restauration, est renvoyée seulement si elle est encore sur le téléphone en statut « en attente » ; demander aux agents de vérifier l'écran « Mes fiches » et de renvoyer les fiches concernées.
