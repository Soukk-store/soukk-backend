from pydantic_settings import BaseSettings, SettingsConfigDict


class BrokerSettings(BaseSettings):
    """Where the Celery queue lives. Every container that queues or runs jobs needs it."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    redis_host: str
    redis_port: int
    redis_celery_db: int

    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_celery_db}"


broker_settings = BrokerSettings()
