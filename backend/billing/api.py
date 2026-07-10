from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from billing.models import AccountingEntry, Invoice, InvoiceLine, InvoicePatientDeclaration, PatientInsurance, Payment, ServicePrice
from billing.patient_payment import declaration_out, declare_patient_payment
from billing.services import build_invoice_for_hospitalization, record_payment, update_invoice
from clinical.models import Hospitalization, Patient
from core.auth import jwt_auth
from core.permissions import require_permission
from core.services.audit import log_audit
from core.services.dashboard import invalidate_dashboard_cache
from core.services.pdf import generate_invoice_pdf
from core.services.storage import store_encrypted_file
from documents.models import Document

router = Router(tags=["Facturation"])


class ServicePriceOut(Schema):
    id: UUID
    code: str
    label: str
    service_type: str
    unit_price: str


class InvoiceOut(Schema):
    id: UUID
    invoice_number: str
    patient_id: UUID
    patient_name: str = ""
    hospitalization_id: UUID | None = None
    status: str
    subtotal: str
    insurance_amount: str
    patient_amount: str
    paid_amount: str
    balance_due: str
    patient_declaration: dict | None = None


class PatientPaymentDeclareIn(Schema):
    phone_number: str
    method: str
    declaration: str
    transaction_reference: str = ""
    amount: Decimal | None = None


class InvoiceLineOut(Schema):
    id: UUID
    description: str
    service_type: str
    quantity: str
    unit_price: str
    total: str


class InvoiceLineIn(Schema):
    description: str
    service_type: str = "ACT"
    quantity: Decimal
    unit_price: Decimal


class InvoiceUpdateIn(Schema):
    lines: list[InvoiceLineIn]
    reason: str = ""


class PaymentIn(Schema):
    amount: Decimal
    method: str
    reference: str = ""
    is_installment: bool = False
    installment_number: int | None = None


class AccountingEntryOut(Schema):
    id: UUID
    entry_date: str
    account_code: str
    label: str
    entry_type: str
    amount: str
    is_adjustment: bool


class AdjustmentIn(Schema):
    invoice_id: UUID
    account_code: str
    label: str
    entry_type: str
    amount: Decimal
    reason: str = ""


@router.get("/prices/", response=list[ServicePriceOut], auth=jwt_auth)
@require_permission("billing.view_finance")
def list_prices(request):
    return [
        {
            "id": p.id,
            "code": p.code,
            "label": p.label,
            "service_type": p.service_type,
            "unit_price": str(p.unit_price),
        }
        for p in ServicePrice.objects.filter(is_active=True)
    ]


@router.post("/invoices/from-hospitalization/{hospitalization_id}/", response=InvoiceOut, auth=jwt_auth)
@require_permission("billing.create_invoice")
def create_invoice_from_hospitalization(request, hospitalization_id: UUID):
    try:
        hosp = Hospitalization.objects.select_related("patient").get(pk=hospitalization_id)
    except Hospitalization.DoesNotExist as exc:
        raise HttpError(404, "Hospitalisation introuvable.") from exc

    insurance = PatientInsurance.objects.filter(
        patient=hosp.patient, is_primary=True
    ).select_related("provider").first()

    invoice = build_invoice_for_hospitalization(hosp, request.auth, insurance)
    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="Invoice",
        resource_id=str(invoice.id),
    )
    return _invoice_out(invoice)


def _invoice_out(inv: Invoice, *, include_declaration: bool = True) -> dict:
    balance = inv.balance_due
    latest = None
    if include_declaration:
        latest = inv.patient_declarations.order_by("-created_at").first()
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "patient_id": inv.patient_id,
        "patient_name": str(inv.patient) if inv.patient_id else "",
        "hospitalization_id": inv.hospitalization_id,
        "status": inv.status,
        "subtotal": f"{inv.subtotal:.2f}",
        "insurance_amount": f"{inv.insurance_amount:.2f}",
        "patient_amount": f"{inv.patient_amount:.2f}",
        "paid_amount": f"{inv.paid_amount:.2f}",
        "balance_due": f"{balance:.2f}",
        "patient_declaration": declaration_out(latest),
    }


def _patient_invoice_or_403(request, invoice_id: UUID) -> Invoice:
    profile = getattr(request.auth, "patient_profile", None)
    if not profile:
        raise HttpError(403, "Réservé aux patients.")
    try:
        return Invoice.objects.select_related("patient").get(pk=invoice_id, patient_id=profile.id)
    except Invoice.DoesNotExist as exc:
        raise HttpError(404, "Facture introuvable.") from exc


