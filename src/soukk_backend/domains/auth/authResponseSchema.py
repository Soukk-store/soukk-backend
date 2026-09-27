import uuid
from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str
    is_active: bool
    created_at: datetime


class RegisterResponse(BaseModel):
    message: str
    user: UserOut


class EmailExistsResponse(BaseModel):
    exists: bool


class MessageResponse(BaseModel):
    message: str
