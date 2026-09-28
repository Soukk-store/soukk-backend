from pydantic import EmailStr

from soukk_backend.settings.brokerSettings import BrokerSettings


class EmailWorkerSettings(BrokerSettings):
    """Only what the email worker needs: the queue and how to send email.

    The celery container receives just these variables, so API secrets (JWT key,
    database password, ...) never reach it.
    """

    email_verify_expire_minutes: int
    password_reset_expire_minutes: int

    mail_username: str
    mail_password: str
    mail_from: EmailStr
    mail_server: str
    mail_port: int
    mail_starttls: bool
    mail_ssl_tls: bool
    email_logo_url: str


email_worker_settings = EmailWorkerSettings()
