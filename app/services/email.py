import os
from typing import Dict

import resend
from bs4 import BeautifulSoup
from mjml import mjml_to_html
from pystache import render

from app.core import celery, settings

resend.api_key = settings.RESEND_API_KEY

TEMPLATE_FOLDER = os.path.join(os.path.dirname(__file__), "../emails")


def send_welcome_email(
    email: str, first_name: str, verification_token: str = None
) -> Dict:
    context = {"first_name": first_name}
    subject = "Welcome to Waiterbildung!"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_emails = [email]

    if verification_token:
        context["verification_link"] = (
            f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        )
        template = "signup.mjml"
    else:
        template = "signup-with-google.mjml"

    return send_mail(from_email, to_emails, subject, template, context)


def send_verification_email(
    email: str, first_name: str, verification_token: str
) -> Dict:
    context = {
        "first_name": first_name,
        "verification_link": f"{settings.FRONTEND_URL}/verify-email?token={verification_token}",
    }
    subject = "Verify your email address"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_emails = [email]
    template = "email-verification.mjml"

    return send_mail(from_email, to_emails, subject, template, context)


def send_email_verified(email: str, first_name: str) -> Dict:
    context = {"first_name": first_name}
    subject = "Your email has been verified"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_emails = [email]
    template = "email-verified.mjml"

    return send_mail(from_email, to_emails, subject, template, context)


def send_password_reset_request(email: str, first_name: str, reset_token: str) -> Dict:
    context = {
        "first_name": first_name,
        "reset_link": f"{settings.FRONTEND_URL}/reset-password?token={reset_token}",
    }
    subject = "Reset your password"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_emails = [email]
    template = "password-reset-request.mjml"

    return send_mail(from_email, to_emails, subject, template, context)


def send_password_reset_success(email: str, first_name: str) -> Dict:
    context = {"first_name": first_name}
    subject = "Your password has been reset"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_emails = [email]
    template = "password-reset-success.mjml"

    return send_mail(from_email, to_emails, subject, template, context)


@celery.task(name="send_mail")
def send_mail_async(from_email: str, to_emails: list, subject: str, html: str) -> Dict:
    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": to_emails,
        "subject": subject,
        "html": html,
        "text": clean_html(html),
    }
    email: resend.Email = resend.Emails.send(params)
    return email


def send_mail(
    from_email: str,
    to_emails: list,
    subject: str,
    template: str,
    context: Dict[str, str] = {},
) -> Dict:
    template_path = os.path.join(TEMPLATE_FOLDER, template)

    with open(template_path, "rb") as f:
        html = mjml_to_html(f).html
    html = render(html, context)

    return send_mail_async.delay(from_email, to_emails, subject, html)


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    text = " ".join(text.split())
    return text
