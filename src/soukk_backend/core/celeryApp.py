from celery import Celery

from soukk_backend.settings import settings

celery_app = Celery(
    "soukk",
    broker=settings.celery_broker_url,
    include=["soukk_backend.core.tasks.emailTask"],
)
celery_app.conf.update(
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)
