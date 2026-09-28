import asyncio
from datetime import timedelta

from sqlalchemy import func, select, update

from soukk_backend.domains.auth.refreshTokenModel import RefreshToken
from soukk_backend.settings.appSettings import settings


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def refresh(client, refresh_token: str):
    return await client.post("/auth/refresh", json={"refresh_token": refresh_token})


async def test_login_returns_tokens(verified_user, login):
    await verified_user()
    response = await login()

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


async def test_login_email_is_case_insensitive(verified_user, login):
    await verified_user("user@example.com")
    assert (await login("USER@Example.com")).status_code == 200


async def test_wrong_password_and_unknown_email_look_the_same(verified_user, login):
    await verified_user()
    wrong_password = await login(password="wrong1234")
    unknown_email = await login("nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_unverified_user_cannot_log_in(register, login):
    await register()
    response = await login()
    assert response.status_code == 403
    assert response.json()["detail"] == "Email not verified"


async def test_me_requires_a_valid_access_token(client, logged_in):
    tokens = await logged_in()

    assert (await client.get("/auth/me", headers=bearer(tokens["access_token"]))).json()[
        "email"
    ] == "user@example.com"
    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.get("/auth/me", headers=bearer(tokens["refresh_token"]))).status_code == 401
    assert (await client.get("/auth/me", headers=bearer("garbage"))).status_code == 401


async def test_refresh_rotates_the_token_within_the_same_family(client, logged_in, db):
    tokens = await logged_in(login_type="ios")

    response = await refresh(client, tokens["refresh_token"])

    assert response.status_code == 200
    rows = (await db.scalars(select(RefreshToken).order_by(RefreshToken.created_at))).all()
    old, new = rows
    assert old.revoked_at is not None
    assert new.revoked_at is None
    assert new.parent_id == old.id
    assert new.family_id == old.family_id == old.id
    assert new.login_type == "ios"


async def test_access_token_cannot_be_used_to_refresh(client, logged_in):
    tokens = await logged_in()
    assert (await refresh(client, tokens["access_token"])).status_code == 401


async def outlive_grace_period(db) -> None:
    """Pretend every rotation happened long ago, past the reuse grace period."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.revoked_at.is_not(None))
        .values(revoked_at=func.now() - timedelta(seconds=settings.refresh_reuse_grace_seconds + 5))
    )
    await db.commit()


async def test_reusing_a_rotated_token_revokes_the_whole_family(client, logged_in, db):
    tokens = await logged_in()
    rotated = (await refresh(client, tokens["refresh_token"])).json()
    await outlive_grace_period(db)

    reuse = await refresh(client, tokens["refresh_token"])
    after_theft = await refresh(client, rotated["refresh_token"])

    assert reuse.status_code == 401
    assert after_theft.status_code == 401


async def test_reuse_on_one_device_does_not_log_out_other_devices(client, logged_in, login, db):
    web = await logged_in(login_type="web")
    ios = (await login(login_type="ios")).json()

    await refresh(client, web["refresh_token"])
    await outlive_grace_period(db)
    await refresh(client, web["refresh_token"])  # reuse: kills the web family

    assert (await refresh(client, ios["refresh_token"])).status_code == 200


async def test_two_tabs_refreshing_at_once_stay_logged_in(client, logged_in):
    tokens = await logged_in()

    responses = await asyncio.gather(
        refresh(client, tokens["refresh_token"]), refresh(client, tokens["refresh_token"])
    )

    assert sorted(r.status_code for r in responses) == [200, 401]
    winner = next(r for r in responses if r.status_code == 200).json()
    # The losing tab's reuse is within the grace period: the session survives.
    assert (await refresh(client, winner["refresh_token"])).status_code == 200


async def test_retry_after_a_lost_response_keeps_the_session(client, logged_in):
    tokens = await logged_in()
    lost = (await refresh(client, tokens["refresh_token"])).json()  # response never arrived

    retry = await refresh(client, tokens["refresh_token"])

    assert retry.status_code == 401
    assert (await refresh(client, lost["refresh_token"])).status_code == 200


async def test_logout_revokes_the_session(client, logged_in):
    tokens = await logged_in()

    response = await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 204
    assert (await refresh(client, tokens["refresh_token"])).status_code == 401


async def test_logout_with_garbage_token_still_succeeds(client):
    response = await client.post("/auth/logout", json={"refresh_token": "garbage"})
    assert response.status_code == 204
