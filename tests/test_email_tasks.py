import pytest
from aiosmtplib import SMTPException

from soukk_backend.core.tasks import emailTask
from soukk_backend.core.tasks.emailTask import (
    send_password_reset_email_task,
    send_verification_email_task,
)

TASKS = [
    (send_verification_email_task, "send_verification_email"),
    (send_password_reset_email_task, "send_password_reset_email"),
]


@pytest.mark.parametrize(("task", "sender_name"), TASKS)
def test_task_sends_the_matching_email(monkeypatch, task, sender_name):
    calls = []

    async def fake_sender(*args):
        calls.append(args)

    monkeypatch.setattr(emailTask, sender_name, fake_sender)

    task.run("user@example.com", "Test", "http://link")

    assert calls == [("user@example.com", "Test", "http://link")]


@pytest.mark.parametrize(("task", "_"), TASKS)
def test_task_is_durable_and_retries_smtp_failures(task, _):
    assert task.acks_late is True
    assert task.reject_on_worker_lost is True
    assert SMTPException in task.autoretry_for
    assert OSError in task.autoretry_for
    assert task.max_retries == 5


def test_failing_send_is_retried_then_raised(monkeypatch):
    attempts = []

    async def failing_sender(*args):
        attempts.append(args)
        raise SMTPException("server down")

    monkeypatch.setattr(emailTask, "send_verification_email", failing_sender)
    # Run in-process (no broker) and without the real backoff delays.
    monkeypatch.setattr(send_verification_email_task, "retry_backoff", False)
    monkeypatch.setattr(send_verification_email_task, "default_retry_delay", 0)

    result = send_verification_email_task.apply(args=("user@example.com", "Test", "http://link"))

    assert result.failed()
    assert isinstance(result.result, SMTPException)
    assert len(attempts) == 1 + send_verification_email_task.max_retries
