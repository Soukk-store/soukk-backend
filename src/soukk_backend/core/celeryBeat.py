from celery.schedules import crontab

from soukk_backend.core.celeryApp import celery_app
from soukk_backend.settings.beatSettings import beat_settings

# Loaded only by the celery-beat container. Beat queues jobs by name at the given
# times (cron format, UTC); it never runs them and never imports their code.
celery_app.conf.beat_schedule = {
    "cleanup-expired-refresh-tokens": {
        "task": "soukk_backend.core.tasks.maintenanceTask.cleanup_refresh_tokens_task",
        "schedule": crontab.from_string(beat_settings.token_cleanup_schedule),
    },
}
