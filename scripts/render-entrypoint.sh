#!/bin/sh
set -e
cd /app/backend
PORT="${PORT:-8000}"
exec gunicorn apidemo.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120
