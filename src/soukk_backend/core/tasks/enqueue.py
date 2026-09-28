import logging

from celery import Task
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


async def enqueue(task: Task, *args) -> bool:
    """Queue a job from an async endpoint; returns False instead of raising.

    Publishing talks to Redis with blocking calls, so it runs in a thread to keep
    the event loop free. It tries once (no retries) and the broker connection has
    a short timeout (celeryApp.py), so a Redis outage costs a request ~2 seconds
    instead of freezing it. A failure is logged and the request still succeeds:
    the user can ask for the email again (resend / forgot password).
    """
    try:
        await run_in_threadpool(task.apply_async, args=args, retry=False)
        return True
    except Exception:
        logger.exception("Could not queue %s", task.name)
        return False
