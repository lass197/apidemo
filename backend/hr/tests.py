import pytest
from django.utils import timezone
from datetime import timedelta

from clinical.models import Patient
from hr.models import Appointment, DoctorAvailability, DoctorProfile, HospitalService
from core.models import Role, User, UserRole


@pytest.fixture
def api_client():
    from ninja.testing import TestClient
    from core.api.router import api
    return TestClient(api)


@pytest.fixture
def seeded_db(db):
    from core.services.rbac import seed_roles_and_permissions
    seed_roles_and_permissions()
    return True


@pytest.fixture
def secretary_user(seeded_db):
    user = User.objects.create_user(
        username="testsec",
        email="sec@test.local",
        password="TestSec@2026",
        email_verified=True,
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code=Role.SECRETARY))
    return user


@pytest.fixture
def doctor_user(seeded_db):
    user = User.objects.create_user(
        username="testdoc",
        email="doc@test.local",
        password="TestDoc@2026",
        email_verified=True,
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code=Role.DOCTOR))
    return user


@pytest.fixture
def patient_user(seeded_db):
    user = User.objects.create_user(
        username="testpatient",
        email="patient@test.local",
        password="Patient@2026",
        email_verified=True,
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code=Role.PATIENT))
    patient = Patient.objects.create(
        user=user,
        first_name="Test",
        last_name="Patient",
        date_of_birth="1990-01-01",
        gender="M",
        email="patient@test.local",
    )
    return user, patient


@pytest.mark.django_db
class TestAppointmentWorkflow:
    def test_book_creates_pending(self, api_client, doctor_user, patient_user):
        user, patient = patient_user
        now = timezone.now()
        DoctorAvailability.objects.create(
            doctor=doctor_user,
            start_at=now,
            end_at=now + timedelta(days=7),
            slot_duration_minutes=30,
        )
        login = api_client.post("/auth/login/", json={"username": user.username, "password": "Patient@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        slot = now + timedelta(days=1)
        slot = slot.replace(hour=10, minute=0, second=0, microsecond=0)
        r = api_client.post("/hr/appointments/", json={
            "patient_id": str(patient.id),
            "doctor_id": str(doctor_user.id),
            "scheduled_at": slot.isoformat(),
            "reason": "Consultation",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "PENDING"

    def test_secretary_confirms_appointment(self, api_client, secretary_user, doctor_user, patient_user):
        user, patient = patient_user
        slot = timezone.now() + timedelta(days=2)
        slot = slot.replace(hour=10, minute=0, second=0, microsecond=0)
        DoctorAvailability.objects.create(
            doctor=doctor_user,
            start_at=slot - timedelta(hours=1),
            end_at=slot + timedelta(hours=4),
            slot_duration_minutes=30,
        )
        appt = Appointment.objects.create(
            patient=patient,
            doctor=doctor_user,
            scheduled_at=slot,
            status=Appointment.PENDING,
        )
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.patch(f"/hr/appointments/{appt.id}/review/", json={
            "action": "confirm",
            "staff_notes": "Apportez votre carte vitale",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "CONFIRMED"

    def test_secretary_cannot_confirm_outside_agenda(self, api_client, secretary_user, doctor_user, patient_user):
        _, patient = patient_user
        slot = timezone.now() + timedelta(days=2)
        slot = slot.replace(hour=10, minute=0, second=0, microsecond=0)
        appt = Appointment.objects.create(
            patient=patient,
            doctor=doctor_user,
            scheduled_at=slot,
            status=Appointment.PENDING,
        )
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.patch(f"/hr/appointments/{appt.id}/review/", json={
            "action": "confirm",
        }, headers=headers)
        assert r.status_code == 409
        assert "agenda" in r.json()["detail"].lower()

    def test_secretary_updates_appointment(self, api_client, secretary_user, doctor_user, patient_user):
        _, patient = patient_user
        new_slot = timezone.now() + timedelta(days=3)
        new_slot = new_slot.replace(hour=11, minute=0, second=0, microsecond=0)
        DoctorAvailability.objects.create(
            doctor=doctor_user,
            start_at=new_slot - timedelta(hours=1),
            end_at=new_slot + timedelta(hours=4),
            slot_duration_minutes=30,
        )
        appt = Appointment.objects.create(
            patient=patient,
            doctor=doctor_user,
            scheduled_at=timezone.now() + timedelta(days=2),
            status=Appointment.CONFIRMED,
        )
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.patch(f"/hr/appointments/{appt.id}/", json={
            "scheduled_at": new_slot.isoformat(),
            "staff_notes": "Salle 2",
            "status": "CONFIRMED",
        }, headers=headers)
        assert r.status_code == 200
        assert "Salle 2" in r.json()["staff_notes"]

    def test_cancel_sends_email_path(self, api_client, secretary_user, doctor_user, patient_user, monkeypatch):
        sent = []

        def fake_notify(appt, **kwargs):
            sent.append(("cancel", appt.patient.email))

        monkeypatch.setattr("hr.api.notify_patient_appointment_cancelled", fake_notify)
        _, patient = patient_user
        appt = Appointment.objects.create(
            patient=patient,
            doctor=doctor_user,
            scheduled_at=timezone.now() + timedelta(days=2),
            status=Appointment.CONFIRMED,
        )
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.delete(f"/hr/appointments/{appt.id}/", headers=headers)
        assert r.status_code == 200
        assert len(sent) == 1

    def test_doctors_directory_lists_specialty_and_slots(self, api_client, doctor_user, patient_user):
        from hr.models import DoctorProfile

        user, patient = patient_user
        DoctorProfile.objects.create(
            user=doctor_user,
            specialty="Cardiologie",
            department_name="Cardiologie",
        )
        now = timezone.now()
        DoctorAvailability.objects.create(
            doctor=doctor_user,
            start_at=now,
            end_at=now + timedelta(days=3),
            slot_duration_minutes=30,
        )
        login = api_client.post("/auth/login/", json={"username": user.username, "password": "Patient@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.get("/hr/doctors/directory/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        cardio = next((d for d in data if d["specialty"] == "Cardiologie"), None)
        assert cardio is not None
        assert cardio["available_slots_count"] > 0
        assert len(cardio["agenda"]) >= 1

    def test_doctor_lists_own_appointments_with_email(self, api_client, doctor_user, patient_user):
        user, patient = patient_user
        now = timezone.now()
        DoctorAvailability.objects.create(
            doctor=doctor_user,
            start_at=now,
            end_at=now + timedelta(days=3),
            slot_duration_minutes=30,
        )
        appt = Appointment.objects.create(
            patient=patient,
            doctor=doctor_user,
            scheduled_at=now + timedelta(days=1),
            status=Appointment.CONFIRMED,
        )
        login = api_client.post("/auth/login/", json={"username": "testdoc", "password": "TestDoc@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.get("/hr/appointments/mine/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        row = next((x for x in data if x["id"] == str(appt.id)), None)
        assert row is not None
        assert row["patient_email"] == "patient@test.local"
        pats = api_client.get("/hr/appointments/mine/patients/", headers=headers)
        assert pats.status_code == 200
        assert any(p["email"] == "patient@test.local" for p in pats.json())
