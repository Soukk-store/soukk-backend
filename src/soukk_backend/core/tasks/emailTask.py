import asyncio

import httpx

from soukk_backend.core.celeryApp import celery_app
from soukk_backend.core.email import (
    MailServiceBusy,
    send_password_reset_email,
    send_verification_email,
)

# Retried after ~1s, 2s, 4s... (with jitter, capped at 10 minutes):
# - httpx.TransportError: the mail API couldn't be reached (down, timeout, refused)
# - MailServiceBusy: the mail API rate limited us or failed (429 / 5xx)
# Other errors (bad token, bad request) fail at once: retrying won't fix them.
RETRY_OPTIONS = {
    "autoretry_for": (httpx.TransportError, MailServiceBusy),
    "retry_backoff": True,
    "max_retries": 5,
}


# Celery tasks are plain functions; asyncio.run runs the async email code inside.
@celery_app.task(**RETRY_OPTIONS)
def send_verification_email_task(email: str, first_name: str, link: str) -> None:
    asyncio.run(send_verification_email(email, first_name, link))


@celery_app.task(**RETRY_OPTIONS)
def send_password_reset_email_task(email: str, first_name: str, link: str) -> None:
    asyncio.run(send_password_reset_email(email, first_name, link))
