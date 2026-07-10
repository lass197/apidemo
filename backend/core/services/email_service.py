import logging
import smtplib
import threading
from email.mime.text import MIMEText

from django.conf import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Envoie un email via SMTP (Gmail) si configuré."""
    host = getattr(settings, "EMAIL_HOST", "")
    if not host or not to:
        logger.info("Email non envoyé (SMTP non configuré): %s → %s\n%s", subject, to, body[:200])
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.DEFAULT_FROM_EMAIL
        msg["To"] = to
        with smtplib.SMTP(host, settings.EMAIL_PORT) as server:
            if settings.EMAIL_USE_TLS:
                server.starttls()
            if settings.EMAIL_HOST_USER:
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:
        logger.warning("Échec envoi email: %s", exc)
        return False


def enqueue_email(to: str, subject: str, body: str) -> None:
    """Envoi email asynchrone (thread daemon) pour ne pas bloquer la requête HTTP."""
    thread = threading.Thread(
        target=send_email,
        args=(to, subject, body),
        daemon=True,
        name=f"email-{to[:20]}",
    )
    thread.start()