@router.get("/invoices/", response=list[InvoiceOut], auth=jwt_auth)
@require_permission("billing.view_finance")
def list_invoices(request, page: int = 1, page_size: int = 20):
    offset = (page - 1) * page_size
    invoices = (
        Invoice.objects.select_related("patient")
        .prefetch_related("patient_declarations")
        .order_by("-created_at")[offset : offset + page_size]
    )
    return [_invoice_out(i) for i in invoices]


@router.get("/invoices/mine/", response=list[InvoiceOut], auth=jwt_auth)
def list_my_invoices(request):
    profile = getattr(request.auth, "patient_profile", None)
    if not profile:
        raise HttpError(403, "Profil patient requis.")
    invoices = (
        Invoice.objects.filter(patient_id=profile.id)
        .exclude(status=Invoice.CANCELLED)
        .prefetch_related("patient_declarations")
        .order_by("-created_at")
    )
    return [_invoice_out(i) for i in invoices]


@router.get("/invoices/mine/{invoice_id}/", response=InvoiceOut, auth=jwt_auth)
def get_my_invoice(request, invoice_id: UUID):
    inv = _patient_invoice_or_403(request, invoice_id)
    return _invoice_out(inv)


@router.get("/invoices/mine/{invoice_id}/lines/", response=list[InvoiceLineOut], auth=jwt_auth)
def get_my_invoice_lines(request, invoice_id: UUID):
    inv = _patient_invoice_or_403(request, invoice_id)
    lines = InvoiceLine.objects.filter(invoice_id=inv.id)
    return [
        {
            "id": l.id,
            "description": l.description,
            "service_type": l.service_type,
            "quantity": str(l.quantity),
            "unit_price": str(l.unit_price),
            "total": str(l.total),
        }
        for l in lines
    ]


@router.post("/invoices/mine/{invoice_id}/declare/", response=InvoiceOut, auth=jwt_auth)
def declare_my_invoice_payment(request, invoice_id: UUID, payload: PatientPaymentDeclareIn):
    inv = _patient_invoice_or_403(request, invoice_id)
    declaration = payload.declaration.upper().strip()
    try:
        declare_patient_payment(
            inv,
            user=request.auth,
            phone_number=payload.phone_number,
            method=payload.method.upper().strip(),
            declaration=declaration,
            transaction_reference=payload.transaction_reference,
            amount=payload.amount,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    inv.refresh_from_db()
    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="Invoice",
        resource_id=str(inv.id),
        new_value={
            "patient_declaration": declaration,
            "phone": payload.phone_number,
            "method": payload.method,
        },
    )
    invalidate_dashboard_cache()
    return _invoice_out(inv)


@router.get("/invoices/{invoice_id}/", response=InvoiceOut, auth=jwt_auth)
@require_permission("billing.view_finance")
def get_invoice(request, invoice_id: UUID):
    try:
        inv = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist as exc:
        raise HttpError(404, "Facture introuvable.") from exc
    return _invoice_out(inv)


@router.get("/invoices/{invoice_id}/lines/", response=list[InvoiceLineOut], auth=jwt_auth)
@require_permission("billing.view_finance")
def get_invoice_lines(request, invoice_id: UUID):
    lines = InvoiceLine.objects.filter(invoice_id=invoice_id)
    return [
        {
            "id": l.id,
            "description": l.description,
            "service_type": l.service_type,
            "quantity": str(l.quantity),
            "unit_price": str(l.unit_price),
            "total": str(l.total),
        }
        for l in lines
    ]


@router.patch("/invoices/{invoice_id}/", response=InvoiceOut, auth=jwt_auth)
@require_permission("billing.create_invoice")
def patch_invoice(request, invoice_id: UUID, payload: InvoiceUpdateIn):
    try:
        invoice = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist as exc:
        raise HttpError(404, "Facture introuvable.") from exc

    try:
        lines = [line.dict() for line in payload.lines]
        invoice = update_invoice(invoice, lines, request.auth, payload.reason)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="Invoice",
        resource_id=str(invoice.id),
        new_value={
            "subtotal": str(invoice.subtotal),
            "patient_amount": str(invoice.patient_amount),
            "reason": payload.reason or None,
        },
    )
    return _invoice_out(invoice)


