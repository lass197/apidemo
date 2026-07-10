"""
Tests RBAC ordonnés par niveau de privilège (ADMIN → PATIENT).
Exécution : pytest core/test_privileges.py -v
"""
import pytest
from django.contrib.auth import get_user_model

from core.models import Role, UserRole
from core.services.rbac import ROLE_PERMISSIONS, seed_roles_and_permissions

User = get_user_model()

PRIVILEGE_ORDER = [
    ("testadmin", Role.ADMIN, "TestAdmin@2026"),
    ("testsec", Role.SECRETARY, "TestSec@2026"),
    ("testacc", Role.ACCOUNTANT, "TestAcc@2026"),
    ("testdoc", Role.DOCTOR, "TestDoc@2026"),
    ("testnurse", Role.NURSE, "TestNurse@2026"),
    ("testbio", Role.BIOLOGIST, "TestBio@2026"),
    ("testpharm", Role.PHARMACIST, "TestPharm@2026"),
    ("testpatient", Role.PATIENT, "TestPatient@2026"),
]


@pytest.fixture
def api_client():
    from ninja.testing import TestClient
    from core.api.router import api
    return TestClient(api)


@pytest.fixture
def admin_api_client():
    from ninja.testing import TestClient
    from administration.router import admin_api
    return TestClient(admin_api)


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    from django.core.cache import cache
    cache.clear()
    yield


@pytest.fixture
def seeded_privileges(db):
    seed_roles_and_permissions()
    for username, role_code, password in PRIVILEGE_ORDER:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@test.local"},
        )
        if created:
            user.set_password(password)
            user.save()
        if role_code == Role.PATIENT and not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
        UserRole.objects.filter(user=user).delete()
        UserRole.objects.create(user=user, role=Role.objects.get(code=role_code))
    return True


def _login(api_client, username, password):
    r = api_client.post("/auth/login/", json={"username": username, "password": password})
    assert r.status_code == 200, r.content
    data = r.json()
    assert "permissions" in data["user"]
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.django_db
class TestPrivilegeOrder:
    @pytest.mark.parametrize("username,role_code,password", PRIVILEGE_ORDER)
    def test_login_returns_expected_permissions(self, api_client, seeded_privileges, username, role_code, password):
        r = api_client.post("/auth/login/", json={"username": username, "password": password})
        assert r.status_code == 200
        perms = set(r.json()["user"]["permissions"])
        expected = set(ROLE_PERMISSIONS[role_code])
        if role_code == Role.ADMIN:
            assert "core.manage_users" in perms
            assert "billing.adjust" in perms
        else:
            assert perms == expected

    def test_admin_only_manage_users(self, admin_api_client, seeded_privileges):
        headers = _login(admin_api_client, "testadmin", "TestAdmin@2026")
        assert admin_api_client.get("/stats/", headers=headers).status_code == 200
        sec_headers = _login(admin_api_client, "testsec", "TestSec@2026")
        assert admin_api_client.get("/stats/", headers=sec_headers).status_code == 403

    def test_secretary_can_admit_not_transfer(self, api_client, seeded_privileges):
        sec = _login(api_client, "testsec", "TestSec@2026")
        doc = _login(api_client, "testdoc", "TestDoc@2026")
        assert "clinical.admit_patient" in api_client.get("/users/me/", headers=sec).json()["permissions"]
        assert "clinical.transfer" not in api_client.get("/users/me/", headers=sec).json()["permissions"]
        assert "clinical.validate_transfer" in api_client.get("/users/me/", headers=sec).json()["permissions"]
        assert "clinical.transfer" in api_client.get("/users/me/", headers=doc).json()["permissions"]
        assert "clinical.validate_transfer" not in api_client.get("/users/me/", headers=doc).json()["permissions"]
        assert "clinical.view_partner_hospitals" in api_client.get("/users/me/", headers=doc).json()["permissions"]
        assert api_client.get("/clinical/partner-hospitals/", headers=sec).status_code == 403
        assert api_client.get("/clinical/partner-hospitals/", headers=doc).status_code == 200
        assert api_client.get("/clinical/beds/available/", headers=doc).status_code == 200
        assert api_client.get("/clinical/beds/available/", headers=sec).status_code == 200

    def test_biologist_has_lab_not_order(self, api_client, seeded_privileges):
        bio = _login(api_client, "testbio", "TestBio@2026")
        perms = api_client.get("/users/me/", headers=bio).json()["permissions"]
        assert "lab.validate_results" in perms
        assert "lab.order" not in perms

    def test_patient_minimal_permissions(self, api_client, seeded_privileges):
        pat = _login(api_client, "testpatient", "TestPatient@2026")
        perms = set(api_client.get("/users/me/", headers=pat).json()["permissions"])
        assert perms == set(ROLE_PERMISSIONS[Role.PATIENT])

    def test_billing_adjust_admin_and_accountant(self, api_client, seeded_privileges):
        from uuid import uuid4
        admin_h = _login(api_client, "testadmin", "TestAdmin@2026")
        acc_h = _login(api_client, "testacc", "TestAcc@2026")
        sec_h = _login(api_client, "testsec", "TestSec@2026")
        payload = {
            "invoice_id": str(uuid4()),
            "account_code": "471",
            "label": "Test",
            "entry_type": "DEBIT",
            "amount": "10.00",
        }
        assert api_client.post("/billing/accounting/adjustments/", json=payload, headers=admin_h).status_code == 404
        assert api_client.post("/billing/accounting/adjustments/", json=payload, headers=acc_h).status_code == 404
        assert api_client.post("/billing/accounting/adjustments/", json=payload, headers=sec_h).status_code == 403

    def test_accountant_can_view_finance_not_create_invoice(self, api_client, seeded_privileges):
        acc = _login(api_client, "testacc", "TestAcc@2026")
        perms = api_client.get("/users/me/", headers=acc).json()["permissions"]
        assert "billing.view_finance" in perms
        assert "billing.adjust" in perms
        assert "billing.create_invoice" not in perms
        assert api_client.get("/billing/invoices/", headers=acc).status_code == 200
        assert api_client.get("/billing/accounting/journal/", headers=acc).status_code == 200
