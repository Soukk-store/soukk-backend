import asyncio

from aiosmtplib import SMTPException

from soukk_backend.core.celeryApp import celery_app
from soukk_backend.core.email import send_password_reset_email, send_verification_email

# SMTP errors (e.g. Mailtrap's "too many emails per second") and network errors
# are retried after ~1s, 2s, 4s... (with jitter, capped at 10 minutes).
RETRY_OPTIONS = {
    "autoretry_for": (SMTPException, OSError),
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
