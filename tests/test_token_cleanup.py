from datetime import timedelta

from celery.schedules import crontab
from sqlalchemy import func, select, update

from soukk_backend.core.celeryApp import celery_app
from soukk_backend.core.tasks.emailTask import send_verification_email_task
from soukk_backend.core.tasks.maintenanceTask import (
    cleanup_refresh_tokens,
    cleanup_refresh_tokens_task,
)
from soukk_backend.domains.auth.refreshTokenModel import RefreshToken
from soukk_backend.settings.maintenanceSettings import maintenance_settings

DAY = timedelta(days=1)


async def token_ids(db) -> list:
    return list((await db.scalars(select(RefreshToken.id).order_by(RefreshToken.created_at))).all())


async def set_token(db, token_id, *, expires_in: timedelta, revoked: bool = False) -> None:
    values = {"expires_at": func.now() + expires_in}
    if revoked:
        values["revoked_at"] = func.now()
    await db.execute(update(RefreshToken).where(RefreshToken.id == token_id).values(values))
    await db.commit()


async def cleanup(batch_size: int = 1000) -> int:
    return await cleanup_refresh_tokens(maintenance_settings.database_url, batch_size)


async def test_deletes_expired_tokens_and_keeps_the_rest(verified_user, login, db):
    await verified_user()
    for _ in range(4):
        await login()
    expired, expired_revoked, revoked, active = await token_ids(db)
    await set_token(db, expired, expires_in=-DAY)
    await set_token(db, expired_revoked, expires_in=-DAY, revoked=True)
    await set_token(db, revoked, expires_in=DAY, revoked=True)
    await set_token(db, active, expires_in=DAY)

    assert await cleanup() == 2

    db.expire_all()
    # The revoked-but-unexpired token stays: reusing it must still be caught as theft.
    assert await token_ids(db) == [revoked, active]


async def test_works_through_a_backlog_in_batches(verified_user, login, db):
    await verified_user()
    for _ in range(5):
        await login()
    for token_id in await token_ids(db):
        await set_token(db, token_id, expires_in=-DAY)

    assert await cleanup(batch_size=2) == 5  # batches of 2, 2, 1

    db.expire_all()
    assert await token_ids(db) == []


async def test_deleting_a_parent_keeps_its_live_child(client, logged_in, db):
    await logged_in()
    await client.post("/auth/refresh")  # the client sends its refresh cookie
    parent, child = await token_ids(db)
    await set_token(db, parent, expires_in=-DAY)

    assert await cleanup() == 1

    db.expire_all()
    remaining = await db.get(RefreshToken, child)
    assert remaining is not None
    assert remaining.parent_id is None


async def test_nothing_to_delete(verified_user, login):
    await verified_user()
    await login()

    assert await cleanup() == 0


def test_maintenance_jobs_use_their_own_queue():
    router = celery_app.amqp.router

    assert router.route({}, cleanup_refresh_tokens_task.name)["queue"].name == "maintenance"
    assert router.route({}, send_verification_email_task.name)["queue"].name == "celery"


def test_beat_schedules_the_cleanup():
    from soukk_backend.core import celeryBeat  # noqa: F401  (sets the schedule on import)
    from soukk_backend.settings.beatSettings import beat_settings

    entry = celery_app.conf.beat_schedule["cleanup-expired-refresh-tokens"]

    assert entry["task"] == cleanup_refresh_tokens_task.name
    assert entry["schedule"] == crontab.from_string(beat_settings.token_cleanup_schedule)
