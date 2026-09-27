from datetime import timedelta

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.core.security import (
    ACCESS_PURPOSE,
    EMAIL_VERIFY_PURPOSE,
    REFRESH_PURPOSE,
    create_token,
    decode_token,
    hash_password,
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
from soukk_backend.domains.auth.authRequestSchema import LoginRequest, RegisterRequest
from soukk_backend.domains.auth.authResponseSchema import TokenResponse
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
    return f"{settings.server_url}/auth/verify-email?token={token}"


async def verify_email(db: AsyncSession, token: str) -> User:
    user_id = decode_token(token, EMAIL_VERIFY_PURPOSE)
    user = await authRepository.get_by_id(db, user_id)
    if user is None:
        raise InvalidToken()
    if user.is_active:
        return user
    return await authRepository.activate_user(db, user)


async def get_unverified_user(db: AsyncSession, email: str) -> User | None:
    user = await authRepository.get_by_email(db, email)
    if user is None or user.is_active:
        return None
    return user


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


def create_session_tokens(user: User) -> TokenResponse:
    access_token = create_token(
        user.id, ACCESS_PURPOSE, timedelta(minutes=settings.access_token_expire_minutes)
    )
    refresh_token = create_token(
        user.id, REFRESH_PURPOSE, timedelta(days=settings.refresh_token_expire_days)
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def get_user_from_token(db: AsyncSession, token: str, purpose: str) -> User:
    user_id = decode_token(token, purpose)
    user = await authRepository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise InvalidToken()
    return user
