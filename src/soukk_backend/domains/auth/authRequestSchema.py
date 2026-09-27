import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from soukk_backend.domains.auth.refreshTokenModel import LoginType

# Lebanese mobile: +961 then 3 + 6 digits, or 70/71/76/78/79/81 + 6 digits
PHONE_PATTERN = re.compile(r"^\+961(3|70|71|76|78|79|81)\d{6}$")


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    phone: str
    password: str = Field(min_length=8)
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
        phone = value.replace(" ", "").replace("-", "")
        if not phone.startswith("+961"):
            phone = "+961" + phone.removeprefix("0")
        if not PHONE_PATTERN.match(phone):
            raise ValueError("Phone number must be a Lebanese mobile number, e.g. +961 XX XXX XXX")
        return phone

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one digit")
        return value

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


class RefreshRequest(BaseModel):
    refresh_token: str