@router.post("/invoices/{invoice_id}/payments/", response=InvoiceOut, auth=jwt_auth)
@require_permission("billing.create_invoice")
def add_payment(request, invoice_id: UUID, payload: PaymentIn):
    try:
        invoice = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist as exc:
        raise HttpError(404, "Facture introuvable.") from exc

    if payload.method not in (Payment.AIRTEL, Payment.MTN):
        raise HttpError(
            400,
            "Mode de paiement non autorisé. Utilisez Airtel Money ou MTN Mobile Money uniquement.",
        )

    try:
        invoice = record_payment(invoice, payload.amount, payload.method, request.auth, payload.dict())
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    invalidate_dashboard_cache()
    return _invoice_out(invoice)


@router.get("/invoices/{invoice_id}/pdf/", auth=jwt_auth)
@require_permission("billing.view_finance")
def download_invoice_pdf(request, invoice_id: UUID):
    try:
        inv = Invoice.objects.select_related("patient").get(pk=invoice_id)
    except Invoice.DoesNotExist as exc:
        raise HttpError(404, "Facture introuvable.") from exc

    lines = InvoiceLine.objects.filter(invoice=inv)
    pdf_bytes = generate_invoice_pdf(
        invoice_number=inv.invoice_number,
        patient_name=str(inv.patient),
        lines=[{"description": l.description, "total": str(l.total)} for l in lines],
        total=str(inv.patient_amount),
    )
    rel_path, file_hash = store_encrypted_file(pdf_bytes, "invoices", f"{inv.invoice_number}.pdf.enc")
    Document.objects.create(
        patient=inv.patient,
        hospitalization=inv.hospitalization,
        document_type=Document.INVOICE,
        title=f"Facture {inv.invoice_number}",
        file_path=rel_path,
        mime_type="application/pdf",
        file_size=len(pdf_bytes),
        file_hash=file_hash,
        is_encrypted=True,
        uploaded_by=request.auth,
        signed_at=timezone.now(),
        signed_by=request.auth,
        signature_hash=file_hash[:64],
    )
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{inv.invoice_number}.pdf"'
    return response


@router.post("/accounting/adjustments/", response=AccountingEntryOut, auth=jwt_auth)
@require_permission("billing.adjust")
def create_adjustment(request, payload: AdjustmentIn):
    if payload.entry_type not in (AccountingEntry.DEBIT, AccountingEntry.CREDIT):
        raise HttpError(400, "entry_type doit être DEBIT ou CREDIT.")
    try:
        invoice = Invoice.objects.get(pk=payload.invoice_id)
    except Invoice.DoesNotExist as exc:
        raise HttpError(404, "Facture introuvable.") from exc

    entry = AccountingEntry.objects.create(
        account_code=payload.account_code,
        label=f"[Ajustement] {payload.label} — {payload.reason}".strip(" —"),
        entry_type=payload.entry_type,
        amount=payload.amount,
        invoice=invoice,
        created_by=request.auth,
        is_adjustment=True,
    )
    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="AccountingEntry",
        resource_id=str(entry.id),
        new_value={"adjustment": payload.label, "amount": str(payload.amount)},
    )
    return {
        "id": entry.id,
        "entry_date": entry.entry_date.isoformat(),
        "account_code": entry.account_code,
        "label": entry.label,
        "entry_type": entry.entry_type,
        "amount": str(entry.amount),
        "is_adjustment": entry.is_adjustment,
    }


@router.get("/insurance/patient/{patient_id}/", auth=jwt_auth)
@require_permission("billing.view_finance")
def get_patient_insurance(request, patient_id: UUID):
    ins = (
        PatientInsurance.objects.filter(patient_id=patient_id, is_primary=True)
        .select_related("provider")
        .first()
    )
    if not ins:
        return {"has_insurance": False}
    return {
        "has_insurance": True,
        "provider_name": ins.provider.name,
        "coverage_rate": str(ins.provider.coverage_rate),
        "policy_number": ins.policy_number,
    }


@router.get("/accounting/journal/", response=list[AccountingEntryOut], auth=jwt_auth)
@require_permission("billing.view_finance")
def accounting_journal(request, page: int = 1, page_size: int = 50):
    offset = (page - 1) * page_size
    entries = AccountingEntry.objects.order_by("-entry_date")[offset : offset + page_size]
    return [
        {
            "id": e.id,
            "entry_date": e.entry_date.isoformat(),
            "account_code": e.account_code,
            "label": e.label,
            "entry_type": e.entry_type,
            "amount": str(e.amount),
            "is_adjustment": e.is_adjustment,
        }
        for e in entries
    ]
