from soukk_backend.settings.databaseSettings import DatabaseSettings
from soukk_backend.settings.emailWorkerSettings import EmailWorkerSettings


class Settings(EmailWorkerSettings, DatabaseSettings):
    """Everything the API needs: the email and database settings plus the API-only ones."""

    env: str
    port: int
    web_workers: int
    server_url: str
    frontend_url: str
    default_image_key: str

    redis_rate_limit_db: int

    jwt_secret: str
    jwt_algorithm: str
    email_cooldown_seconds: int
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    refresh_reuse_grace_seconds: int

    rate_limit_email_exists: str
    rate_limit_register: str
    rate_limit_resend: str
    rate_limit_login: str
    rate_limit_forgot_password: str
    rate_limit_reset_password: str
    rate_limit_change_password: str
    rate_limit_refresh: str
    rate_limit_logout: str

    @property
    def is_dev(self) -> bool:
        return self.env.lower() == "development"

    @property
    def rate_limit_storage_url(self) -> str:
        return self.redis_url(self.redis_rate_limit_db)


settings = Settings()
