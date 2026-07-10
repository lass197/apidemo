# Manuel utilisateur — Personnel hospitalier

## Connexion

1. Ouvrir le portail staff (http://localhost:5173 en dev, ou `/` en production)
2. Saisir identifiant et mot de passe fournis par l'administration
3. Le menu affiche uniquement les modules autorisés selon votre rôle

## Modules par rôle

### Secrétaire
- **Patients** : création et recherche dossiers
- **Admissions** : hospitalisation, attribution lit, sortie patient
- **Documents** : dépôt pièces administratives

### Médecin
- **Consultations** : symptômes, diagnostic CIM-10, prescriptions
- **Transferts** : changement de lit/service
- **Documents** : comptes-rendus

### Infirmier
- **Soins** : constantes vitales, plan de soins, alertes doses omises
- Graphique tendance fréquence cardiaque

### Biologiste
- **Laboratoire** : workflow commandes → prélèvement → résultats → validation
- Pas de création de commandes (réservé médecin)

### Pharmacien
- **Pharmacie** : stock, ordonnances validées en attente de délivrance

### Comptabilité (secrétaire/admin)
- **Facturation** : génération factures, tiers-payant, paiements, journal

## Bonnes pratiques

- Déconnexion en fin de poste
- Vérifier le patient avant toute action clinique
- En cas d'erreur 409 (conflit), recharger la page avant de réessayer
