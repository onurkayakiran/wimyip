import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_address: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_address:
        logger.warning("SMTP yapilandirilmamis, e-posta gonderilmedi: %s -> %s", subject, to_address)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_address
    message["To"] = to_address
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except Exception:
        # E-posta gonderimi basarisiz olsa bile kontrol dongusu asla
        # durmamali - sadece loglanir, cagiran (monitor_checks) devam eder.
        logger.exception("E-posta gonderilemedi: %s -> %s", subject, to_address)
