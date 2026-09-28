from soukk_backend.settings.brokerSettings import BrokerSettings
from soukk_backend.settings.databaseSettings import DatabaseSettings


class MaintenanceSettings(BrokerSettings, DatabaseSettings):
    """The maintenance worker: the queue plus the database, and nothing about email or JWT."""

    token_cleanup_batch_size: int


maintenance_settings = MaintenanceSettings()
