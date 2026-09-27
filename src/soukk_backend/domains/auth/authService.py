from datetime import UTC, datetime, timedelta

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.core.security import (
    ACCESS_PURPOSE,
    EMAIL_VERIFY_PURPOSE,
    PASSWORD_RESET_PURPOSE,
    REFRESH_PURPOSE,
    create_token,
    decode_claims,
    decode_token,
    decode_token_id,
    hash_password,
    password_fingerprint,
    verify_password,
)
from soukk_backend.domains.auth import authRepository
from soukk_backend.domains.auth.authExceptions import (
    EmailAlreadyExists,
    EmailNotVerified,
    InvalidCredentials,
    InvalidToken,
    PhoneAlreadyExists,
)
from soukk_backend.domains.auth.authRequestSchema import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
)
from soukk_backend.domains.auth.authResponseSchema import TokenResponse
from soukk_backend.domains.auth.refreshTokenModel import RefreshToken
from soukk_backend.domains.users.userModel import User
from soukk_backend.settings import settings


async def email_exists(db: AsyncSession, email: str) -> bool:
    return await authRepository.get_by_email(db, email.lower()) is not None


async def register(db: AsyncSession, data: RegisterRequest) -> User:
    if await authRepository.get_by_email(db, data.email):
        raise EmailAlreadyExists()
    if await authRepository.get_by_phone(db, data.phone):
        raise PhoneAlreadyExists()

    # Argon2 hashing is CPU-heavy; run it off the event loop so it
    # doesn't block other requests while it runs.
    hashed_password = await run_in_threadpool(hash_password, data.password)

    try:
        return await authRepository.create_user(
            db,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            hashed_password=hashed_password,
        )
    except IntegrityError as error:
        # Two concurrent registrations can both pass the checks above
        # and then race on the database's unique constraints.
        await db.rollback()
        constraint = str(error.orig)
        if "email" in constraint:
            raise EmailAlreadyExists() from error
        if "phone" in constraint:
            raise PhoneAlreadyExists() from error
        raise


def build_verification_link(user: User) -> str:
    token = create_token(
        user.id, EMAIL_VERIFY_PURPOSE, timedelta(minutes=settings.email_verify_expire_minutes)
    )
    return f"{settings.frontend_url}/verified?token={token}"


async def verify_email(db: AsyncSession, token: str) -> User:
    user_id = decode_token(token, EMAIL_VERIFY_PURPOSE)
    user = await authRepository.get_by_id(db, user_id)
    if user is None:
        raise InvalidToken()
    if user.is_active:
        return user
    return await authRepository.activate_user(db, user)


async def claim_verification_email(db: AsyncSession, email: str) -> User | None:
    """Return the user if a verification email should be sent now, else None."""
    user = await authRepository.get_by_email(db, email)
    if user is None or user.is_active:
        return None
    if not await _claim_email_slot(db, user, User.verification_email_sent_at):
        return None
    return user


async def claim_password_reset_email(db: AsyncSession, email: str) -> User | None:
    """Return the user if a password reset email should be sent now, else None."""
    user = await authRepository.get_by_email(db, email)
    if user is None:
        return None
    if not await _claim_email_slot(db, user, User.password_reset_email_sent_at):
        return None
    return user


async def _claim_email_slot(db: AsyncSession, user: User, sent_at_column) -> bool:
    cooldown = timedelta(seconds=settings.email_cooldown_seconds)
    return await authRepository.claim_email_slot(db, user.id, sent_at_column, cooldown)


def build_password_reset_link(user: User) -> str:
    token = create_token(
        user.id,
        PASSWORD_RESET_PURPOSE,
        timedelta(minutes=settings.password_reset_expire_minutes),
        fingerprint=password_fingerprint(user.hashed_password),
    )
    return f"{settings.frontend_url}/reset-password?token={token}"


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    user_id = decode_token(token, PASSWORD_RESET_PURPOSE)
    user = await authRepository.get_by_id(db, user_id)
    if user is None:
        raise InvalidToken()

    claims = decode_claims(token, PASSWORD_RESET_PURPOSE)
    if claims.get("pwd") != password_fingerprint(user.hashed_password):
        raise InvalidToken()

    hashed_password = await run_in_threadpool(hash_password, new_password)
    # Whoever knew the old password may still hold a session, so end them all.
    await authRepository.update_password_and_revoke_sessions(db, user, hashed_password)


async def change_password(
    db: AsyncSession, user: User, data: ChangePasswordRequest
) -> TokenResponse:
    if not await run_in_threadpool(verify_password, data.current_password, user.hashed_password):
        raise InvalidCredentials()

    hashed_password = await run_in_threadpool(hash_password, data.new_password)
    # End every session, then give the device that made the change a fresh
    # one, so it stays logged in while all other devices are logged out.
    await authRepository.update_password_and_revoke_sessions(db, user, hashed_password)
    return await start_session(db, user, data.login_type)


async def login(db: AsyncSession, data: LoginRequest) -> User:
    user = await authRepository.get_by_email(db, data.email)
    if user is None:
        raise InvalidCredentials()

    # Argon2 verification is CPU-heavy, same as hashing in register().
    if not await run_in_threadpool(verify_password, data.password, user.hashed_password):
        raise InvalidCredentials()

    if not user.is_active:
        raise EmailNotVerified()
    return user


async def start_session(db: AsyncSession, user: User, login_type: str) -> TokenResponse:
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    stored = await authRepository.create_refresh_token(db, user.id, login_type, expires_at)
    return _build_tokens(user, stored)


async def refresh_session(db: AsyncSession, refresh_token: str) -> TokenResponse:
    token_id = decode_token_id(refresh_token, REFRESH_PURPOSE)
    stored = await authRepository.get_refresh_token_for_update(db, token_id)
    if stored is None:
        raise InvalidToken()

    if stored.revoked_at is not None:
        # An already-rotated token being used again means it was probably
        # stolen, so end the whole session for both the thief and the owner.
        await authRepository.revoke_family(db, stored.family_id)
        raise InvalidToken()

    user = await authRepository.get_by_id(db, stored.user_id)
    if user is None or not user.is_active:
        raise InvalidToken()

    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    new_stored = await authRepository.rotate_refresh_token(db, stored, expires_at)
    return _build_tokens(user, new_stored)


async def end_session(db: AsyncSession, refresh_token: str) -> None:
    try:
        token_id = decode_token_id(refresh_token, REFRESH_PURPOSE)
    except InvalidToken:
        return
    stored = await authRepository.get_refresh_token_for_update(db, token_id)
    if stored is not None:
        await authRepository.revoke_family(db, stored.family_id)


def _build_tokens(user: User, stored: RefreshToken) -> TokenResponse:
    access_token = create_token(
        user.id, ACCESS_PURPOSE, timedelta(minutes=settings.access_token_expire_minutes)
    )
    refresh_token = create_token(
        user.id, REFRESH_PURPOSE, stored.expires_at - datetime.now(UTC), token_id=stored.id
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def get_user_from_token(db: AsyncSession, token: str, purpose: str) -> User:
    user_id = decode_token(token, purpose)
    user = await authRepository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise InvalidToken()
    return user
