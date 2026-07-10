import pytest
from django.contrib.auth import get_user_model

from clinical.models import Bed, Building, Department, Hospitalization, InterHospitalTransfer, PartnerHospital, Patient, Room
from core.models import Role, UserRole
from core.services.rbac import seed_roles_and_permissions

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    from django.core.cache import cache

    cache.clear()
    yield


@pytest.fixture
def api_client():
    from ninja.testing import TestClient

    from core.api.router import api

    return TestClient(api)


@pytest.fixture
def seeded_db(db):
    seed_roles_and_permissions()
    return True


@pytest.fixture
def admin_user(seeded_db):
    user = User.objects.create_user(
        username="testadmin",
        email="testadmin@test.local",
        password="TestAdmin@2026",
        is_staff=True,
        is_superuser=True,
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code=Role.ADMIN))
    return user


@pytest.fixture
def secretary_user(seeded_db):
    user = User.objects.create_user(
        username="testsec",
        email="sec@test.local",
        password="TestSec@2026",
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code=Role.SECRETARY))
    return user


@pytest.fixture
def doctor_user(seeded_db):
    user = User.objects.create_user(
        username="testdoc",
        email="doc@test.local",
        password="TestDoc@2026",
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code=Role.DOCTOR))
    return user


@pytest.fixture
def hospital_setup(seeded_db, doctor_user):
    building = Building.objects.create(code="T", name="Test Building")
    dept = Department.objects.create(building=building, code="URG", name="Urgences")
    room = Room.objects.create(department=dept, number="1")
    bed = Bed.objects.create(room=room, label="1", status=Bed.AVAILABLE)
    return {"building": building, "dept": dept, "room": room, "bed": bed, "doctor": doctor_user}


