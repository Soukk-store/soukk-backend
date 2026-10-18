import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.database import get_db
from soukk_backend.domains.auth.authDependencies import get_current_user
from soukk_backend.domains.locations import locationService
from soukk_backend.domains.locations.locationExceptions import (
    DefaultLocationConflict,
    LocationLimitReached,
    LocationNotFound,
)
from soukk_backend.domains.locations.locationRequestSchema import (
    CreateLocationRequest,
    UpdateLocationRequest,
)
from soukk_backend.domains.locations.locationResponseSchema import LocationOut
from soukk_backend.domains.locations.locationService import MAX_LOCATIONS_PER_USER
from soukk_backend.domains.users.userModel import User

router = APIRouter(prefix="/users/me/locations", tags=["locations"])

NOT_FOUND = HTTPException(status_code=404, detail="Location not found")


@router.get("", response_model=list[LocationOut])
async def list_locations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    locations = await locationService.list_locations(db, user)
    return [LocationOut.build(location, user) for location in locations]


@router.post("", response_model=LocationOut, status_code=201)
async def create_location(
    data: CreateLocationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        location = await locationService.create_location(db, user, data)
    except LocationLimitReached:
        raise HTTPException(
            status_code=409, detail=f"You can save at most {MAX_LOCATIONS_PER_USER} locations"
        )
    except DefaultLocationConflict:
        raise HTTPException(status_code=409, detail="Locations changed at the same time, try again")
    return LocationOut.build(location, user)


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: uuid.UUID,
    data: UpdateLocationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        location = await locationService.update_location(db, user, location_id, data)
    except LocationNotFound:
        raise NOT_FOUND
    return LocationOut.build(location, user)


@router.post("/{location_id}/default", response_model=LocationOut)
async def set_default(
    location_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        location = await locationService.set_default(db, user, location_id)
    except LocationNotFound:
        raise NOT_FOUND
    except DefaultLocationConflict:
        raise HTTPException(status_code=409, detail="Locations changed at the same time, try again")
    return LocationOut.build(location, user)


@router.delete("/{location_id}", status_code=204)
async def delete_location(
    location_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await locationService.delete_location(db, user, location_id)
    except LocationNotFound:
        raise NOT_FOUND
    return Response(status_code=204)
