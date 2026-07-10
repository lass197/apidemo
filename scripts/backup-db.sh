#!/bin/sh
# Sauvegarde PostgreSQL SGHL — usage : ./scripts/backup-db.sh
set -e
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="backups/sghl_${STAMP}.sql.gz"
mkdir -p backups
PGPASSWORD="${DB_PASSWORD:-sghl}" pg_dump -h "${DB_HOST:-localhost}" -U "${DB_USER:-sghl}" "${DB_NAME:-sghl}" | gzip > "$OUT"
echo "Backup : $OUT"
