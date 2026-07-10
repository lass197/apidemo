# Manuel administrateur — Console SGHL

## Accès

URL : `/admin/` — compte `admin` / `Admin@SGHL2026` (démo)

## Tableau de bord

Statistiques globales : utilisateurs actifs, audit récent, état infrastructure.

## Gestion utilisateurs

- Création / modification comptes personnel
- Attribution rôles (un utilisateur peut avoir plusieurs rôles)
- Activation MFA par utilisateur

## Rôles & permissions

Matrice RBAC : chaque rôle hérite d'un ensemble de permissions (`core.manage_users`, `clinical.prescribe`, etc.)

## Audit & sécurité

Journal des actions : CREATE, UPDATE, DELETE, TRANSFER sur ressources sensibles.
Filtrage par date, utilisateur, type d'action.

## MFA & sécurité

1. Menu **MFA & sécurité**
2. Démarrer configuration → URI provisioning TOTP
3. Scanner avec Google Authenticator
4. Confirmer avec code à 6 chiffres

## Infrastructure

Vue services, lits, départements — gestion capacité hospitalière.

## Comptabilité

Ajustements comptables manuels (permission `billing.adjust`) avec traçabilité audit.

## Maintenance

- Sauvegardes BDD : voir `docs/DEPLOIEMENT.md`
- Logs applicatifs : stdout Gunicorn / Docker
- Mises à jour : `migrate` puis redémarrage
