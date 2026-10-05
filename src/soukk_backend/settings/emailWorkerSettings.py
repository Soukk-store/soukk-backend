from pydantic import EmailStr

from soukk_backend.settings.brokerSettings import BrokerSettings


class EmailWorkerSettings(BrokerSettings):
    """Only what the email worker needs: the queue and how to send email.

    The celery container receives just these variables, so API secrets (JWT key,
    database password, ...) never reach it.
    """

    email_verify_expire_minutes: int
    password_reset_expire_minutes: int

    mail_api_url: str
    mail_api_token: str
    mail_from: EmailStr
    mail_timeout_seconds: float
    email_asset_url: str


email_worker_settings = EmailWorkerSettings()
