import pytest
from decimal import Decimal

from billing.models import AccountingEntry, Invoice, InvoiceLine
from billing.services import update_invoice
from clinical.models import Patient


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
    from django.contrib.auth import get_user_model

    from core.models import Role, UserRole

    User = get_user_model()
    user = User.objects.create_user(
        username="testsec",
        email="sec@test.local",
        password="TestSec@2026",
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code=Role.SECRETARY))
    return user


@pytest.fixture
def sample_invoice(seeded_db, secretary_user):
    patient = Patient.objects.create(
        first_name="Paul",
        last_name="Martin",
        date_of_birth="1980-01-01",
        gender="M",
    )
    invoice = Invoice.objects.create(
        invoice_number="FAC-TEST-00001",
        patient=patient,
        status=Invoice.ISSUED,
        subtotal=Decimal("100.00"),
        insurance_amount=Decimal("0"),
        patient_amount=Decimal("100.00"),
        issued_by=secretary_user,
    )
    InvoiceLine.objects.create(
        invoice=invoice,
        description="Nuitées (2 nuits)",
        service_type="NIGHT",
        quantity=2,
        unit_price=Decimal("50.00"),
        total=Decimal("100.00"),
    )
    AccountingEntry.objects.create(
        account_code="411",
        label="Facture test",
        entry_type=AccountingEntry.DEBIT,
        amount=Decimal("100.00"),
        invoice=invoice,
        created_by=secretary_user,
    )
    AccountingEntry.objects.create(
        account_code="706",
        label="Prestations test",
        entry_type=AccountingEntry.CREDIT,
        amount=Decimal("100.00"),
        invoice=invoice,
        created_by=secretary_user,
    )
    return invoice


@pytest.mark.django_db
class TestInvoiceUpdate:
    def test_update_invoice_recalculates_totals(self, sample_invoice, secretary_user):
        invoice = update_invoice(
            sample_invoice,
            [
                {
                    "description": "Nuitées (3 nuits)",
                    "service_type": "NIGHT",
                    "quantity": "3",
                    "unit_price": "50.00",
                }
            ],
            secretary_user,
            reason="Erreur décompte nuitées",
        )
        assert invoice.subtotal == Decimal("150.00")
        assert invoice.patient_amount == Decimal("150.00")
        assert invoice.lines.count() == 1
        assert AccountingEntry.objects.filter(invoice=invoice, is_adjustment=True).exists()

    def test_update_paid_invoice_rejected(self, sample_invoice, secretary_user):
        sample_invoice.status = Invoice.PAID
        sample_invoice.paid_amount = Decimal("100.00")
        sample_invoice.save()
        with pytest.raises(ValueError, match="ne peut plus"):
            update_invoice(
                sample_invoice,
                [{"description": "Ligne", "quantity": "1", "unit_price": "10"}],
                secretary_user,
            )

    def test_patch_invoice_api(self, api_client, sample_invoice, secretary_user):
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.patch(
            f"/billing/invoices/{sample_invoice.id}/",
            json={
                "lines": [
                    {
                        "description": "Consultation urgences",
                        "service_type": "ACT",
                        "quantity": "1",
                        "unit_price": "80.00",
                    }
                ],
                "reason": "Mauvaise ligne initiale",
            },
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["subtotal"] == "80.00"
        assert r.json()["patient_amount"] == "80.00"


@pytest.mark.django_db
class TestMobileMoneyPayment:
    def test_airtel_payment_success(self, api_client, sample_invoice, secretary_user):
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.post(
            f"/billing/invoices/{sample_invoice.id}/payments/",
            json={"amount": "50.00", "method": "AIRTEL", "reference": "TXN-AIRTEL-001"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["paid_amount"] == "50.00"
        assert r.json()["balance_due"] == "50.00"
        assert r.json()["status"] == "PARTIAL"

    def test_payment_rejects_insufficient_balance(self, api_client, sample_invoice, secretary_user):
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.post(
            f"/billing/invoices/{sample_invoice.id}/payments/",
            json={"amount": "500.00", "method": "MTN", "reference": "TXN-MTN-999"},
            headers=headers,
        )
        assert r.status_code == 400
        assert "Solde insuffisant" in r.json()["detail"]

    def test_payment_rejects_card_method(self, api_client, sample_invoice, secretary_user):
        login = api_client.post("/auth/login/", json={"username": "testsec", "password": "TestSec@2026"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        r = api_client.post(
            f"/billing/invoices/{sample_invoice.id}/payments/",
            json={"amount": "10.00", "method": "CARD", "reference": "REF1234"},
            headers=headers,
        )
        assert r.status_code == 400
