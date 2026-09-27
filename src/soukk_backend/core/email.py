from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from soukk_backend.settings import settings

mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_SERVER=settings.mail_server,
    MAIL_PORT=settings.mail_port,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=bool(settings.mail_username),
)

mailer = FastMail(mail_config)


async def send_verification_email(email: str, link: str) -> None:
    message = MessageSchema(
        subject="Verify your Soukk account",
        recipients=[email],
        body=(
            "<p>Welcome to Soukk!</p>"
            f'<p>Click <a href="{link}">here</a> to verify your email.</p>'
            f"<p>This link expires in {settings.email_verify_expire_minutes // 60} hours.</p>"
        ),
        subtype=MessageType.html,
    )
    await mailer.send_message(message)
