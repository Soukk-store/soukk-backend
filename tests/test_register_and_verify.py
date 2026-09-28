from datetime import timedelta

from sqlalchemy import func, select, update

from soukk_backend.core.security import ACCESS_PURPOSE, create_token
from soukk_backend.domains.users.userModel import User
from soukk_backend.settings import settings

RESEND_MESSAGE = "If the account needs verification, an email has been sent"


async def expire_cooldown(db, email: str, column) -> None:
    await db.execute(
        update(User).where(User.email == email).values({column: func.now() - timedelta(hours=1)})
    )
    await db.commit()


async def test_register_creates_inactive_user_and_sends_verification_email(register, outbox):
    response = await register("new@example.com")

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "new@example.com"
    assert response.json()["user"]["is_active"] is False
    assert "password" not in str(response.json())
    assert len(outbox) == 1
    assert outbox[0]["kind"] == "verify"
    assert outbox[0]["link"].startswith(f"{settings.frontend_url}/verified?token=")


async def test_register_rejects_duplicate_email_case_insensitively(register):
    await register("taken@example.com")
    response = await register("TAKEN@example.com")
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


async def test_register_rejects_duplicate_phone(register):
    await register("first@example.com", phone="+96171000001")
    response = await register("second@example.com", phone="071 000 001")
    assert response.status_code == 409
    assert response.json()["detail"] == "Phone number already registered"


async def test_email_exists(client, register):
    await register("taken@example.com")
    taken = await client.get("/auth/email-exists", params={"email": "Taken@Example.com"})
    free = await client.get("/auth/email-exists", params={"email": "free@example.com"})
    assert taken.json() == {"exists": True}
    assert free.json() == {"exists": False}


async def test_verification_link_activates_user_and_can_be_reopened(client, register, outbox, db):
    await register("new@example.com")
    token = outbox[0]["token"]

    first = await client.get("/auth/verify-email", params={"token": token})
    second = await client.get("/auth/verify-email", params={"token": token})

    assert first.status_code == 200
    assert second.status_code == 200
    user = await db.scalar(select(User).where(User.email == "new@example.com"))
    assert user.is_active is True


async def test_verify_rejects_invalid_and_wrong_purpose_tokens(client, register, db):
    await register("new@example.com")
    user = await db.scalar(select(User).where(User.email == "new@example.com"))
    access_token = create_token(user.id, ACCESS_PURPOSE, timedelta(minutes=5))

    for token in ["garbage", access_token]:
        response = await client.get("/auth/verify-email", params={"token": token})
        assert response.status_code == 400


async def test_resend_is_blocked_right_after_register_then_allowed_after_cooldown(
    client, register, outbox, db
):
    await register("new@example.com")

    blocked = await client.post("/auth/resend-verification", json={"email": "new@example.com"})
    assert blocked.status_code == 202
    assert len(outbox) == 1

    await expire_cooldown(db, "new@example.com", User.verification_email_sent_at)
    allowed = await client.post("/auth/resend-verification", json={"email": "new@example.com"})
    assert allowed.json()["message"] == RESEND_MESSAGE
    assert len(outbox) == 2


async def test_resend_sends_nothing_for_unknown_or_verified_users(client, verified_user, outbox, db):
    await verified_user("done@example.com")
    await expire_cooldown(db, "done@example.com", User.verification_email_sent_at)
    outbox.clear()

    for email in ["done@example.com", "nobody@example.com"]:
        response = await client.post("/auth/resend-verification", json={"email": email})
        assert response.status_code == 202
        assert response.json()["message"] == RESEND_MESSAGE
    assert outbox == []
