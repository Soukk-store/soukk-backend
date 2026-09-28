from celery import Celery

from soukk_backend.settings.brokerSettings import broker_settings

# Shared by every process that queues or runs jobs. Only the broker is set here:
# each worker loads its own task module with `-I` (see docker-compose.yaml), so the
# email worker never imports database code and the maintenance worker never
# imports email code, and neither needs the other's variables.
celery_app = Celery("soukk", broker=broker_settings.celery_broker_url)
celery_app.conf.update(
    # Nobody reads the return value of these jobs, so don't store it.
    task_ignore_result=True,
    # Remove a job from the queue only after it finished; if the worker is
    # killed mid-job, the job goes back in the queue instead of being lost.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Take one job at a time so a busy process doesn't hold jobs others could run.
    worker_prefetch_multiplier=1,
    # Keep retrying the Redis connection when a process starts before Redis is ready.
    broker_connection_retry_on_startup=True,
    # Give up on Redis after a few seconds instead of waiting forever, so the API
    # fails fast (see tasks/enqueue.py) when Redis is down or hangs. The read
    # timeout must stay above the workers' 1 second polling interval.
    broker_transport_options={"socket_connect_timeout": 2, "socket_timeout": 5},
    # Maintenance jobs go to their own queue, read only by the maintenance worker.
    # Everything else stays on the default "celery" queue (the email worker).
    task_routes={"soukk_backend.core.tasks.maintenanceTask.*": {"queue": "maintenance"}},
)
