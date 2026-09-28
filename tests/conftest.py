import os

# Must run before the app is imported: settings are read once at import time,
# and environment variables take precedence over .env.
os.environ["DB_NAME"] = "soukk_test"

import itertools
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from soukk_backend import app
from soukk_backend.core.rateLimit import limiter
from soukk_backend.database import Base, SessionLocal, engine
from soukk_backend.domains.auth import authController
from soukk_backend.settings import settings

PASSWORD = "secret123"

# Guard against ever wiping a real database.
assert settings.db_name.endswith("_test"), "tests must run against a *_test database"


@pytest.fixture(scope="session", autouse=True)
async def test_database():
    """Create the test database if needed and build the schema from the models."""
    admin_url = engine.url.set(database="postgres")
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": settings.db_name}
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{settings.db_name}"'))
    await admin_engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_state():
    """Every test starts with empty tables and fresh rate-limit counters."""
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users, refresh_tokens CASCADE"))
    limiter.reset()


@pytest.fixture(autouse=True)
def outbox(monkeypatch) -> list[dict]:
    """Capture emails instead of sending them. Autouse, so no test can send real mail."""
    sent: list[dict] = []

    def capture(kind: str):
        async def fake_send(email: str, link: str) -> None:
            token = parse_qs(urlparse(link).query)["token"][0]
            sent.append({"kind": kind, "email": email, "link": link, "token": token})

        return fake_send

    monkeypatch.setattr(authController, "send_verification_email", capture("verify"))
    monkeypatch.setattr(authController, "send_password_reset_email", capture("reset"))
    return sent


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def db():
    async with SessionLocal() as session:
        yield session


_phone_numbers = (f"+96170{n:06d}" for n in itertools.count(1))


@pytest.fixture
def register(client):
    async def _register(email: str = "user@example.com", password: str = PASSWORD, **overrides):
        body = {
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "phone": next(_phone_numbers),
            "password": password,
            "confirm_password": password,
            **overrides,
        }
        return await client.post("/auth/register", json=body)

    return _register


@pytest.fixture
def verified_user(client, register, outbox):
    """Register a user and click their verification link. Returns the email."""

    async def _verified_user(email: str = "user@example.com", password: str = PASSWORD) -> str:
        response = await register(email, password)
        assert response.status_code == 201
        token = [m for m in outbox if m["kind"] == "verify" and m["email"] == email][-1]["token"]
        assert (await client.get("/auth/verify-email", params={"token": token})).status_code == 200
        return email

    return _verified_user


@pytest.fixture
def login(client):
    async def _login(email: str = "user@example.com", password: str = PASSWORD, login_type: str = "web"):
        return await client.post(
            "/auth/login", json={"email": email, "password": password, "login_type": login_type}
        )

    return _login


@pytest.fixture
def logged_in(verified_user, login):
    """Verified user plus a session. Returns the token response body."""

    async def _logged_in(email: str = "user@example.com", login_type: str = "web") -> dict:
        await verified_user(email)
        response = await login(email, login_type=login_type)
        assert response.status_code == 200
        return response.json()

    return _logged_in
