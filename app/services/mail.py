import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_otp_email(recipient: str, otp: str) -> bool:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        return False

    message = EmailMessage()
    message["Subject"] = f"{settings.PROJECT_NAME} password reset OTP"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                f"Your {settings.PROJECT_NAME} password reset OTP is: {otp}",
                "",
                f"This code expires in {settings.PASSWORD_RESET_OTP_EXPIRE_MINUTES} minutes.",
                "If you did not request a password reset, you can ignore this email.",
            ]
        )
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.ehlo()
            if settings.SMTP_USE_TLS:
                server.starttls(context=context)
                server.ehlo()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
        return True
    except Exception as exc:
        logger.exception("Failed to send password reset OTP email")
        return False
