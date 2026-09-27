from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.core.security import hash_password
from soukk_backend.domains.auth import authRepository
from soukk_backend.domains.auth.authExceptions import EmailAlreadyExists, PhoneAlreadyExists
from soukk_backend.domains.auth.authRequestSchema import RegisterRequest
from soukk_backend.domains.users.userModel import User


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
