#!/bin/sh
set -e
cd /app/backend

migrated=0
i=0
while [ "$i" -lt 12 ]; do
  if python manage.py migrate --noinput; then
    migrated=1
    break
  fi
  i=$((i + 1))
  echo "Migration en attente de Postgres ($i/12)..."
  sleep 2
done

# Si Postgres est inaccessible (région, URL interne, DB down) → SQLite démo
if [ "$migrated" -ne 1 ]; then
  echo "WARN: Postgres inaccessible — bascule SQLite pour la démo."
  unset DATABASE_URL
  export DB_ENGINE=sqlite
  python manage.py migrate --noinput
fi

# Seed synchrone : comptes admin + patient disponibles dès le démarrage
if [ "${SEED_ON_BOOT:-false}" = "true" ]; then
  python manage.py seed_sghl || echo "Seed SGHL ignoré/échoué."
fi

PORT="${PORT:-8000}"
exec gunicorn apidemo.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 120
