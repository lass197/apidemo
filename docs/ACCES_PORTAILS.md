# Guide d'accès — SGHL

## Les 3 portails

| Profil | URL | Compte démo | Interface |
|--------|-----|-------------|-----------|
| **Administrateur** | `/admin/` | admin / Admin@SGHL2026 | Console RBAC, audit, infra |
| **Personnel** | `/login` → `/dashboard` | sec.dupont, dr.martin… | Modules métier selon rôle |
| **Patient** | `/patient/register` → `/patient` | Inscription — email unique obligatoire |
| **Patient (démo)** | `/patient/login` | alice.moreau / Patient@2026 |
| **Patient mobile** | App Flutter → « Créer un compte » | `POST /auth/register/patient/` |

Page d'accueil publique : `/` — choix du portail.

## Permissions par rôle (résumé)

- **ADMIN** : tout + console `/admin/`
- **SECRETARY** : admissions, patients, facturation, documents, RH
- **DOCTOR** : consultations, prescriptions, transferts, labo (commandes), documents
- **NURSE** : soins infirmiers, constantes, plan de soins
- **BIOLOGIST** : validation résultats labo (pas de commandes)
- **PHARMACIST** : stock, dispensation, ordonnances validées
- **PATIENT** : son dossier uniquement (web + mobile)

Matrice complète : Admin → Rôles & permissions.

## Inscription patient

- **Endpoint** : `POST /api/v1/auth/register/patient/` (public, rate limit 10/h/IP)
- **Email unique** : vérifié sur `User.email` et `Patient.email`
- **Liaison dossier** : si la secrétaire a créé un dossier avec le même email (sans compte), l'inscription lie automatiquement le compte
- **Connexion** : identifiant ou email + mot de passe
