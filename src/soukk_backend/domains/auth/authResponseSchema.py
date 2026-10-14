import uuid
from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from soukk_backend.core import storage
from soukk_backend.settings.appSettings import settings


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str
    is_active: bool
    created_at: datetime
    # Storage key, not a URL; clients get image_url instead.
    image: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def image_url(self) -> str:
        return storage.public_url(self.image or settings.default_image_key)


class RegisterResponse(BaseModel):
    message: str
    user: UserOut


class EmailExistsResponse(BaseModel):
    exists: bool


class MessageResponse(BaseModel):
    message: str


class VerifyEmailResponse(BaseModel):
    message: str
    first_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
