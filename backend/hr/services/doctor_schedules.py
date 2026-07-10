"""Génération d'agendas médecins réalistes — plages hebdomadaires variées."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from django.utils import timezone

from hr.models import DoctorAvailability

# weekday: 0=lundi … 6=dimanche ; sessions = (h_debut, m_debut, h_fin, m_fin)
SPECIALTY_SCHEDULES: dict[str, list[dict]] = {
    "Médecine générale": [
        {"weekday": 0, "sessions": [(8, 0, 12, 0), (14, 0, 17, 30)]},
        {"weekday": 1, "sessions": [(8, 30, 12, 30)]},
        {"weekday": 2, "sessions": [(8, 0, 12, 0), (14, 0, 18, 0)]},
        {"weekday": 3, "sessions": [(9, 0, 12, 30)]},
        {"weekday": 4, "sessions": [(8, 0, 12, 0), (14, 0, 16, 30)]},
    ],
    "Cardiologie": [
        {"weekday": 0, "sessions": [(8, 30, 12, 0)]},
        {"weekday": 2, "sessions": [(8, 30, 12, 0), (14, 0, 17, 0)]},
        {"weekday": 4, "sessions": [(9, 0, 12, 30)]},
        {"weekday": 1, "sessions": [(14, 0, 17, 30)]},
    ],
    "Pédiatrie": [
        {"weekday": 0, "sessions": [(8, 30, 12, 30), (14, 0, 18, 0)]},
        {"weekday": 1, "sessions": [(9, 0, 12, 0)]},
        {"weekday": 2, "sessions": [(8, 30, 12, 30)]},
        {"weekday": 3, "sessions": [(14, 0, 18, 30)]},
        {"weekday": 4, "sessions": [(8, 0, 12, 0), (14, 0, 17, 0)]},
        {"weekday": 5, "sessions": [(9, 0, 12, 0)]},
    ],
    "Gynécologie": [
        {"weekday": 1, "sessions": [(8, 30, 12, 30)]},
        {"weekday": 2, "sessions": [(14, 0, 17, 30)]},
        {"weekday": 3, "sessions": [(8, 30, 12, 0)]},
        {"weekday": 4, "sessions": [(9, 0, 12, 30), (14, 0, 16, 30)]},
    ],
    "Dermatologie": [
        {"weekday": 0, "sessions": [(9, 0, 12, 30)]},
        {"weekday": 2, "sessions": [(14, 0, 18, 0)]},
        {"weekday": 4, "sessions": [(8, 30, 12, 0)]},
        {"weekday": 1, "sessions": [(14, 0, 17, 0)]},
    ],
    "Neurologie": [
        {"weekday": 0, "sessions": [(9, 0, 12, 30)]},
        {"weekday": 2, "sessions": [(9, 0, 12, 0), (14, 0, 17, 30)]},
        {"weekday": 1, "sessions": [(14, 0, 18, 0)]},
        {"weekday": 4, "sessions": [(9, 30, 12, 30)]},
    ],
    "Ophtalmologie": [
        {"weekday": 1, "sessions": [(8, 0, 12, 0)]},
        {"weekday": 3, "sessions": [(8, 30, 12, 30), (14, 0, 17, 0)]},
        {"weekday": 5, "sessions": [(9, 0, 12, 0)]},
    ],
    "ORL": [
        {"weekday": 0, "sessions": [(14, 0, 17, 30)]},
        {"weekday": 2, "sessions": [(8, 30, 12, 30)]},
        {"weekday": 4, "sessions": [(8, 30, 12, 0), (14, 0, 16, 30)]},
    ],
    "Chirurgie générale": [
        {"weekday": 1, "sessions": [(8, 0, 12, 0)]},
        {"weekday": 3, "sessions": [(14, 0, 17, 0)]},
        {"weekday": 4, "sessions": [(9, 0, 12, 30)]},
    ],
    "Pneumologie": [
        {"weekday": 0, "sessions": [(9, 0, 12, 0)]},
        {"weekday": 2, "sessions": [(14, 0, 17, 30)]},
        {"weekday": 4, "sessions": [(9, 0, 12, 30), (14, 0, 17, 0)]},
        {"weekday": 1, "sessions": [(9, 0, 12, 0)]},
    ],
    "Urologie": [
        {"weekday": 1, "sessions": [(8, 30, 12, 0), (14, 0, 17, 0)]},
        {"weekday": 3, "sessions": [(9, 0, 12, 30)]},
        {"weekday": 4, "sessions": [(14, 0, 17, 30)]},
    ],
    "Psychiatrie": [
        {"weekday": 0, "sessions": [(14, 0, 18, 0)]},
        {"weekday": 2, "sessions": [(9, 0, 12, 30), (14, 0, 17, 30)]},
        {"weekday": 4, "sessions": [(9, 0, 12, 0)]},
    ],
    "Rhumatologie": [
        {"weekday": 1, "sessions": [(9, 0, 12, 30)]},
        {"weekday": 3, "sessions": [(8, 30, 12, 0), (14, 0, 17, 0)]},
        {"weekday": 5, "sessions": [(9, 0, 11, 30)]},
    ],
    "Endocrinologie": [
        {"weekday": 0, "sessions": [(8, 30, 12, 0)]},
        {"weekday": 2, "sessions": [(14, 0, 17, 30)]},
        {"weekday": 4, "sessions": [(9, 0, 12, 30), (14, 0, 16, 30)]},
    ],
    "Radiologie": [
        {"weekday": 1, "sessions": [(8, 0, 12, 0), (14, 0, 17, 0)]},
        {"weekday": 2, "sessions": [(8, 30, 12, 30)]},
        {"weekday": 4, "sessions": [(9, 0, 12, 0)]},
    ],
    "Anesthésie-réanimation": [
        {"weekday": 0, "sessions": [(8, 0, 12, 0)]},
        {"weekday": 3, "sessions": [(14, 0, 17, 0)]},
    ],
}

# Décalage individuel pour éviter que tous les médecins d'une spé. aient les mêmes jours
WEEKDAY_SHIFTS = [0, 1, -1, 2, -2]

SLOT_DURATION_BY_SPECIALTY = {
    "Chirurgie générale": 45,
    "Gynécologie": 45,
    "Psychiatrie": 45,
    "Cardiologie": 45,
}


def _schedule_for_specialty(specialty: str, doctor_key: str) -> list[dict]:
    base = SPECIALTY_SCHEDULES.get(specialty)
    if not base:
        base = SPECIALTY_SCHEDULES["Médecine générale"]
    shift = WEEKDAY_SHIFTS[abs(hash(doctor_key)) % len(WEEKDAY_SHIFTS)]
    rotated: list[dict] = []
    for day in base:
        wd = (day["weekday"] + shift) % 7
        if wd >= 5 and specialty not in ("Pédiatrie", "Ophtalmologie", "Rhumatologie"):
            continue
        rotated.append({"weekday": wd, "sessions": day["sessions"]})
    return rotated


def _slot_duration(specialty: str) -> int:
    return SLOT_DURATION_BY_SPECIALTY.get(specialty, 30)


def _make_aware(dt: datetime) -> datetime:
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


def generate_doctor_availabilities(
    doctor,
    *,
    specialty: str,
    weeks_ahead: int = 8,
    replace_existing: bool = True,
) -> int:
    """Crée des plages de consultation sur N semaines (matin / après-midi, jours mélangés)."""
    now = timezone.now()
    today = now.date()
    # Commencer lundi de la semaine courante ou suivante
    start_monday = today - timedelta(days=today.weekday())
    if now.hour >= 18:
        start_monday += timedelta(days=7)

    schedule = _schedule_for_specialty(specialty, doctor.username)
    duration = _slot_duration(specialty)

    if replace_existing:
        DoctorAvailability.objects.filter(doctor=doctor, end_at__gte=now).delete()

    created = 0

    for week in range(weeks_ahead):
        week_start = start_monday + timedelta(weeks=week)
        for day_cfg in schedule:
            day_date = week_start + timedelta(days=day_cfg["weekday"])
            for h1, m1, h2, m2 in day_cfg["sessions"]:
                start_dt = _make_aware(datetime.combine(day_date, time(h1, m1)))
                end_dt = _make_aware(datetime.combine(day_date, time(h2, m2)))
                if end_dt <= now:
                    continue
                if start_dt < now:
                    start_dt = now.replace(second=0, microsecond=0)
                    # Aligner sur la durée de créneau
                    minutes = duration
                    offset = int((start_dt - _make_aware(datetime.combine(day_date, time(h1, m1)))).total_seconds() // 60)
                    remainder = offset % minutes
                    if remainder:
                        start_dt += timedelta(minutes=minutes - remainder)
                if start_dt >= end_dt:
                    continue
                DoctorAvailability.objects.create(
                    doctor=doctor,
                    start_at=start_dt,
                    end_at=end_dt,
                    slot_duration_minutes=duration,
                    is_bookable=True,
                )
                created += 1

    return created


WEEKDAYS_FR = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
MONTHS_FR = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def _fr_weekday_label(dt: datetime) -> str:
    wd = WEEKDAYS_FR[dt.weekday()]
    month = MONTHS_FR[dt.month - 1]
    return f"{wd.capitalize()} {dt.day} {month}"


def summarize_agenda_blocks(blocks) -> list[dict]:
    """Regroupe les plages par jour pour l'affichage patient."""
    by_day: dict[str, dict] = {}
    for block in blocks:
        day_key = block["start_at"].strftime("%Y-%m-%d")
        if day_key not in by_day:
            by_day[day_key] = {
                "date": day_key,
                "weekday": WEEKDAYS_FR[block["start_at"].weekday()],
                "weekday_label": _fr_weekday_label(block["start_at"]),
                "sessions": [],
            }
        by_day[day_key]["sessions"].append(
            {
                "start": block["start_at"].strftime("%H:%M"),
                "end": block["end_at"].strftime("%H:%M"),
                "slot_duration_minutes": block["slot_duration_minutes"],
            }
        )
    return sorted(by_day.values(), key=lambda d: d["date"])
