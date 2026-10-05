import httpx
import pytest

from soukk_backend.core.email import MailServiceBusy
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
def test_task_is_durable_and_retries_mail_failures(task, _):
    assert task.acks_late is True
    assert task.reject_on_worker_lost is True
    assert set(task.autoretry_for) == {httpx.TransportError, MailServiceBusy}
    assert task.max_retries == 5


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectTimeout("mail API unreachable"),
        MailServiceBusy("429: too many emails per second"),
    ],
    ids=["network", "busy"],
)
def test_failing_send_is_retried_then_raised(monkeypatch, error):
    attempts = []

    async def failing_sender(*args):
        attempts.append(args)
        raise error

    monkeypatch.setattr(emailTask, "send_verification_email", failing_sender)
    # Run in-process (no broker) and without the real backoff delays.
    monkeypatch.setattr(send_verification_email_task, "retry_backoff", False)
    monkeypatch.setattr(send_verification_email_task, "default_retry_delay", 0)

    result = send_verification_email_task.apply(args=("user@example.com", "Test", "http://link"))

    assert result.failed()
    assert type(result.result) is type(error)
    assert len(attempts) == 1 + send_verification_email_task.max_retries


def test_bad_request_is_not_retried(monkeypatch):
    """A wrong token or payload won't fix itself: fail on the first attempt."""
    attempts = []

    async def rejected_sender(*args):
        attempts.append(args)
        request = httpx.Request("POST", "https://mail.example")
        raise httpx.HTTPStatusError(
            "401", request=request, response=httpx.Response(401, request=request)
        )

    monkeypatch.setattr(emailTask, "send_verification_email", rejected_sender)

    result = send_verification_email_task.apply(args=("user@example.com", "Test", "http://link"))

    assert result.failed()
    assert len(attempts) == 1
