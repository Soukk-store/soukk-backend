from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from soukk_backend.settings.emailWorkerSettings import email_worker_settings

TEMPLATE_FOLDER = Path(__file__).resolve().parent.parent / "templates" / "email"

mail_config = ConnectionConfig(
    MAIL_USERNAME=email_worker_settings.mail_username,
    MAIL_PASSWORD=email_worker_settings.mail_password,
    MAIL_FROM=email_worker_settings.mail_from,
    MAIL_SERVER=email_worker_settings.mail_server,
    MAIL_PORT=email_worker_settings.mail_port,
    MAIL_STARTTLS=email_worker_settings.mail_starttls,
    MAIL_SSL_TLS=email_worker_settings.mail_ssl_tls,
    USE_CREDENTIALS=bool(email_worker_settings.mail_username),
    TEMPLATE_FOLDER=TEMPLATE_FOLDER,
)

mailer = FastMail(mail_config)


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


async def _send(email: str, subject: str, template_name: str, values: dict) -> None:
    """Every template also gets the recipient's email and the logo."""
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        template_body={"email": email, "logo_url": email_worker_settings.email_logo_url, **values},
        subtype=MessageType.html,
    )
    await mailer.send_message(message, template_name=template_name)


def format_duration(minutes: int) -> str:
    """1440 -> "24 hours", 90 -> "90 minutes"."""
    if minutes % 60:
        return f"{minutes} minutes" if minutes != 1 else "1 minute"
    hours = minutes // 60
    return f"{hours} hours" if hours != 1 else "1 hour"
