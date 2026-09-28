# Import the settings you need from their module, never from here. Each container
# only receives the variables of its own settings class, and a module builds its
# settings when imported, so importing the wrong one fails on missing variables.
#   API:                appSettings.settings
#   email worker:       emailWorkerSettings.email_worker_settings
#   maintenance worker: maintenanceSettings.maintenance_settings
#   celery beat:        beatSettings.beat_settings
#   any queue user:     brokerSettings.broker_settings
#   database code:      databaseSettings.database_settings
