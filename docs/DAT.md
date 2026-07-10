# Document d'Architecture Technique — SGHL

## 1. Vue d'ensemble

SGHL est un ERP hospitalier modulaire couvrant l'admission, le parcours clinique, le laboratoire (LIS), la pharmacie, la facturation et la RH.

### Stack

| Couche | Technologie | Rôle |
|--------|-------------|------|
| API | Django 5 + Django Ninja | REST JSON, JWT, RBAC |
| BDD | PostgreSQL (prod) / SQLite (dev) | Données métier |
| Cache | Redis (optionnel) | KPIs dashboard |
| Staff UI | Vue 3 + Tailwind | Portail personnel |
| Admin UI | Vue 3 + Tailwind | Console administration |
| Mobile | Flutter | Portail patient |
| Auth | JWT + refresh rotation, MFA TOTP | Sécurité |

## 2. Architecture logique

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Frontend   │  │    Admin    │  │   Mobile    │
│  Vue 3      │  │   Vue 3     │  │   Flutter   │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │ HTTPS / JSON
              ┌─────────▼─────────┐
              │  Django Ninja API │
              │  /api/v1/         │
              │  /api/v1/admin/   │
              └─────────┬─────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
    ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
    │PostgreSQL│   │   Redis   │  │  Media  │
    └─────────┘   └───────────┘  └─────────┘
```

## 3. Modules backend

| Module | Responsabilité |
|--------|----------------|
| `core` | Auth JWT, RBAC, audit, MFA, chiffrement fichiers |
| `clinical` | Patients, hospitalisations, consultations, prescriptions, soins |
| `laboratory` | Commandes labo, résultats, workflow LIS |
| `pharmacy` | Stock, lots, délivrance ordonnances |
| `billing` | Factures, paiements, assurance, comptabilité |
| `hr` | Plannings, RDV, chat patient, rappels médicaments |
| `documents` | Upload chiffré, téléchargement sécurisé |
| `administration` | API console admin (users, rôles, infra) |

## 4. Sécurité

- **RBAC** : 7 rôles, permissions granulaires (`core/services/rbac.py`)
- **JWT** : access 15 min, refresh 7 j avec rotation
- **MFA** : TOTP (pyotp) pour comptes sensibles
- **Audit** : journalisation CREATE/UPDATE/DELETE sur ressources critiques
- **Fichiers** : chiffrement Fernet (`FIELD_ENCRYPTION_KEY`)
- **Rate limiting** : login (5 tentatives / 15 min)

## 5. Déploiement

- **Docker Compose** : PostgreSQL + Redis + Gunicorn (voir `docker-compose.yml`)
- **Variables** : `backend/.env.example`
- **Build SPA** : intégré au Dockerfile multi-stage
- **Sauvegarde BDD** : `scripts/backup-db.sh`

## 6. Intégrations futures (P3)

- HL7 / FHIR pour interopérabilité
- Push notifications mobile (FCM)
- WebSocket chat temps réel
- Prometheus / Grafana monitoring
