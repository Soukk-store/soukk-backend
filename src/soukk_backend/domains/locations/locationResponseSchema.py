import uuid
from datetime import datetime

from pydantic import BaseModel

from soukk_backend.domains.locations.locationModel import UserLocation
from soukk_backend.domains.users.userModel import User


class LocationOut(BaseModel):
    id: uuid.UUID
    name: str
    district: str
    area: str
    details: str
    floor: str
    latitude: float
    longitude: float
    receiver_phone: str
    is_default: bool
    created_at: datetime

    @classmethod
    def build(cls, location: UserLocation, user: User) -> "LocationOut":
        return cls(
            id=location.id,
            name=location.name,
            district=location.district,
            area=location.area,
            details=location.details,
            floor=location.floor,
            latitude=float(location.latitude),
            longitude=float(location.longitude),
            receiver_phone=location.receiver_phone or user.phone,
            is_default=location.is_default,
            created_at=location.created_at,
        )
