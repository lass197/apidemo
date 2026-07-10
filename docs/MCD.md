# Modèle Conceptuel de Données — SGHL

## Entités principales

### Utilisateurs & sécurité

```
User ──< UserRole >── Role
User ──< AuditLog
```

- **User** : identité, MFA, permissions dérivées des rôles
- **Role** : ADMIN, DOCTOR, NURSE, SECRETARY, BIOLOGIST, PHARMACIST, PATIENT
- **AuditLog** : traçabilité des actions sensibles

### Clinique

```
Patient ──< Hospitalization >── Bed ── Service
Hospitalization ──< Consultation ──< Prescription ──< PrescriptionItem
Consultation ──> ICD10Code (M2M)
Hospitalization ──< CarePlan ──< CareTask
Hospitalization ──< VitalSign
Hospitalization ──< TransferLog
```

### Laboratoire

```
LabOrder ──< LabOrderItem
LabOrder ──< LabResult
```

Workflow : ORDERED → COLLECTED → IN_PROGRESS → VALIDATED

### Pharmacie

```
Medicine ──< MedicineBatch
Prescription (VALIDATED) → décrémentation stock automatique
```

### Facturation

```
Hospitalization ── Invoice ──< Payment
Patient ──< PatientInsurance >── InsuranceProvider
Invoice ──< AccountingEntry
```

### RH & patient

```
User (DOCTOR) ──< DoctorAvailability
Patient ──< Appointment >── User (DOCTOR)
Patient ──< ChatMessage
Patient ──< MedicationReminder
User ──< Shift
```

## Cardinalités clés

| Relation | Cardinalité | Contrainte |
|----------|-------------|------------|
| Patient → Hospitalization | 1:N | 1 active max |
| Bed → Hospitalization | 1:1 | statut AVAILABLE/OCCUPIED |
| Consultation → Prescription | 1:N | validation verrouille |
| CarePlan → CareTask | 1:N | statuts PENDING/DONE/MISSED |
| Invoice → Payment | 1:N | solde calculé |

## Index & performance

- UUID comme clé primaire (sécurité, distribution)
- `Hospitalization.status` + `Bed.status` pour KPIs occupation
- Cache Redis 60s pour `/dashboard/kpis/`

## Versioning optimiste

- `Hospitalization.version` : conflits 409 sur sortie/transfert concurrent
- `Prescription.version` : verrouillage post-validation
