from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from billing.models import AccountingEntry, Invoice, InvoiceLine, PatientInsurance, Payment, ServicePrice
from clinical.models import Hospitalization
from laboratory.models import LabOrder


def _next_invoice_number() -> str:
    year = timezone.now().year
    count = Invoice.objects.filter(invoice_number__startswith=f"FAC-{year}").count() + 1
    return f"FAC-{year}-{count:05d}"


def build_invoice_for_hospitalization(
    hospitalization: Hospitalization,
    user,
    insurance: PatientInsurance | None = None,
) -> Invoice:
    patient = hospitalization.patient
    nights = max(
        1,
        (timezone.now().date() - hospitalization.admission_date.date()).days or 1,
    )

    invoice = Invoice.objects.create(
        invoice_number=_next_invoice_number(),
        patient=patient,
        hospitalization=hospitalization,
        insurance=insurance,
        status=Invoice.ISSUED,
        issued_at=timezone.now(),
        issued_by=user,
    )

    subtotal = Decimal("0")
    night_price = ServicePrice.objects.filter(service_type=ServicePrice.NIGHT, is_active=True).first()
    if night_price:
        total = night_price.unit_price * nights
        InvoiceLine.objects.create(
            invoice=invoice,
            description=f"Nuitées ({nights} nuit(s))",
            service_type=ServicePrice.NIGHT,
            quantity=nights,
            unit_price=night_price.unit_price,
            total=total,
        )
        subtotal += total

    for lab_order in LabOrder.objects.filter(
        hospitalization=hospitalization, status=LabOrder.PUBLISHED
    ).select_related("test_type"):
        total = lab_order.test_type.price
        InvoiceLine.objects.create(
            invoice=invoice,
            description=f"Examen — {lab_order.test_type.name}",
            service_type=ServicePrice.EXAM,
            quantity=1,
            unit_price=total,
            total=total,
            reference_id=str(lab_order.id),
        )
        subtotal += total

    coverage = Decimal("0")
    if insurance:
        coverage = (subtotal * insurance.provider.coverage_rate / Decimal("100")).quantize(Decimal("0.01"))

    patient_amount = subtotal - coverage
    invoice.subtotal = subtotal
    invoice.insurance_amount = coverage
    invoice.patient_amount = patient_amount
    invoice.save()

    AccountingEntry.objects.create(
        account_code="411",
        label=f"Facture {invoice.invoice_number} — {patient}",
        entry_type=AccountingEntry.DEBIT,
        amount=patient_amount,
        invoice=invoice,
        created_by=user,
    )
    if coverage > 0:
        AccountingEntry.objects.create(
            account_code="416",
            label=f"Tiers-payant {insurance.provider.name}",
            entry_type=AccountingEntry.DEBIT,
            amount=coverage,
            invoice=invoice,
            created_by=user,
        )
    AccountingEntry.objects.create(
        account_code="706",
        label=f"Prestations hospitalières {invoice.invoice_number}",
        entry_type=AccountingEntry.CREDIT,
        amount=subtotal,
        invoice=invoice,
        created_by=user,
    )

    return invoice


def record_payment(invoice: Invoice, amount: Decimal, method: str, user, extra: dict) -> Invoice:
    allowed = {Payment.AIRTEL, Payment.MTN}
    if method not in allowed:
        raise ValueError(
            "Mode de paiement non autorisé. Seuls Airtel Money et MTN Mobile Money sont acceptés (Congo-Brazzaville)."
        )
    if amount <= 0:
        raise ValueError("Le montant doit être strictement positif.")

    if invoice.status in (Invoice.PAID, Invoice.CANCELLED):
        raise ValueError("Cette facture est déjà soldée ou annulée — paiement impossible.")

    balance = invoice.balance_due
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount > balance:
        raise ValueError(
            f"Solde insuffisant : reste à payer {balance} FCFA, montant saisi {amount} FCFA."
        )

    reference = (extra.get("reference") or "").strip()
    if len(reference) < 4:
        raise ValueError(
            "Référence mobile money obligatoire (N° de transaction ou téléphone du payeur, min. 4 caractères)."
        )

    method_label = dict(Payment.METHOD_CHOICES).get(method, method)
    Payment.objects.create(
        invoice=invoice,
        amount=amount,
        method=method,
        received_by=user,
        reference=reference,
        is_installment=extra.get("is_installment", False),
        installment_number=extra.get("installment_number"),
        declared_by_patient=extra.get("declared_by_patient", False),
    )
    invoice.paid_amount += amount
    if invoice.paid_amount >= invoice.patient_amount:
        invoice.status = Invoice.PAID
    elif invoice.paid_amount > 0:
        invoice.status = Invoice.PARTIAL
    invoice.save()

    AccountingEntry.objects.create(
        account_code="512",
        label=f"Paiement {method_label} — {invoice.invoice_number} (réf. {reference})",
        entry_type=AccountingEntry.DEBIT,
        amount=amount,
        invoice=invoice,
        created_by=user,
    )
    AccountingEntry.objects.create(
        account_code="411",
        label=f"Règlement patient — {invoice.invoice_number}",
        entry_type=AccountingEntry.CREDIT,
        amount=amount,
        invoice=invoice,
        created_by=user,
    )
    return invoice


