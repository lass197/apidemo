#!/bin/sh
set -e
cd /app/backend

# Free tier : pas de preDeployCommand — migrations au démarrage
python manage.py migrate --noinput

if [ "${SEED_ON_BOOT:-false}" = "true" ]; then
  python manage.py seed_sghl || true
fi

PORT="${PORT:-8000}"
exec gunicorn apidemo.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120
