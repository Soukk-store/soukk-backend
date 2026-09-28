from soukk_backend.settings.brokerSettings import BrokerSettings


class BeatSettings(BrokerSettings):
    """Celery beat only puts jobs on the queue on a schedule: no database, no email."""

    token_cleanup_schedule: str


beat_settings = BeatSettings()
