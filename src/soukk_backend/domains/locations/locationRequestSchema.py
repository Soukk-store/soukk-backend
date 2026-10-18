from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from soukk_backend.core.phone import normalize_lebanese_phone
from soukk_backend.domains.locations.locationEnums import (
    AREAS_BY_DISTRICT,
    LATITUDE_MAX,
    LATITUDE_MIN,
    LONGITUDE_MAX,
    LONGITUDE_MIN,
    District,
)

COORDINATE_PRECISION = Decimal("0.000001")

Name = Annotated[str, Field(min_length=1, max_length=50)]
Details = Annotated[str, Field(min_length=1, max_length=500)]
Floor = Annotated[str, Field(min_length=1, max_length=20)]
Latitude = Annotated[Decimal, Field(ge=LATITUDE_MIN, le=LATITUDE_MAX)]
Longitude = Annotated[Decimal, Field(ge=LONGITUDE_MIN, le=LONGITUDE_MAX)]


def check_area(district: District, area: str) -> None:
    if area not in AREAS_BY_DISTRICT[district]:
        raise ValueError(f"Area {area} is not in district {district.value}")


class LocationRequestBase(BaseModel):
    # user_id, is_default and the like are never accepted from the client.
    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "details", "floor", mode="before", check_fields=False)
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("latitude", "longitude", check_fields=False)
    @classmethod
    def round_coordinate(cls, value: Decimal | None) -> Decimal | None:
        # GPS gives more digits than the column keeps; ~10 cm is plenty for delivery.
        return value.quantize(COORDINATE_PRECISION) if value is not None else None

    @field_validator("receiver_phone", check_fields=False)
    @classmethod
    def validate_receiver_phone(cls, value: str | None) -> str | None:
        return normalize_lebanese_phone(value) if value is not None else None


class CreateLocationRequest(LocationRequestBase):
    name: Name
    district: District
    area: str
    details: Details
    floor: Floor
    latitude: Latitude
    longitude: Longitude
    receiver_phone: str | None = None

    @model_validator(mode="after")
    def area_in_district(self) -> "CreateLocationRequest":
        check_area(self.district, self.area)
        return self


class UpdateLocationRequest(LocationRequestBase):
    """Partial update: only the fields sent are changed. receiver_phone: null
    goes back to the account phone; no other field can be cleared."""

    name: Name | None = None
    district: District | None = None
    area: str | None = None
    details: Details | None = None
    floor: Floor | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    receiver_phone: str | None = None

    @model_validator(mode="after")
    def validate_partial(self) -> "UpdateLocationRequest":
        cleared = [
            field
            for field in self.model_fields_set - {"receiver_phone"}
            if getattr(self, field) is None
        ]
        if cleared:
            raise ValueError(f"{', '.join(sorted(cleared))} cannot be null")
        # Sent together, so the area is always checked against the district it ends up in.
        if ("district" in self.model_fields_set) != ("area" in self.model_fields_set):
            raise ValueError("district and area must be sent together")
        if self.district is not None and self.area is not None:
            check_area(self.district, self.area)
        return self
