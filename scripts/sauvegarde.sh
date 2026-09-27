#!/usr/bin/env bash
# Sauvegarde de la base PostgreSQL et des photos (voir docs/guides/sauvegarde-restauration.md).
# Usage : ./scripts/sauvegarde.sh   (depuis la racine du dépôt, là où se trouve docker-compose.yml)
# Variables : BACKUP_DIR (défaut /var/backups/ymejibu), KEEP_DAYS (défaut 14), OFFSITE_CMD (copie hors site, optionnelle)
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/ymejibu}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M)"
PROJECT="$(basename "$(pwd)")"
MEDIA_VOLUME="${MEDIA_VOLUME:-${PROJECT}_media}"

mkdir -p "$BACKUP_DIR"
echo "[$(date -Is)] Sauvegarde $STAMP"

docker compose exec -T db pg_dump -U ymejibu -d ymejibu -Fc > "$BACKUP_DIR/db-$STAMP.dump"
docker run --rm -v "$MEDIA_VOLUME":/data:ro -v "$BACKUP_DIR":/backup alpine \
  tar czf "/backup/media-$STAMP.tar.gz" -C /data .

# Vérification minimale : le dump doit être lisible.
docker compose exec -T db pg_restore --list < "$BACKUP_DIR/db-$STAMP.dump" > /dev/null

if [ -n "${OFFSITE_CMD:-}" ]; then
  # Exemple : OFFSITE_CMD='rclone copy /var/backups/ymejibu distant:ymejibu-backups'
  eval "$OFFSITE_CMD"
fi

find "$BACKUP_DIR" -name 'db-*.dump' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name 'media-*.tar.gz' -mtime +"$KEEP_DAYS" -delete
echo "[$(date -Is)] OK : $BACKUP_DIR/db-$STAMP.dump, $BACKUP_DIR/media-$STAMP.tar.gz"
