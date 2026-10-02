from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader

from soukk_backend.settings.emailWorkerSettings import email_worker_settings

TEMPLATE_FOLDER = Path(__file__).resolve().parent.parent / "templates" / "email"

# autoescape: user input (e.g. first_name) can't inject HTML into the email.
templates = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER), autoescape=True)


class MailServiceBusy(Exception):
    """The mail API is rate limiting us or failing (429 / 5xx): worth retrying."""


async def send_verification_email(email: str, first_name: str, link: str) -> None:
    await _send(
        email,
        subject="Confirm your Souk email",
        template_name="verify_email.html",
        values={
            "first_name": first_name,
            "verify_url": link,
            "expires_in": format_duration(email_worker_settings.email_verify_expire_minutes),
        },
    )


async def send_password_reset_email(email: str, first_name: str, link: str) -> None:
    await _send(
        email,
        subject="Reset your Souk password",
        template_name="reset_password.html",
        values={
            "first_name": first_name,
            "reset_url": link,
            "expires_in": format_duration(email_worker_settings.password_reset_expire_minutes),
        },
    )


def render(template_name: str, values: dict) -> str:
    return templates.get_template(template_name).render(**values)


async def _send(email: str, subject: str, template_name: str, values: dict) -> None:
    """Send through the Resend HTTPS API.

    Every template also gets the recipient's email and the images folder.
    """
    html = render(
        template_name,
        {"email": email, "asset_url": email_worker_settings.email_asset_url, **values},
    )
    async with httpx.AsyncClient(timeout=email_worker_settings.mail_timeout_seconds) as client:
        response = await client.post(
            email_worker_settings.mail_api_url,
            headers={"Authorization": f"Bearer {email_worker_settings.mail_api_token}"},
            json={
                "from": email_worker_settings.mail_from,
                "to": [email],
                "subject": subject,
                "html": html,
            },
        )

    if response.status_code == 429 or response.status_code >= 500:
        raise MailServiceBusy(f"{response.status_code}: {response.text}")
    # Any other error (bad token, bad request) won't fix itself: fail without retrying.
    response.raise_for_status()


def format_duration(minutes: int) -> str:
    """1440 -> "24 hours", 90 -> "90 minutes"."""
    if minutes % 60:
        return f"{minutes} minutes" if minutes != 1 else "1 minute"
    hours = minutes // 60
    return f"{hours} hours" if hours != 1 else "1 hour"
