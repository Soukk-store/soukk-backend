import asyncio
from datetime import timedelta

from sqlalchemy import func, select, update

from soukk_backend.core.security import EMAIL_VERIFY_PURPOSE, create_token
from soukk_backend.domains.users.userModel import User
from soukk_backend.settings import settings

PASSWORD = "secret123"  # what the conftest fixtures register users with
NEW_PASSWORD = "newpass456"


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def refresh(client, refresh_token: str):
    return await client.post("/auth/refresh", json={"refresh_token": refresh_token})


async def forgot(client, email: str = "user@example.com"):
    return await client.post("/auth/forgot-password", json={"email": email})


async def reset(client, token: str, password: str = NEW_PASSWORD, confirm: str | None = None):
    return await client.post(
        "/auth/reset-password",
        json={"token": token, "password": password, "confirm_password": confirm or password},
    )


def reset_emails(outbox) -> list[dict]:
    return [m for m in outbox if m["kind"] == "reset"]


# --- forgot password ---


async def test_forgot_password_emails_a_frontend_reset_link(client, verified_user, outbox):
    await verified_user()
    response = await forgot(client)

    assert response.status_code == 202
    [email] = reset_emails(outbox)
    assert email["link"].startswith(f"{settings.frontend_url}/reset-password?token=")


async def test_forgot_password_for_unknown_email_sends_nothing(client, outbox):
    response = await forgot(client, "nobody@example.com")
    assert response.status_code == 202
    assert outbox == []


async def test_forgot_password_cooldown(client, verified_user, outbox, db):
    await verified_user()
    await forgot(client)
    await forgot(client)
    assert len(reset_emails(outbox)) == 1

    await db.execute(
        update(User).values(password_reset_email_sent_at=func.now() - timedelta(hours=1))
    )
    await db.commit()
    await forgot(client)
    assert len(reset_emails(outbox)) == 2


async def test_reset_cooldown_is_separate_from_verification_cooldown(client, register, outbox):
    await register()  # starts the verification cooldown
    await forgot(client)
    assert len(reset_emails(outbox)) == 1


async def test_parallel_forgot_requests_send_one_email(client, verified_user, outbox):
    await verified_user()
    await asyncio.gather(*(forgot(client) for _ in range(5)))
    assert len(reset_emails(outbox)) == 1


# --- reset password ---


async def test_reset_password_changes_password_and_logs_out_everywhere(
    client, logged_in, login, outbox
):
    tokens = await logged_in()
    await forgot(client)

    response = await reset(client, reset_emails(outbox)[0]["token"])

    assert response.status_code == 200
    assert (await login(password=PASSWORD)).status_code == 401
    assert (await login(password=NEW_PASSWORD)).status_code == 200
    assert (await refresh(client, tokens["refresh_token"])).status_code == 401


async def test_reset_link_works_only_once(client, verified_user, outbox):
    await verified_user()
    await forgot(client)
    token = reset_emails(outbox)[0]["token"]

    assert (await reset(client, token)).status_code == 200
    assert (await reset(client, token, "another789")).status_code == 400


async def test_reset_rejects_garbage_and_wrong_purpose_tokens(client, verified_user, db):
    await verified_user()
    user = await db.scalar(select(User))
    verify_token = create_token(user.id, EMAIL_VERIFY_PURPOSE, timedelta(minutes=5))

    assert (await reset(client, "garbage")).status_code == 400
    assert (await reset(client, verify_token)).status_code == 400


async def test_reset_validates_the_new_password(client, verified_user, outbox):
    await verified_user()
    await forgot(client)
    token = reset_emails(outbox)[0]["token"]

    assert (await reset(client, token, "weakpass")).status_code == 422
    assert (await reset(client, token, NEW_PASSWORD, "different1")).status_code == 422


# --- change password ---


def change_body(current: str = PASSWORD, new: str = NEW_PASSWORD, login_type: str = "web") -> dict:
    return {
        "current_password": current,
        "new_password": new,
        "confirm_password": new,
        "login_type": login_type,
    }


async def test_change_password_requires_login(client):
    response = await client.post("/auth/change-password", json=change_body())
    assert response.status_code == 401


async def test_change_password_rejects_wrong_current_password(client, logged_in):
    tokens = await logged_in()
    response = await client.post(
        "/auth/change-password",
        json=change_body(current="wrong1234"),
        headers=bearer(tokens["access_token"]),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"


async def test_change_password_keeps_this_device_and_logs_out_others(client, logged_in, login):
    web = await logged_in(login_type="web")
    ios = (await login(login_type="ios")).json()

    response = await client.post(
        "/auth/change-password", json=change_body(), headers=bearer(web["access_token"])
    )

    assert response.status_code == 200
    new_tokens = response.json()
    assert (await refresh(client, new_tokens["refresh_token"])).status_code == 200
    assert (await refresh(client, web["refresh_token"])).status_code == 401
    assert (await refresh(client, ios["refresh_token"])).status_code == 401
    assert (await login(password=NEW_PASSWORD)).status_code == 200
