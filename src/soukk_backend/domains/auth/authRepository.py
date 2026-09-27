import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.domains.auth.refreshTokenModel import RefreshToken
from soukk_backend.domains.users.userModel import User


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    hashed_password: str,
) -> User:
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        hashed_password=hashed_password,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def activate_user(db: AsyncSession, user: User) -> User:
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user


async def create_refresh_token(
    db: AsyncSession, user_id: uuid.UUID, login_type: str, expires_at: datetime
) -> RefreshToken:
    token_id = uuid.uuid4()
    token = RefreshToken(
        id=token_id,
        user_id=user_id,
        family_id=token_id,
        login_type=login_type,
        expires_at=expires_at,
    )
    db.add(token)
    await db.commit()
    return token


async def get_refresh_token_for_update(db: AsyncSession, token_id: uuid.UUID) -> RefreshToken | None:
    # Row lock so two concurrent refreshes with the same token can't both rotate it.
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.id == token_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def rotate_refresh_token(
    db: AsyncSession, old: RefreshToken, expires_at: datetime
) -> RefreshToken:
    old.revoked_at = func.now()
    new = RefreshToken(
        user_id=old.user_id,
        family_id=old.family_id,
        parent_id=old.id,
        login_type=old.login_type,
        expires_at=expires_at,
    )
    db.add(new)
    await db.commit()
    return new


async def revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=func.now())
    )
    await db.commit()


async def update_password_and_revoke_sessions(
    db: AsyncSession, user: User, hashed_password: str
) -> None:
    user.hashed_password = hashed_password
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=func.now())
    )
    await db.commit()
