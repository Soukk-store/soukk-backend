import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from soukk_backend.core.phone import normalize_lebanese_phone
from soukk_backend.domains.auth.refreshTokenModel import LoginType


PASSWORD_MIN_LENGTH = 8
PASSWORD_RULES = [
    (r"[A-Z]", "one uppercase letter"),
    (r"\d", "one number"),
    (r"[^A-Za-z0-9\s]", "one symbol"),
]


def check_password_strength(value: str) -> str:
    missing = [rule for pattern, rule in PASSWORD_RULES if not re.search(pattern, value)]
    if len(value) < PASSWORD_MIN_LENGTH:
        missing.insert(0, f"{PASSWORD_MIN_LENGTH} characters")
    if missing:
        raise ValueError(f"Password must contain at least {', '.join(missing)}")
    return value


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    phone: str
    password: str
    confirm_password: str

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_lebanese_phone(value)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return check_password_strength(value)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class ResendVerificationRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    login_type: LoginType

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return check_password_strength(value)

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str
    login_type: LoginType

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return check_password_strength(value)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self
