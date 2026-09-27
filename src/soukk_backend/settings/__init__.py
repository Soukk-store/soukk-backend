from functools import lru_cache

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: str = "development"
    port: int = 8000
    web_workers: int = 1
    server_url: str = "http://localhost:8000"
    frontend_url: str

    db_host: str
    db_port: int = 5432
    db_user: str
    db_password: str
    db_name: str

    jwt_secret: str
    jwt_algorithm: str
    email_verify_expire_minutes: int
    password_reset_expire_minutes: int
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    mail_username: str
    mail_password: str
    mail_from: EmailStr
    mail_server: str
    mail_port: int
    mail_starttls: bool
    mail_ssl_tls: bool

    rate_limit_email_exists: str
    rate_limit_register: str
    rate_limit_resend: str
    rate_limit_login: str
    rate_limit_forgot_password: str

    @property
    def is_dev(self) -> bool:
        return self.env.lower() == "development"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
