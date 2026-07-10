from decimal import Decimal

from django.db import transaction

from billing.models import Invoice, InvoicePatientDeclaration, Payment
from billing.services import record_payment
from core.services.validators import validate_phone


def _latest_declaration(invoice: Invoice) -> InvoicePatientDeclaration | None:
    return invoice.patient_declarations.order_by("-created_at").first()


def declaration_out(decl: InvoicePatientDeclaration | None) -> dict | None:
    if not decl:
        return None
    return {
        "id": str(decl.id),
        "status": decl.status,
        "phone_number": decl.phone_number,
        "method": decl.method,
        "transaction_reference": decl.transaction_reference,
        "amount_claimed": f"{decl.amount_claimed:.2f}",
        "declared_at": decl.created_at.isoformat(),
    }


def declare_patient_payment(
    invoice: Invoice,
    *,
    user,
    phone_number: str,
    method: str,
    declaration: str,
    transaction_reference: str = "",
    amount: Decimal | None = None,
) -> tuple[InvoicePatientDeclaration, Invoice]:
    if declaration not in (InvoicePatientDeclaration.PAID, InvoicePatientDeclaration.UNPAID):
        raise ValueError("Statut invalide : PAID ou UNPAID.")

    if method not in (Payment.AIRTEL, Payment.MTN):
        raise ValueError("Choisissez Airtel Money ou MTN Mobile Money.")

    phone = validate_phone(phone_number.strip(), required=True)
    reference = (transaction_reference or phone).strip()

    if invoice.status == Invoice.CANCELLED:
        raise ValueError("Cette facture est annulée.")

    pay_amount = Decimal("0")

    with transaction.atomic():
        if declaration == InvoicePatientDeclaration.PAID:
            if invoice.status == Invoice.PAID:
                raise ValueError("Cette facture est déjà marquée comme payée.")
            pay_amount = amount if amount is not None else invoice.balance_due
            pay_amount = Decimal(str(pay_amount)).quantize(Decimal("0.01"))
            if pay_amount <= 0:
                raise ValueError("Montant invalide ou facture déjà soldée.")
            record_payment(
                invoice,
                pay_amount,
                method,
                user,
                {
                    "reference": reference,
                    "declared_by_patient": True,
                },
            )
            invoice.refresh_from_db()

        decl = InvoicePatientDeclaration.objects.create(
            invoice=invoice,
            patient=invoice.patient,
            phone_number=phone,
            method=method,
            transaction_reference=reference,
            status=declaration,
            amount_claimed=pay_amount,
            declared_by=user,
        )

    return decl, invoice
