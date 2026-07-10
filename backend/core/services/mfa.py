import io
import base64

import pyotp
from django.conf import settings


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def verify_mfa_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def provisioning_uri(username: str, secret: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=getattr(settings, "MFA_ISSUER", "SGHL"),
    )
