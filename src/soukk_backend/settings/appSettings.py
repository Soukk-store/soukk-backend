from soukk_backend.settings.workerSettings import WorkerSettings


class Settings(WorkerSettings):
    """Everything the API needs: the worker's settings plus the API-only ones."""

    env: str
    port: int
    web_workers: int
    server_url: str
    frontend_url: str

    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str

    redis_rate_limit_db: int

    jwt_secret: str
    jwt_algorithm: str
    email_cooldown_seconds: int
    access_token_expire_minutes: int
    refresh_token_expire_days: int

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
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_rate_limit_db}"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
