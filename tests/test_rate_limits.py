import pytest

from soukk_backend.settings.appSettings import settings


def first_limit(limit: str) -> int:
    """'20/minute;200/hour' -> 20: the limit a burst of requests hits first."""
    return int(limit.split(";")[0].split("/")[0])


REGISTER_BODY = {
    "first_name": "Test",
    "last_name": "User",
    "email": "user@example.com",
    "phone": "+96170999999",
    "password": "Secret123!",
    "confirm_password": "Secret123!",
}

# Each request must pass validation: a 422 is rejected before the limiter counts it.
ENDPOINTS = [
    ("GET", "/auth/email-exists?email=a@example.com", None, settings.rate_limit_email_exists),
    ("POST", "/auth/register", REGISTER_BODY, settings.rate_limit_register),
    ("POST", "/auth/resend-verification", {"email": "a@example.com"}, settings.rate_limit_resend),
    (
        "POST",
        "/auth/login",
        {"email": "a@example.com", "password": "x", "login_type": "web"},
        settings.rate_limit_login,
    ),
    ("POST", "/auth/forgot-password", {"email": "a@example.com"}, settings.rate_limit_forgot_password),
    (
        "POST",
        "/auth/reset-password",
        {"token": "x", "password": "Secret123!", "confirm_password": "Secret123!"},
        settings.rate_limit_reset_password,
    ),
    ("POST", "/auth/refresh", {"refresh_token": "x"}, settings.rate_limit_refresh),
    ("POST", "/auth/logout", {"refresh_token": "x"}, settings.rate_limit_logout),
]


@pytest.mark.parametrize(("method", "path", "body", "limit"), ENDPOINTS, ids=[e[1] for e in ENDPOINTS])
async def test_endpoint_is_rate_limited(client, method, path, body, limit):
    allowed = first_limit(limit)

    for _ in range(allowed):
        response = await client.request(method, path, json=body)
        assert response.status_code != 429

    response = await client.request(method, path, json=body)
    assert response.status_code == 429


async def test_change_password_is_rate_limited(client, logged_in):
    tokens = await logged_in()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    body = {
        "current_password": "wrong1234",
        "new_password": "Newpass456!",
        "confirm_password": "Newpass456!",
        "login_type": "web",
    }

    for _ in range(first_limit(settings.rate_limit_change_password)):
        assert (await client.post("/auth/change-password", json=body, headers=headers)).status_code == 400
    response = await client.post("/auth/change-password", json=body, headers=headers)
    assert response.status_code == 429
