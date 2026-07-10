# Guide de déploiement SGHL

## Prérequis

- Docker 24+ et Docker Compose v2
- Ou : Python 3.12, Node 20, PostgreSQL 16, Redis 7

## Option A — Render (recommandé, domaine gratuit)

Déploie API + frontend staff + console admin sur `https://<nom>.onrender.com`.

### Limites free tier

| Ressource | Limite |
|-----------|--------|
| Web service | S’endort après ~15 min d’inactivité (cold start ~1 min) |
| Postgres | 1 Go, **expire après 30 jours** (à upgrader pour garder les données) |
| Key Value (Redis) | Sans persistance durable |
| Disque | Éphémère (fichiers `media/` perdus au redéploy) |

L’app mobile Flutter n’est pas hébergée sur Render : build APK localement et pointez l’API vers l’URL Render.

### 1. Pousser le code sur GitHub

Le dossier n’est pas encore un dépôt Git. Depuis la racine du projet :

```powershell
git init
git add .
git commit -m "Préparation déploiement Render SGHL"
# Créer un dépôt vide sur GitHub, puis :
gh repo create sghl --private --source=. --remote=origin --push
# ou : git remote add origin https://github.com/VOTRE_USER/sghl.git
#      git push -u origin main
```

Ne pas committer `backend/.env` ni `backend/tools/` (déjà dans `.gitignore`).

### 2. Créer le Blueprint Render

1. Compte sur [render.com](https://render.com) (connexion GitHub)
2. **Dashboard → New → Blueprint**
3. Sélectionner le dépôt contenant `render.yaml`
4. Appliquer le Blueprint (crée `sghl-web`, `sghl-db`, `sghl-redis`)
5. Quand Render demande `FIELD_ENCRYPTION_KEY`, générer localement :

```powershell
py -3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

6. Renseigner optionnellement les variables email (SMTP) si demandées

> **Free tier** : `preDeployCommand` n’est pas supporté. Les migrations et le seed démo
> s’exécutent au démarrage du conteneur (`scripts/render-entrypoint.sh`, `SEED_ON_BOOT=true`).

URL publique : `https://sghl-web.onrender.com` (ou le nom choisi).

### 3. Après le premier déploiement

Les migrations et le seed démo partent automatiquement (`preDeployCommand` + `initialDeployHook`).

Comptes démo : voir [README.md](../README.md).

- Staff : `https://<service>.onrender.com/`
- Admin : `https://<service>.onrender.com/admin/`
- API docs : `https://<service>.onrender.com/api/v1/docs`

### 4. Mobile Flutter

```bash
# Dans mobile/, configurer l’URL API de production (selon votre client HTTP)
flutter build apk --release
```

## Option B — Docker Compose (local / VPS)

```bash
cp backend/.env.docker backend/.env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_sghl
```

Accès : http://localhost:8000 (API + frontend staff + admin `/admin/`)

## Option C — Installation manuelle

### 1. Base de données PostgreSQL

```sql
CREATE DATABASE sghl;
CREATE USER sghl WITH PASSWORD 'sghl';
GRANT ALL PRIVILEGES ON DATABASE sghl TO sghl;
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt gunicorn
cp .env.example .env
# Éditer .env : DB_ENGINE=postgresql, REDIS_URL, SECRET_KEY, FIELD_ENCRYPTION_KEY
python manage.py migrate
python manage.py seed_sghl
python manage.py collectstatic --noinput
gunicorn apidemo.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### 3. Frontends (build production)

```bash
cd frontend && npm ci && npm run build
cd admin && npm ci && npm run build
```

Les builds sont servis par Django depuis `frontend/dist` et `admin/dist`.

## Variables d'environnement critiques

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé Django (obligatoire en prod) |
| `FIELD_ENCRYPTION_KEY` | Clé Fernet pour documents |
| `DATABASE_URL` | Connexion Postgres (Render) — prioritaire sur `DB_*` |
| `DB_*` | Connexion PostgreSQL (Docker Compose / manuel) |
| `REDIS_URL` | Cache KPIs (optionnel ; LocMem sinon) |
| `EMAIL_*` | SMTP confirmations RDV / OTP |
| `CORS_ALLOWED_ORIGINS` | Origines front autorisées |
| `RENDER_EXTERNAL_URL` | Injecté par Render (HTTPS public) |

## Sauvegarde

```bash
DB_PASSWORD=sghl ./scripts/backup-db.sh
```

## APK Flutter

```bash
cd mobile
flutter pub get
flutter build apk --release
# Sortie : build/app/outputs/flutter-apk/app-release.apk
```

## OpenAPI

Documentation interactive : `/api/v1/docs` (Swagger UI Django Ninja)
