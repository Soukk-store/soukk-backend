import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.domains.locations.locationModel import UserLocation
from soukk_backend.domains.users.userModel import User

# Every query here is scoped to an owner: there is deliberately no way to
# fetch a location by id alone.


def _owned_by(user_id: uuid.UUID):
    return (UserLocation.user_id == user_id) & UserLocation.deleted_at.is_(None)


async def lock_owner(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Serialize location writes per user until the transaction ends, so two
    requests can't both pass the limit or fight over the default."""
    await db.execute(select(User.id).where(User.id == user_id).with_for_update())


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[UserLocation]:
    result = await db.execute(
        select(UserLocation)
        .where(_owned_by(user_id))
        .order_by(UserLocation.is_default.desc(), UserLocation.created_at.desc())
    )
    return list(result.scalars())


async def get_for_user(
    db: AsyncSession, location_id: uuid.UUID, user_id: uuid.UUID
) -> UserLocation | None:
    result = await db.execute(
        select(UserLocation).where(UserLocation.id == location_id, _owned_by(user_id))
    )
    return result.scalar_one_or_none()


async def count_for_user(db: AsyncSession, user_id: uuid.UUID) -> int:
    return await db.scalar(select(func.count()).select_from(UserLocation).where(_owned_by(user_id)))


async def latest_for_user(db: AsyncSession, user_id: uuid.UUID) -> UserLocation | None:
    result = await db.execute(
        select(UserLocation)
        .where(_owned_by(user_id))
        .order_by(UserLocation.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, user_id: uuid.UUID, is_default: bool, **fields) -> UserLocation:
    location = UserLocation(user_id=user_id, is_default=is_default, **fields)
    db.add(location)
    await db.flush()
    return location


async def clear_default(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(UserLocation)
        .where(UserLocation.user_id == user_id, UserLocation.is_default.is_(True))
        .values(is_default=False)
    )
