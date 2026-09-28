from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Only what the Celery worker needs: where the queue is and how to send email.

    The worker container receives just these variables, so API secrets (JWT key,
    database password, ...) never reach it. The API's Settings extends this class.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    redis_host: str
    redis_port: int
    redis_celery_db: int

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

    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_celery_db}"


worker_settings = WorkerSettings()
