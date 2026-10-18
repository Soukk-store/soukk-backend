import uuid

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.domains.locations import locationRepository
from soukk_backend.domains.locations.locationExceptions import (
    DefaultLocationConflict,
    LocationLimitReached,
    LocationNotFound,
)
from soukk_backend.domains.locations.locationModel import UserLocation
from soukk_backend.domains.locations.locationRequestSchema import (
    CreateLocationRequest,
    UpdateLocationRequest,
)
from soukk_backend.domains.users.userModel import User

MAX_LOCATIONS_PER_USER = 20


async def list_locations(db: AsyncSession, user: User) -> list[UserLocation]:
    return await locationRepository.list_for_user(db, user.id)


async def create_location(db: AsyncSession, user: User, data: CreateLocationRequest) -> UserLocation:
    await locationRepository.lock_owner(db, user.id)
    count = await locationRepository.count_for_user(db, user.id)
    if count >= MAX_LOCATIONS_PER_USER:
        await db.rollback()
        raise LocationLimitReached()

    location = await locationRepository.create(
        db,
        user.id,
        # The first location is the one checkout should pick.
        is_default=count == 0,
        name=data.name,
        district=data.district.value,
        area=data.area,
        details=data.details,
        floor=data.floor,
        latitude=data.latitude,
        longitude=data.longitude,
        receiver_phone=data.receiver_phone,
    )
    return await _commit(db, location)


async def update_location(
    db: AsyncSession, user: User, location_id: uuid.UUID, data: UpdateLocationRequest
) -> UserLocation:
    location = await _get_owned(db, user, location_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "district":
            value = value.value
        setattr(location, field, value)
    return await _commit(db, location)


async def set_default(db: AsyncSession, user: User, location_id: uuid.UUID) -> UserLocation:
    await locationRepository.lock_owner(db, user.id)
    # Ownership is checked before anything is written.
    location = await _get_owned(db, user, location_id)
    if not location.is_default:
        await locationRepository.clear_default(db, user.id)
        location.is_default = True
    # Commit even when nothing changed: it releases the lock, and unlike a
    # rollback it doesn't expire the objects the response is built from.
    return await _commit(db, location)


async def delete_location(db: AsyncSession, user: User, location_id: uuid.UUID) -> None:
    await locationRepository.lock_owner(db, user.id)
    location = await _get_owned(db, user, location_id)

    # Soft delete: past orders may still point at this row.
    was_default = location.is_default
    location.deleted_at = func.now()
    location.is_default = False
    await db.flush()

    if was_default:
        replacement = await locationRepository.latest_for_user(db, user.id)
        if replacement is not None:
            replacement.is_default = True
    await _commit(db, None)


async def _get_owned(db: AsyncSession, user: User, location_id: uuid.UUID) -> UserLocation:
    location = await locationRepository.get_for_user(db, location_id, user.id)
    if location is None:
        # Same answer whether it doesn't exist or belongs to someone else.
        await db.rollback()
        raise LocationNotFound()
    return location


async def _commit(db: AsyncSession, location: UserLocation | None) -> UserLocation | None:
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        if "uq_user_locations_one_default" in str(error.orig):
            raise DefaultLocationConflict() from error
        raise
    if location is not None:
        await db.refresh(location)
    return location
