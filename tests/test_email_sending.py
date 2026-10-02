import json

import httpx
import pytest

from soukk_backend.core import email
from soukk_backend.core.email import MailServiceBusy, send_verification_email
from soukk_backend.settings.emailWorkerSettings import email_worker_settings


@pytest.fixture
def mail_api(monkeypatch):
    """Answer the mail API calls with `mail_api.status` and record the requests."""
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(handler.status, json={})

    handler.status = 200
    handler.requests = requests
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        email.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    return handler


async def test_email_is_posted_to_the_mail_api(mail_api):
    await send_verification_email("user@example.com", "Test", "http://link")

    [request] = mail_api.requests
    assert str(request.url) == email_worker_settings.mail_api_url
    assert request.headers["authorization"] == f"Bearer {email_worker_settings.mail_api_token}"
    body = json.loads(request.content)
    assert body["from"] == email_worker_settings.mail_from
    assert body["to"] == ["user@example.com"]
    assert body["subject"] == "Confirm your Souk email"
    assert 'href="http://link"' in body["html"]


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_rate_limit_and_server_errors_are_retryable(mail_api, status):
    mail_api.status = status
    with pytest.raises(MailServiceBusy):
        await send_verification_email("user@example.com", "Test", "http://link")


@pytest.mark.parametrize("status", [400, 401, 403])
async def test_client_errors_are_not_retryable(mail_api, status):
    mail_api.status = status
    with pytest.raises(httpx.HTTPStatusError):
        await send_verification_email("user@example.com", "Test", "http://link")
