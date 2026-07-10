#!/bin/sh
set -e
cd /app/backend

# Attendre Postgres (free tier : démarrage parfois lent)
i=0
while [ "$i" -lt 30 ]; do
  if python manage.py migrate --noinput; then
    break
  fi
  i=$((i + 1))
  echo "Migration en attente de la base ($i/30)..."
  sleep 2
done

# Seed en arrière-plan pour ne pas bloquer le health check Render
if [ "${SEED_ON_BOOT:-false}" = "true" ]; then
  (python manage.py seed_sghl && echo "Seed SGHL terminé.") || echo "Seed SGHL ignoré/échoué." &
fi

PORT="${PORT:-8000}"
exec gunicorn apidemo.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 120
