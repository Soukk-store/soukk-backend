from soukk_backend.settings.databaseSettings import DatabaseSettings
from soukk_backend.settings.emailWorkerSettings import EmailWorkerSettings
from soukk_backend.settings.storageSettings import StorageSettings


class Settings(EmailWorkerSettings, DatabaseSettings, StorageSettings):
    """Everything the API needs: the email, database and storage settings plus the API-only ones."""

    env: str
    port: int
    web_workers: int
    server_url: str
    frontend_url: str

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
    rate_limit_image_upload: str

    @property
    def is_dev(self) -> bool:
        return self.env.lower() == "development"

    @property
    def rate_limit_storage_url(self) -> str:
        return self.redis_url(self.redis_rate_limit_db)


settings = Settings()
