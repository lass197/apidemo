# --- Frontend staff ---
FROM node:20-alpine AS staff-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Console admin ---
FROM node:20-alpine AS admin-build
WORKDIR /build/admin
COPY admin/package*.json ./
RUN npm ci
COPY admin/ ./
RUN npm run build

# --- Flutter Web (patient / médecin) ---
FROM ghcr.io/cirruslabs/flutter:stable AS mobile-build
WORKDIR /build
COPY mobile/ ./
RUN flutter config --enable-web \
  && flutter pub get \
  && flutter build web --release --base-href /m/ --dart-define=API_BASE=/api/v1

# --- Backend ---
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ .
COPY --from=staff-build /build/frontend/dist /app/frontend/dist
COPY --from=admin-build /build/admin/dist /app/admin/dist
COPY --from=mobile-build /build/build/web /app/mobile/dist
COPY scripts/render-entrypoint.sh /app/render-entrypoint.sh
RUN chmod +x /app/render-entrypoint.sh \
  && find /app/backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8000
CMD ["/app/render-entrypoint.sh"]
