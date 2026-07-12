#!/bin/sh
set -e
cd /app/backend

# Free tier : Postgres interne souvent inaccessible (région / DNS).
# USE_SQLITE=true → ignore DATABASE_URL et démarre immédiatement.
if [ "${USE_SQLITE:-false}" = "true" ]; then
  echo "USE_SQLITE=true — démarrage avec SQLite (démo)."
  unset DATABASE_URL
  export DB_ENGINE=sqlite
  python manage.py migrate --noinput
else
  migrated=0
  i=0
  max_tries=3
  while [ "$i" -lt "$max_tries" ]; do
    if python manage.py migrate --noinput; then
      migrated=1
      break
    fi
    i=$((i + 1))
    echo "Migration en attente de Postgres ($i/$max_tries)..."
    sleep 2
  done

  if [ "$migrated" -ne 1 ]; then
    echo "WARN: Postgres inaccessible — bascule SQLite pour la démo."
    unset DATABASE_URL
    export DB_ENGINE=sqlite
    python manage.py migrate --noinput
  fi
fi

if [ "${SEED_ON_BOOT:-false}" = "true" ]; then
  python manage.py seed_sghl || echo "Seed SGHL ignoré/échoué."
fi

PORT="${PORT:-8000}"
exec gunicorn apidemo.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 120
