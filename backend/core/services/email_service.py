import logging
import smtplib
import threading
from email.mime.text import MIMEText

from django.conf import settings

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 8


def smtp_configured() -> bool:
    """True seulement si host + identifiants sont présents."""
    host = (getattr(settings, "EMAIL_HOST", "") or "").strip()
    user = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    password = (getattr(settings, "EMAIL_HOST_PASSWORD", "") or "").strip()
    return bool(host and user and password)


def send_email(to: str, subject: str, body: str) -> bool:
    """Envoie un email via SMTP si configuré (timeout court pour éviter les 502 Render)."""
    if not smtp_configured() or not to:
        logger.info("Email non envoyé (SMTP non configuré): %s → %s", subject, to)
        return False
    host = settings.EMAIL_HOST.strip()
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        msg["To"] = to
        with smtplib.SMTP(host, settings.EMAIL_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
            if settings.EMAIL_USE_TLS:
                server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:
        logger.warning("Échec envoi email: %s", exc)
        return False


def enqueue_email(to: str, subject: str, body: str) -> None:
    """Envoi email asynchrone (ne bloque jamais la requête HTTP)."""
    thread = threading.Thread(
        target=send_email,
        args=(to, subject, body),
        daemon=True,
        name=f"email-{to[:20]}",
    )
    thread.start()
