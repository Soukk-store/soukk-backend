from soukk_backend.core.tasks.enqueue import enqueue
from soukk_backend.domains.auth import authController


class BrokenQueue:
    """Stands in for a task when Redis is down: publishing raises."""

    name = "broken"

    def apply_async(self, args: tuple, **options) -> None:
        raise ConnectionError("redis is down")


class RecordingQueue:
    name = "recording"

    def __init__(self):
        self.calls = []

    def apply_async(self, args: tuple, **options) -> None:
        self.calls.append((args, options))


async def test_enqueue_publishes_once_without_retries():
    task = RecordingQueue()

    assert await enqueue(task, "a", "b") is True
    assert task.calls == [(("a", "b"), {"retry": False})]


async def test_enqueue_reports_failure_instead_of_raising(caplog):
    assert await enqueue(BrokenQueue(), "a") is False
    assert "Could not queue broken" in caplog.text


async def test_register_succeeds_when_the_queue_is_down(register, monkeypatch):
    monkeypatch.setattr(authController, "send_verification_email_task", BrokenQueue())

    response = await register("new@example.com")

    assert response.status_code == 201


async def test_forgot_password_answers_normally_when_the_queue_is_down(client, verified_user, monkeypatch):
    await verified_user()
    monkeypatch.setattr(authController, "send_password_reset_email_task", BrokenQueue())

    response = await client.post("/auth/forgot-password", json={"email": "user@example.com"})

    assert response.status_code == 202