def _recalculate_invoice_status(invoice: Invoice) -> None:
    if invoice.status == Invoice.CANCELLED:
        return
    if invoice.paid_amount >= invoice.patient_amount:
        invoice.status = Invoice.PAID
    elif invoice.paid_amount > 0:
        invoice.status = Invoice.PARTIAL
    else:
        invoice.status = Invoice.ISSUED


def _validate_invoice_line(line_data: dict) -> dict:
    description = (line_data.get("description") or "").strip()
    if len(description) < 2:
        raise ValueError("Description de ligne obligatoire (min. 2 caractères).")
    quantity = Decimal(str(line_data["quantity"]))
    unit_price = Decimal(str(line_data["unit_price"]))
    if quantity <= 0:
        raise ValueError("La quantité doit être positive.")
    if unit_price < 0:
        raise ValueError("Prix unitaire invalide.")
    total = (quantity * unit_price).quantize(Decimal("0.01"))
    return {
        "description": description,
        "service_type": line_data.get("service_type") or ServicePrice.ACT,
        "quantity": quantity,
        "unit_price": unit_price,
        "total": total,
        "reference_id": line_data.get("reference_id", ""),
    }


def _post_invoice_correction(invoice: Invoice, old: dict, user, reason: str) -> None:
    """Écritures d'ajustement comptable après correction d'une facture."""
    suffix = f" — {reason.strip()}" if reason and reason.strip() else " — correction facture"
    base_label = f"Facture {invoice.invoice_number}{suffix}"

    deltas = [
        ("706", invoice.subtotal - old["subtotal"], "Prestations"),
        ("416", invoice.insurance_amount - old["insurance_amount"], "Tiers-payant"),
        ("411", invoice.patient_amount - old["patient_amount"], "Patient"),
    ]
    for account_code, delta, label_part in deltas:
        if delta == 0:
            continue
        entry_type = AccountingEntry.CREDIT if delta > 0 else AccountingEntry.DEBIT
        if account_code in ("411", "416"):
            entry_type = AccountingEntry.DEBIT if delta > 0 else AccountingEntry.CREDIT
        AccountingEntry.objects.create(
            account_code=account_code,
            label=f"[Correction] {label_part} {base_label}",
            entry_type=entry_type,
            amount=abs(delta),
            invoice=invoice,
            created_by=user,
            is_adjustment=True,
        )


def update_invoice(invoice: Invoice, lines: list[dict], user, reason: str = "") -> Invoice:
    """Corrige les lignes d'une facture et recalcule les montants."""
    if invoice.status in (Invoice.CANCELLED, Invoice.PAID):
        raise ValueError("Cette facture ne peut plus être modifiée.")

    if not lines:
        raise ValueError("La facture doit contenir au moins une ligne.")

    validated = [_validate_invoice_line(line) for line in lines]

    old = {
        "subtotal": invoice.subtotal,
        "insurance_amount": invoice.insurance_amount,
        "patient_amount": invoice.patient_amount,
    }

    subtotal = sum(line["total"] for line in validated)

    coverage = Decimal("0")
    if invoice.insurance_id:
        insurance = PatientInsurance.objects.select_related("provider").get(pk=invoice.insurance_id)
        coverage = (subtotal * insurance.provider.coverage_rate / Decimal("100")).quantize(Decimal("0.01"))

    patient_amount = subtotal - coverage

    if invoice.paid_amount > patient_amount:
        raise ValueError(
            f"Montant patient ({patient_amount} FCFA) inférieur aux paiements déjà reçus ({invoice.paid_amount} FCFA)."
        )

    with transaction.atomic():
        invoice.lines.all().delete()
        for line in validated:
            InvoiceLine.objects.create(invoice=invoice, **line)

        invoice.subtotal = subtotal
        invoice.insurance_amount = coverage
        invoice.patient_amount = patient_amount
        _recalculate_invoice_status(invoice)
        invoice.save(
            update_fields=[
                "subtotal",
                "insurance_amount",
                "patient_amount",
                "status",
                "updated_at",
            ]
        )
        _post_invoice_correction(invoice, old, user, reason)

    return invoice
