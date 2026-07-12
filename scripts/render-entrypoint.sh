#!/bin/sh
set -e
cd /app/backend

if [ -z "${DATABASE_URL:-}" ]; then
  echo "================================================================"
  echo "FATAL: DATABASE_URL est manquant sur Render."
  echo "1) Ouvrez sghl-db → Connect → External Database URL"
  echo "2) Collez-la dans sghl-web → Environment → DATABASE_URL"
  echo "3) Supprimez USE_SQLITE s'il existe"
  echo "4) Redéployez"
  echo "================================================================"
  exit 1
fi

# Afficher le host (sans mot de passe) pour le debug
python - <<'PY'
import os
from urllib.parse import urlparse
raw = os.environ.get("DATABASE_URL", "")
u = raw.replace("postgres://", "postgresql://", 1) if raw.startswith("postgres://") else raw
p = urlparse(u)
print(f"DATABASE_URL host brut: {p.hostname!r} db={ (p.path or '/').lstrip('/')!r}")
PY

migrate_ok=0
# Essayer la région demandée puis oregon/frankfurt (hostname externe Render)
regions=""
if [ -n "${RENDER_DB_REGION:-}" ]; then
  regions="$RENDER_DB_REGION"
fi
for candidate in oregon frankfurt; do
  case " $regions " in
    *" $candidate "*) ;;
    *) regions="$regions $candidate" ;;
  esac
done

for region in $regions; do
  export RENDER_DB_REGION="$region"
  echo "Tentative PostgreSQL (région externe=$RENDER_DB_REGION)..."
  if python manage.py migrate --noinput; then
    migrate_ok=1
    echo "OK: Postgres joignable (RENDER_DB_REGION=$RENDER_DB_REGION)"
    break
  fi
  echo "Échec région=$region"
done

if [ "$migrate_ok" -ne 1 ]; then
  echo "================================================================"
  echo "FATAL: PostgreSQL inaccessible."
  echo "Collez l'External Database URL complète (pas l'Internal) dans DATABASE_URL."
  echo "Dashboard → sghl-db → Connect → External Database URL"
  echo "================================================================"
  exit 1
fi

if [ "${SEED_ON_BOOT:-false}" = "true" ]; then
  python manage.py seed_sghl || echo "Seed SGHL ignoré/échoué."
fi

PORT="${PORT:-8000}"
exec gunicorn apidemo.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 120
