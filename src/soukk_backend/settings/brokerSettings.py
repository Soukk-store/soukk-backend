from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class BrokerSettings(BaseSettings):
    """Where the Celery queue lives. Every container that queues or runs jobs needs it."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    redis_host: str
    redis_port: int
    redis_password: str
    redis_celery_db: int

    def redis_url(self, db: int) -> str:
        # Quoted so a password with URL characters (@, /, :) can't break the URL.
        password = quote(self.redis_password, safe="")
        return f"redis://:{password}@{self.redis_host}:{self.redis_port}/{db}"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url(self.redis_celery_db)


broker_settings = BrokerSettings()
