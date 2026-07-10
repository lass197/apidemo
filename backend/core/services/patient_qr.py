import hashlib
import hmac
from datetime import datetime, timezone
from uuid import UUID

from django.conf import settings


def _public_site_url() -> str:
    return getattr(settings, "PUBLIC_SITE_URL", "http://127.0.0.1:8000").rstrip("/")


def sign_patient_qr(patient_id: UUID, doctor_id: UUID | None, issued_at: datetime) -> str:
    raw = f"{patient_id}|{doctor_id or ''}|{issued_at.strftime('%Y%m%d')}"
    return hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()[:24]


def verify_patient_qr_token(
    patient_id: UUID,
    doctor_id: UUID | None,
    issued_at: datetime,
    token: str,
) -> bool:
    if not token:
        return False
    expected = sign_patient_qr(patient_id, doctor_id, issued_at)
    return hmac.compare_digest(expected, token)


def build_patient_qr_url(patient_id: UUID, doctor_id: UUID | None, issued_at: datetime | None = None) -> str:
    issued = issued_at or datetime.now(timezone.utc)
    token = sign_patient_qr(patient_id, doctor_id, issued)
    at = issued.strftime("%Y%m%d")
    base = _public_site_url()
    url = f"{base}/patient/qr?p={patient_id}&t={token}&at={at}"
    if doctor_id:
        url += f"&d={doctor_id}"
    return url
