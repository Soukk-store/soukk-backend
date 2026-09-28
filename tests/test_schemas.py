import pytest
from pydantic import ValidationError

from soukk_backend.domains.auth.authRequestSchema import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)


def register_body(**overrides) -> dict:
    return {
        "first_name": "Test",
        "last_name": "User",
        "email": "user@example.com",
        "phone": "+96170123456",
        "password": "secret123",
        "confirm_password": "secret123",
        **overrides,
    }


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("+96170123456", "+96170123456"),
        ("70123456", "+96170123456"),
        ("070 123 456", "+96170123456"),
        ("03-123-456", "+9613123456"),
        ("+961 81 123 456", "+96181123456"),
    ],
)
def test_phone_is_normalized(raw, normalized):
    assert RegisterRequest(**register_body(phone=raw)).phone == normalized


@pytest.mark.parametrize("phone", ["+96112345678", "12345", "+1 555 123 4567", "+96172123456"])
def test_non_lebanese_mobile_is_rejected(phone):
    with pytest.raises(ValidationError):
        RegisterRequest(**register_body(phone=phone))


def test_email_is_lowercased_and_names_stripped():
    data = RegisterRequest(**register_body(email="User@Example.COM", first_name="  Test "))
    assert data.email == "user@example.com"
    assert data.first_name == "Test"


@pytest.mark.parametrize("password", ["short1", "lettersonly", "12345678"])
def test_weak_password_is_rejected(password):
    with pytest.raises(ValidationError):
        RegisterRequest(**register_body(password=password, confirm_password=password))


def test_mismatched_passwords_are_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(**register_body(confirm_password="different1"))


def test_login_requires_known_login_type():
    LoginRequest(email="a@b.com", password="x", login_type="ios")
    with pytest.raises(ValidationError):
        LoginRequest(email="a@b.com", password="x", login_type="tv")
    with pytest.raises(ValidationError):
        LoginRequest(email="a@b.com", password="x")


def test_reset_and_change_password_apply_the_same_rules():
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="t", password="weakpass", confirm_password="weakpass")
    with pytest.raises(ValidationError):
        ChangePasswordRequest(
            current_password="old", new_password="secret123", confirm_password="other1234", login_type="web"
        )
