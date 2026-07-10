# SGHL — Système de Gestion Hospitalière et Laboratoire

ERP médical full-stack : backend Django Ninja, frontend staff Vue 3, console admin, application mobile patient Flutter.

## Démarrage rapide (développement)

```powershell
# Backend
cd backend
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_sghl
python manage.py runserver

# Frontend staff (port 5173)
cd frontend && npm install && npm run dev

# Console admin (port 5174)
cd admin && npm install && npm run dev

# Mobile Flutter
cd mobile && flutter pub get && flutter run
```

## Comptes de démonstration

| Rôle | Identifiant | Mot de passe | Interface |
|------|-------------|--------------|-----------|
| ADMIN | admin | Admin@SGHL2026 | `/admin/` |
| SECRÉTAIRE | sec.dupont | Secretaire@2026 | frontend |
| MÉDECIN | dr.martin | Medecin@2026 | frontend |
| INFIRMIER | inf.bernard | Infirmier@2026 | frontend |
| BIOLOGISTE | bio.leroy | Biologiste@2026 | frontend |
| PHARMACIEN | pharm.vidal | Pharmacien@2026 | frontend |
| PATIENT | alice.moreau | Patient@2026 | mobile |

## Hébergement Render (domaine gratuit)

Blueprint prêt : `render.yaml` → Web + Postgres + Redis sur `https://<service>.onrender.com`.

Voir [docs/DEPLOIEMENT.md](docs/DEPLOIEMENT.md) (section Render) : push GitHub → New Blueprint.

## Docker (production / démo locale)

```powershell
docker compose up --build
# API + SPA sur http://localhost:8000
```

## Documentation

- [Architecture technique (DAT)](docs/DAT.md)
- [Modèle conceptuel (MCD)](docs/MCD.md)
- [Déploiement](docs/DEPLOIEMENT.md)
- [Manuel utilisateur staff](docs/manuels/utilisateur-staff.md)
- [Manuel administrateur](docs/manuels/administrateur.md)
- API OpenAPI : `http://localhost:8000/api/v1/docs`

## Structure

```
backend/     Django + Ninja (API REST)
frontend/    Vue 3 staff (Tailwind)
admin/       Console admin Vue 3
mobile/      Flutter patient
docs/        DAT, MCD, manuels
```

## Tests

```powershell
cd backend
pytest
```
