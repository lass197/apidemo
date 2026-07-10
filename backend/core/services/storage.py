import os
import uuid
from pathlib import Path

from cryptography.fernet import Fernet
from django.conf import settings


def _get_fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        key = Fernet.generate_key().decode()
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_bytes(data: bytes) -> bytes:
    return _get_fernet().encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    return _get_fernet().decrypt(data)


def store_encrypted_file(content: bytes, subdirectory: str, filename: str | None = None) -> tuple[str, str]:
    """Retourne (chemin relatif, hash sha256)."""
    from documents.models import Document

    file_hash = Document.compute_hash(content)
    name = filename or f"{uuid.uuid4()}.bin"
    rel_dir = Path(subdirectory)
    abs_dir = settings.MEDIA_ROOT / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    abs_path = abs_dir / name
    encrypted = encrypt_bytes(content)
    abs_path.write_bytes(encrypted)
    return str(rel_dir / name), file_hash