@pytest.mark.django_db
class TestHealth:
    def test_health_endpoint(self, api_client):
        response = api_client.get("/sante/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"


@pytest.mark.django_db
class TestAuth:
    def test_login_success(self, api_client, admin_user):
        response = api_client.post("/auth/login/", json={
            "username": "testadmin",
            "password": "TestAdmin@2026",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "testadmin"

    def test_login_failure(self, api_client, admin_user):
        response = api_client.post("/auth/login/", json={
            "username": "testadmin",
            "password": "wrong",
        })
        assert response.status_code == 401

    def test_me_endpoint(self, api_client, admin_user):
        login = api_client.post("/auth/login/", json={
            "username": "testadmin",
            "password": "TestAdmin@2026",
        })
        token = login.json()["access_token"]
        response = api_client.get("/users/me/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["username"] == "testadmin"


@pytest.mark.django_db
class TestAdmission:
    def test_admit_patient(self, api_client, secretary_user, doctor_user, hospital_setup):
        login = api_client.post("/auth/login/", json={
            "username": "testsec",
            "password": "TestSec@2026",
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        patient_resp = api_client.post("/clinical/patients/", json={
            "first_name": "Marie",
            "last_name": "Dupont",
            "date_of_birth": "1985-03-15",
            "gender": "F",
            "phone": "0600000000",
        }, headers=headers)
        assert patient_resp.status_code == 200
        patient_id = patient_resp.json()["id"]

        admission_resp = api_client.post("/clinical/admissions/", json={
            "patient_id": patient_id,
            "bed_id": str(hospital_setup["bed"].id),
            "referring_doctor_id": str(doctor_user.id),
            "expected_discharge_date": "2026-06-10",
            "admission_reason": "Observation cardiologique",
        }, headers=headers)
        assert admission_resp.status_code == 200
        assert admission_resp.json()["status"] == "ACTIVE"

        hospital_setup["bed"].refresh_from_db()
        assert hospital_setup["bed"].status == Bed.OCCUPIED

    def test_admission_creates_history_and_pdf(
        self, api_client, secretary_user, doctor_user, hospital_setup
    ):
        from documents.models import Document

        login = api_client.post("/auth/login/", json={
            "username": "testsec",
            "password": "TestSec@2026",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        patient = Patient.objects.create(
            first_name="Luc",
            last_name="Historique",
            date_of_birth="1990-01-01",
            gender="M",
        )
        resp = api_client.post("/clinical/admissions/", json={
            "patient_id": str(patient.id),
            "bed_id": str(hospital_setup["bed"].id),
            "referring_doctor_id": str(doctor_user.id),
            "expected_discharge_date": "2026-06-10",
            "admission_reason": "Observation",
        }, headers=headers)
        assert resp.status_code == 200
        hosp_id = resp.json()["id"]

        history = api_client.get("/clinical/patient-movements/", headers=headers)
        assert history.status_code == 200
        rows = history.json()
        assert any(r["event_type"] == "ADMISSION" and r["document_id"] for r in rows)

        docs = Document.objects.filter(patient=patient, document_type=Document.ADMISSION)
        assert docs.exists()

        patch = api_client.patch(
            f"/clinical/hospitalizations/{hosp_id}/admission-date/",
            json={"admission_date": "2026-06-01T08:30:00Z", "reason": "Erreur saisie"},
            headers=headers,
        )
        assert patch.status_code == 200

        cancel = api_client.delete(
            f"/clinical/hospitalizations/{hosp_id}/cancel-admission/?reason=Test",
            headers=headers,
        )
        assert cancel.status_code == 200
        hospital_setup["bed"].refresh_from_db()
        assert hospital_setup["bed"].status == Bed.AVAILABLE

    def test_admit_unavailable_bed(self, api_client, secretary_user, doctor_user, hospital_setup):
        bed = hospital_setup["bed"]
        bed.status = Bed.OCCUPIED
        bed.save()

        login = api_client.post("/auth/login/", json={
            "username": "testsec",
            "password": "TestSec@2026",
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        patient = Patient.objects.create(
            first_name="Paul",
            last_name="Durand",
            date_of_birth="1990-01-01",
            gender="M",
        )

        response = api_client.post("/clinical/admissions/", json={
            "patient_id": str(patient.id),
            "bed_id": str(bed.id),
            "referring_doctor_id": str(doctor_user.id),
            "expected_discharge_date": "2026-06-10",
            "admission_reason": "Test",
        }, headers=headers)
        assert response.status_code == 409


@pytest.mark.django_db
class TestInterHospitalTransfer:
    def _doctor_headers(self, api_client, doctor_user):
        login = api_client.post("/auth/login/", json={
            "username": doctor_user.username,
            "password": "TestDoc@2026",
        })
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    def _admit_patient(self, api_client, secretary_user, doctor_user, bed):
        login = api_client.post("/auth/login/", json={
            "username": "testsec",
            "password": "TestSec@2026",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        patient = Patient.objects.create(
            first_name="Alice",
            last_name="Test",
            date_of_birth="1990-01-01",
            gender="F",
        )
        resp = api_client.post("/clinical/admissions/", json={
            "patient_id": str(patient.id),
            "bed_id": str(bed.id),
            "referring_doctor_id": str(doctor_user.id),
            "expected_discharge_date": "2026-06-10",
            "admission_reason": "Transfert spécialisé requis",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_doctor_role_can_list_partner_hospitals_without_extra_perms(
        self, api_client, doctor_user, hospital_setup
    ):
        """Tout compte avec le rôle DOCTOR peut consulter les hôpitaux partenaires."""
        PartnerHospital.objects.create(
            name="CHU Test",
            city="Brazzaville",
            available_beds=2,
            total_beds=10,
        )
        headers = self._doctor_headers(api_client, doctor_user)
        me = api_client.get("/users/me/", headers=headers).json()
        assert "DOCTOR" in me["roles"]

        list_resp = api_client.get("/clinical/partner-hospitals/", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

    def _secretary_headers(self, api_client):
        login = api_client.post("/auth/login/", json={
            "username": "testsec",
            "password": "TestSec@2026",
        })
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    def test_doctor_submits_secretary_validates(
        self, api_client, secretary_user, doctor_user, hospital_setup
    ):
        partner = PartnerHospital.objects.create(
            name="CHU Test",
            city="Brazzaville",
            available_beds=2,
            total_beds=10,
        )
        doc_headers = self._doctor_headers(api_client, doctor_user)
        sec_headers = self._secretary_headers(api_client)

        hosp_id = self._admit_patient(
            api_client, secretary_user, doctor_user, hospital_setup["bed"]
        )
        create_resp = api_client.post("/clinical/inter-hospital-transfers/", json={
            "hospitalization_id": hosp_id,
            "partner_hospital_id": str(partner.id),
            "reason": "Besoin de réanimation spécialisée",
            "clinical_summary": "Instabilité hémodynamique",
        }, headers=doc_headers)
        assert create_resp.status_code == 200
        transfer_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "PENDING"

        assert api_client.post(
            f"/clinical/inter-hospital-transfers/{transfer_id}/validate/",
            headers=doc_headers,
        ).status_code == 403

        list_resp = api_client.get("/clinical/inter-hospital-transfers/", headers=sec_headers)
        assert list_resp.status_code == 200
        assert any(t["id"] == transfer_id for t in list_resp.json())

        validate_resp = api_client.post(
            f"/clinical/inter-hospital-transfers/{transfer_id}/validate/",
            headers=sec_headers,
        )
        assert validate_resp.status_code == 200
        assert validate_resp.json()["status"] == "APPROVED"

        hospital_setup["bed"].refresh_from_db()
        assert hospital_setup["bed"].status == Bed.AVAILABLE
        hosp = Hospitalization.objects.get(pk=hosp_id)
        assert hosp.status == Hospitalization.TRANSFERRED

    def test_list_partner_hospitals_and_validate_transfer(
        self, api_client, secretary_user, doctor_user, hospital_setup
    ):
        partner = PartnerHospital.objects.create(
            name="CHU Test",
            city="Brazzaville",
            available_beds=2,
            total_beds=10,
        )
        headers = self._doctor_headers(api_client, doctor_user)
        list_resp = api_client.get("/clinical/partner-hospitals/", headers=headers)
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert len(data) == 1
        assert data[0]["can_receive"] is True

        cities_resp = api_client.get("/clinical/partner-hospitals/cities/", headers=headers)
        assert cities_resp.status_code == 200
        assert "Brazzaville" in cities_resp.json()

        hosp_id = self._admit_patient(
            api_client, secretary_user, doctor_user, hospital_setup["bed"]
        )
        create_resp = api_client.post("/clinical/inter-hospital-transfers/", json={
            "hospitalization_id": hosp_id,
            "partner_hospital_id": str(partner.id),
            "reason": "Besoin de réanimation spécialisée",
            "clinical_summary": "Instabilité hémodynamique",
        }, headers=headers)
        assert create_resp.status_code == 200
        transfer_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "PENDING"

        sec_headers = self._secretary_headers(api_client)
        validate_resp = api_client.post(
            f"/clinical/inter-hospital-transfers/{transfer_id}/validate/",
            headers=sec_headers,
        )
        assert validate_resp.status_code == 200
        assert validate_resp.json()["status"] == "APPROVED"

        hospital_setup["bed"].refresh_from_db()
        assert hospital_setup["bed"].status == Bed.AVAILABLE
        hosp = Hospitalization.objects.get(pk=hosp_id)
        assert hosp.status == Hospitalization.TRANSFERRED
        partner.refresh_from_db()
        assert partner.available_beds == 1

    def test_cannot_transfer_to_full_hospital(
        self, api_client, secretary_user, doctor_user, hospital_setup
    ):
        partner = PartnerHospital.objects.create(
            name="Hôpital saturé",
            city="Pointe-Noire",
            available_beds=0,
            total_beds=5,
        )
        headers = self._doctor_headers(api_client, doctor_user)
        hosp_id = self._admit_patient(
            api_client, secretary_user, doctor_user, hospital_setup["bed"]
        )
        resp = api_client.post("/clinical/inter-hospital-transfers/", json={
            "hospitalization_id": hosp_id,
            "partner_hospital_id": str(partner.id),
            "reason": "Saturation service local — transfert nécessaire",
        }, headers=headers)
        assert resp.status_code == 409

    def test_rejects_invalid_transfer_reason(
        self, api_client, secretary_user, doctor_user, hospital_setup
    ):
        partner = PartnerHospital.objects.create(
            name="CHU Test",
            city="Brazzaville",
            available_beds=2,
            total_beds=10,
        )
        headers = self._doctor_headers(api_client, doctor_user)
        hosp_id = self._admit_patient(
            api_client, secretary_user, doctor_user, hospital_setup["bed"]
        )
        resp = api_client.post("/clinical/inter-hospital-transfers/", json={
            "hospitalization_id": hosp_id,
            "partner_hospital_id": str(partner.id),
            "reason": "1234567890",
        }, headers=headers)
        assert resp.status_code == 400
        assert "Motif" in resp.json()["detail"]

    def test_transfer_patient_search_shows_registered_and_hospitalized(
        self, api_client, secretary_user, doctor_user, hospital_setup
    ):
        Patient.objects.create(
            first_name="Jean",
            last_name="NonAdmis",
            date_of_birth="1990-01-01",
            gender="M",
        )
        headers = self._doctor_headers(api_client, doctor_user)
        resp = api_client.get(
            "/clinical/transfers/patient-search/?search=NonAdmis",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(not row["is_hospitalized"] for row in data)


@pytest.fixture
def admin_api_client():
    from ninja.testing import TestClient

    from administration.router import admin_api

    return TestClient(admin_api)


@pytest.mark.django_db
class TestAdminPanel:
    def test_admin_stats(self, admin_api_client, admin_user):
        login = admin_api_client.post("/auth/login/", json={
            "username": "testadmin",
            "password": "TestAdmin@2026",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = admin_api_client.get("/stats/", headers=headers)
        assert r.status_code == 200
        assert "users_total" in r.json()
        assert "users_online" in r.json()

    def test_online_users(self, admin_api_client, admin_user, secretary_user):
        admin_login = admin_api_client.post("/auth/login/", json={
            "username": "testadmin",
            "password": "TestAdmin@2026",
        })
        sec_login = admin_api_client.post("/auth/login/", json={
            "username": "testsec",
            "password": "TestSec@2026",
        })
        assert admin_login.status_code == 200
        assert sec_login.status_code == 200

        headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        r = admin_api_client.get("/online-users/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        usernames = {u["username"] for u in data}
        assert "testadmin" in usernames
        assert "testsec" in usernames
        admin_row = next(u for u in data if u["username"] == "testadmin")
        assert "ADMIN" in admin_row["roles"]
        assert "Administrateur" in admin_row["role_labels"]

    def test_create_user_via_admin(self, admin_api_client, admin_user):
        login = admin_api_client.post("/auth/login/", json={
            "username": "testadmin",
            "password": "TestAdmin@2026",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = admin_api_client.post("/users/", json={
            "username": "newuser",
            "email": "new@test.local",
            "password": "NewUser@2026",
            "first_name": "New",
            "last_name": "User",
            "role_codes": ["SECRETARY"],
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["username"] == "newuser"

    def test_admin_spa_route(self, admin_user):
        from django.test import Client

        client = Client()
        response = client.get("/admin/")
        assert response.status_code in (200, 404)

    def test_secretary_denied_admin_api(self, admin_api_client, secretary_user):
        login = admin_api_client.post("/auth/login/", json={
            "username": "testsec",
            "password": "TestSec@2026",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = admin_api_client.get("/stats/", headers=headers)
        assert r.status_code == 403

    def test_infrastructure_crud(self, admin_api_client, admin_user):
        login = admin_api_client.post("/auth/login/", json={
            "username": "testadmin",
            "password": "TestAdmin@2026",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        b = admin_api_client.post("/infrastructure/buildings/", json={
            "name": "Annexe Test",
            "code": "ANN-T",
            "address": "1 rue Test",
        }, headers=headers)
        assert b.status_code == 200
        building_id = b.json()["id"]
        d = admin_api_client.post("/infrastructure/departments/", json={
            "building_id": building_id,
            "name": "Urgences Test",
            "code": "URG-T",
        }, headers=headers)
        assert d.status_code == 200
        dept_id = d.json()["id"]
        room = admin_api_client.post("/infrastructure/rooms/", json={
            "department_id": dept_id,
            "number": "101",
            "floor": 1,
        }, headers=headers)
        assert room.status_code == 200
        bed = admin_api_client.post("/infrastructure/beds/", json={
            "room_id": room.json()["id"],
            "label": "A",
            "status": "AVAILABLE",
        }, headers=headers)
        assert bed.status_code == 200
        patch_b = admin_api_client.patch(f"/infrastructure/buildings/{building_id}/", json={
            "name": "Annexe Test Modifiée",
        }, headers=headers)
        assert patch_b.status_code == 200
        assert patch_b.json()["name"] == "Annexe Test Modifiée"
        delete_b = admin_api_client.delete(f"/infrastructure/buildings/{building_id}/", headers=headers)
        assert delete_b.status_code == 200

    def test_delete_building_admin_only(self, admin_api_client, admin_user, secretary_user):
        from core.models import Permission, Role, RolePermission

        seed_roles_and_permissions()
        manage_perm = Permission.objects.get(codename="core.manage_users")
        sec_role = Role.objects.get(code=Role.SECRETARY)
        RolePermission.objects.get_or_create(role=sec_role, permission=manage_perm)

        login = admin_api_client.post("/auth/login/", json={
            "username": "testadmin",
            "password": "TestAdmin@2026",
        })
        admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        b = admin_api_client.post("/infrastructure/buildings/", json={
            "name": "Bloc Sec",
            "code": "SEC-DEL",
            "address": "",
        }, headers=admin_headers)
        assert b.status_code == 200
        building_id = b.json()["id"]

        sec_login = admin_api_client.post("/auth/login/", json={
            "username": "testsec",
            "password": "TestSec@2026",
        })
        sec_headers = {"Authorization": f"Bearer {sec_login.json()['access_token']}"}
        denied = admin_api_client.delete(f"/infrastructure/buildings/{building_id}/", headers=sec_headers)
        assert denied.status_code == 403

        allowed = admin_api_client.delete(f"/infrastructure/buildings/{building_id}/", headers=admin_headers)
        assert allowed.status_code == 200

    def test_list_roles(self, admin_api_client, admin_user):
        login = admin_api_client.post("/auth/login/", json={
            "username": "testadmin",
            "password": "TestAdmin@2026",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = admin_api_client.get("/roles/", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1
        assert "code" in r.json()[0]
        assert "permissions" in r.json()[0]


@pytest.mark.django_db
class TestDjangoAdmin:
    def test_admin_login_page(self, admin_user):
        from django.test import Client

        client = Client()
        response = client.get("/admin/login/")
        assert response.status_code in (200, 404)

    def test_admin_index(self, admin_user):
        from django.test import Client

        client = Client()
        response = client.get("/admin/")
        assert response.status_code == 200

    def test_old_django_admin_removed(self):
        from django.test import Client

        client = Client()
        response = client.get("/admin/login/")
        assert response.status_code == 200
        body = b"".join(response.streaming_content)
        assert b"Connexion admin" in body or b"id=\"app\"" in body


@pytest.fixture
def biologist_user(seeded_db):
    user = User.objects.create_user(
        username="testbio",
        email="bio@test.local",
        password="TestBio@2026",
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code=Role.BIOLOGIST))
    return user


@pytest.mark.django_db
class TestLaboratory:
    def test_lab_workflow(self, api_client, doctor_user, biologist_user, hospital_setup):
        from laboratory.models import LabTestType

        patient = Patient.objects.create(
            first_name="Lab", last_name="Test", date_of_birth="1980-01-01", gender="M"
        )
        test = LabTestType.objects.create(code="TST", name="Test Exam", price="10.00")

        doc_login = api_client.post("/auth/login/", json={"username": "testdoc", "password": "TestDoc@2026"})
        doc_headers = {"Authorization": f"Bearer {doc_login.json()['access_token']}"}

        order_resp = api_client.post("/laboratory/orders/", json={
            "patient_id": str(patient.id),
            "test_type_id": str(test.id),
        }, headers=doc_headers)
        assert order_resp.status_code == 200
        order_id = order_resp.json()["id"]

        bio_login = api_client.post("/auth/login/", json={"username": "testbio", "password": "TestBio@2026"})
        bio_headers = {"Authorization": f"Bearer {bio_login.json()['access_token']}"}

        for step in ("collect", "assign"):
            r = api_client.post(f"/laboratory/orders/{order_id}/{step}/", headers=bio_headers)
            assert r.status_code == 200

        r = api_client.post(f"/laboratory/orders/{order_id}/results/", json={
            "result_data": {"hb": "14.2"},
            "interpretation": "Normal",
        }, headers=bio_headers)
        assert r.status_code == 200

        r = api_client.post(f"/laboratory/orders/{order_id}/validate/", headers=bio_headers)
        assert r.status_code == 200

        r = api_client.post(f"/laboratory/orders/{order_id}/publish/", headers=bio_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "PUBLISHED"


@pytest.mark.django_db
class TestDashboard:
    def test_kpis(self, api_client, admin_user):
        login = api_client.post("/auth/login/", json={"username": "testadmin", "password": "TestAdmin@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.get("/dashboard/kpis/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "occupancy_rate" in data
        assert "pending_lab_exams" in data


@pytest.fixture
def fixed_otp(monkeypatch):
    monkeypatch.setattr("core.services.email_otp._generate_code", lambda: "654321")


def _verify_patient(api_client, email, password):
    return api_client.post("/auth/register/patient/verify-otp/", json={
        "email": email,
        "code": "654321",
        "password": password,
    })


@pytest.mark.django_db
class TestPatientRegistration:
    def test_register_patient_success(self, api_client, seeded_db, fixed_otp):
        payload = {
            "email": "nouveau.patient@test.local",
            "password": "PatientTest@2026",
            "first_name": "Jean",
            "last_name": "Dupont",
            "date_of_birth": "1990-05-15",
            "gender": "M",
            "phone": "0600000000",
        }
        r = api_client.post("/auth/register/patient/", json=payload)
        assert r.status_code == 200
        assert "otp_sent" in r.json()
        v = _verify_patient(api_client, payload["email"], payload["password"])
        assert v.status_code == 200, v.json()
        assert "access_token" in v.json()
        assert "PATIENT" in v.json()["user"]["roles"]
        assert Patient.objects.filter(email="nouveau.patient@test.local").exists()

    def test_register_duplicate_email_rejected(self, api_client, seeded_db, fixed_otp):
        payload = {
            "email": "dup@test.local",
            "password": "PatientTest@2026",
            "first_name": "Alice",
            "last_name": "Bernard",
            "date_of_birth": "1990-01-01",
            "gender": "F",
        }
        assert api_client.post("/auth/register/patient/", json=payload).status_code == 200
        _verify_patient(api_client, payload["email"], payload["password"])
        r = api_client.post("/auth/register/patient/", json={**payload, "first_name": "Claire"})
        assert r.status_code == 400
        assert "email" in r.json()["detail"].lower()

    def test_register_links_existing_patient_dossier(self, api_client, seeded_db, fixed_otp):
        Patient.objects.create(
            first_name="Marie",
            last_name="Curie",
            date_of_birth="1985-03-20",
            gender="F",
            email="marie.curie@test.local",
        )
        payload = {
            "email": "marie.curie@test.local",
            "password": "PatientTest@2026",
            "first_name": "Marie",
            "last_name": "Curie",
            "date_of_birth": "1985-03-20",
            "gender": "F",
        }
        assert api_client.post("/auth/register/patient/", json=payload).status_code == 200
        _verify_patient(api_client, payload["email"], payload["password"])
        patient = Patient.objects.get(email="marie.curie@test.local")
        assert patient.user_id is not None

    def test_login_with_email(self, api_client, seeded_db, fixed_otp):
        payload = {
            "email": "login.email@test.local",
            "password": "PatientTest@2026",
            "first_name": "Test",
            "last_name": "Email",
            "date_of_birth": "1992-01-01",
            "gender": "M",
        }
        api_client.post("/auth/register/patient/", json=payload)
        _verify_patient(api_client, payload["email"], payload["password"])
        r = api_client.post("/auth/login/", json={
            "username": "login.email@test.local",
            "password": "PatientTest@2026",
        })
        assert r.status_code == 200

    def test_login_blocked_before_email_verified(self, api_client, seeded_db, fixed_otp):
        payload = {
            "email": "unverified@test.local",
            "password": "PatientTest@2026",
            "first_name": "Non",
            "last_name": "Verifie",
            "date_of_birth": "1992-01-01",
            "gender": "M",
        }
        api_client.post("/auth/register/patient/", json=payload)
        r = api_client.post("/auth/login/", json={"username": payload["email"], "password": payload["password"]})
        assert r.status_code == 401
        assert "vérifi" in r.json()["detail"].lower()


@pytest.mark.django_db
class TestPatientApi:
    def test_list_patients_null_email(self, api_client, secretary_user, seeded_db):
        Patient.objects.create(
            first_name="Sans",
            last_name="Email",
            date_of_birth="1990-01-01",
            gender="M",
            email=None,
        )
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.get("/clinical/patients/", headers=headers)
        assert r.status_code == 200
        assert all(isinstance(p["email"], str) for p in r.json())

    def test_create_patient_rejects_digits_in_name(self, api_client, secretary_user, seeded_db):
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.post(
            "/clinical/patients/",
            json={
                "first_name": "Jean123",
                "last_name": "Dupont",
                "date_of_birth": "1990-01-01",
                "gender": "M",
            },
            headers=headers,
        )
        assert r.status_code == 400
        assert "chiffres" in r.json()["detail"].lower()

    def test_update_and_archive_patient(self, api_client, secretary_user, seeded_db):
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        created = api_client.post(
            "/clinical/patients/",
            json={
                "first_name": "Marie",
                "last_name": "Test",
                "date_of_birth": "1985-05-05",
                "gender": "F",
                "phone": "0612345678",
            },
            headers=headers,
        )
        assert created.status_code == 200
        pid = created.json()["id"]

        updated = api_client.patch(
            f"/clinical/patients/{pid}/",
            json={"phone": "0698765432"},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["phone"] == "0698765432"

        archived = api_client.delete(f"/clinical/patients/{pid}/", headers=headers)
        assert archived.status_code == 200

        listing = api_client.get("/clinical/patients/", headers=headers)
        assert all(p["id"] != pid for p in listing.json())


class TestPatientValidation:
    def test_register_rejects_digits_in_name(self, api_client, seeded_db):
        r = api_client.post("/auth/register/patient/", json={
            "email": "bad.name@test.local",
            "password": "Patient@2026",
            "first_name": "A1ice",
            "last_name": "Moreau",
            "date_of_birth": "1990-01-01",
            "gender": "F",
        })
        assert r.status_code == 400
        assert "chiffres" in r.json()["detail"].lower()

