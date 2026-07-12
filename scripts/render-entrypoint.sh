#!/bin/sh
set -e
cd /app/backend

# Postgres uniquement (pas de bascule SQLite).
# L'URL interne dpg-* est convertie en FQDN externe dans settings.py.
echo "Démarrage avec PostgreSQL..."
i=0
max_tries=20
until python manage.py migrate --noinput; do
  i=$((i + 1))
  if [ "$i" -ge "$max_tries" ]; then
    echo "ERREUR: impossible de joindre PostgreSQL après $max_tries tentatives."
    echo "Vérifiez DATABASE_URL (External Database URL) et RENDER_DB_REGION (oregon|frankfurt)."
    exit 1
  fi
  echo "Migration en attente de Postgres ($i/$max_tries)..."
  sleep 3
done

if [ "${SEED_ON_BOOT:-false}" = "true" ]; then
  python manage.py seed_sghl || echo "Seed SGHL ignoré/échoué."
fi

PORT="${PORT:-8000}"
exec gunicorn apidemo.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 120
