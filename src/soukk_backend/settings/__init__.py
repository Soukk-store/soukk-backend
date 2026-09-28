# Import the settings you need from their module, never from here:
#   API code:    from soukk_backend.settings.appSettings import settings
#   worker code: from soukk_backend.settings.workerSettings import worker_settings
# Keeping this file empty means importing one never builds the other, so the
# worker starts without the API's variables.
