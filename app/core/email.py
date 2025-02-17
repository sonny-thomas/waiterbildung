from pathlib import Path
from typing import Dict

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from fastapi_mail.schemas import MessageType
from mjml import mjml_to_html
from pystache import render

from app.core.config import settings
from app.core.queue import email_queue

TEMPLATE_FOLDER = Path(__file__).parent.parent / "emails"

email_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_USERNAME,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
)
fm = FastMail(email_config)


def send_email(
    subject: str, email: str, template_name: str, context: Dict[str, str] = {}
) -> None:
    """Send email using MJML template"""
    template_path = TEMPLATE_FOLDER / template_name
    with open(template_path, "rb") as f:
        html_content = str(render(mjml_to_html(f).html, context))

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=html_content,
        subtype=MessageType.html,
    )
    email_queue.enqueue(fm.send_message, message=message)


def send_verification_email(email: str, first_name: str, token: str) -> None:
    """Send Verification Email"""
    send_email(
        subject="Verify your email address",
        email=email,
        template_name="verification.mjml",
        context={
            "first_name": first_name,
            "verification_url": f"{settings.FRONTEND_URL}/auth/verify/{token}",
        },
    )


def send_reset_password(email: str, first_name: str, token: str) -> None:
    """Send reset password email"""
    send_email(
        subject="Reset your password",
        email=email,
        template_name="reset_password.mjml",
        context={
            "first_name": first_name,
            "reset_url": f"{settings.FRONTEND_URL}/auth/reset-password/{token}",
        },
    )
