from uuid import UUID

from django.http import HttpResponse
from django.utils import timezone
from ninja import File, Form, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile

from core.auth import jwt_auth
from core.middleware import get_client_ip
from core.permissions import require_permission
from core.services.audit import log_audit
from core.services.storage import decrypt_bytes, store_encrypted_file
from documents.models import Document, DocumentAccessLog
from clinical.models import Patient
from django.conf import settings
from pathlib import Path

router = Router(tags=["Documents"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/dicom",
}


class DocumentOut(Schema):
    id: UUID
    title: str
    document_type: str
    mime_type: str
    file_size: int
    signed_at: str | None
    created_at: str


@router.get("/", response=list[DocumentOut], auth=jwt_auth)
def list_documents(request, patient_id: UUID | None = None, page: int = 1, page_size: int = 20):
    profile = getattr(request.auth, "patient_profile", None)
    if profile:
        if patient_id and patient_id != profile.id:
            raise HttpError(403, "Accès refusé.")
        qs = Document.objects.filter(patient_id=profile.id)
    elif request.auth.has_perm_code("documents.view"):
        qs = Document.objects.all()
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
    else:
        raise HttpError(403, "Accès refusé.")
    qs = qs.order_by("-created_at")
    offset = (page - 1) * page_size
    return [
        {
            "id": d.id,
            "title": d.title,
            "document_type": d.document_type,
            "mime_type": d.mime_type,
            "file_size": d.file_size,
            "signed_at": d.signed_at.isoformat() if d.signed_at else None,
            "created_at": d.created_at.isoformat(),
        }
        for d in qs[offset : offset + page_size]
    ]


@router.post("/upload/", response=DocumentOut, auth=jwt_auth)
@require_permission("documents.upload")
def upload_document(
    request,
    patient_id: UUID = Form(...),
    title: str = Form(...),
    document_type: str = Form("OTHER"),
    file: UploadedFile = File(...),
):
    if file.size > MAX_UPLOAD_BYTES:
        raise HttpError(413, "Fichier trop volumineux (max 10 Mo).")
    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_MIMES:
        raise HttpError(400, f"Type MIME non autorisé : {mime}")

    try:
        patient = Patient.objects.get(pk=patient_id, is_active=True)
    except Patient.DoesNotExist as exc:
        raise HttpError(404, "Patient introuvable.") from exc

    content = file.read()
    rel_path, file_hash = store_encrypted_file(content, "uploads", f"{patient_id}_{file.name}.enc")

    doc = Document.objects.create(
        patient=patient,
        document_type=document_type,
        title=title,
        file_path=rel_path,
        mime_type=mime,
        file_size=len(content),
        file_hash=file_hash,
        is_encrypted=True,
        uploaded_by=request.auth,
        signed_at=timezone.now(),
        signed_by=request.auth,
        signature_hash=file_hash[:64],
    )
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="Document",
        resource_id=str(doc.id),
        new_value={"title": title, "patient_id": str(patient_id)},
    )
    return {
        "id": doc.id,
        "title": doc.title,
        "document_type": doc.document_type,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "signed_at": doc.signed_at.isoformat() if doc.signed_at else None,
        "created_at": doc.created_at.isoformat(),
    }


@router.get("/{document_id}/download/", auth=jwt_auth)
def download_document(request, document_id: UUID):
    try:
        doc = Document.objects.get(pk=document_id)
    except Document.DoesNotExist as exc:
        raise HttpError(404, "Document introuvable.") from exc

    profile = getattr(request.auth, "patient_profile", None)
    if profile:
        if doc.patient_id != profile.id:
            raise HttpError(403, "Accès refusé à ce document.")
    elif not request.auth.has_perm_code("documents.view"):
        raise HttpError(403, "Accès refusé.")

    file_path = Path(settings.MEDIA_ROOT) / doc.file_path
    if not file_path.exists():
        raise HttpError(404, "Fichier introuvable.")

    content = file_path.read_bytes()
    if doc.is_encrypted:
        content = decrypt_bytes(content)

    DocumentAccessLog.objects.create(
        document=doc,
        user=request.auth,
        ip_address=get_client_ip(request),
        action="DOWNLOAD",
    )

    ext = ".pdf" if "pdf" in doc.mime_type else ""
    response = HttpResponse(content, content_type=doc.mime_type)
    response["Content-Disposition"] = f'attachment; filename="{doc.title}{ext}"'
    return response
