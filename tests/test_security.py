import uuid
from datetime import timedelta

import jwt
import pytest

from soukk_backend.core.security import (
    ACCESS_PURPOSE,
    PASSWORD_RESET_PURPOSE,
    REFRESH_PURPOSE,
    create_token,
    decode_claims,
    decode_token,
    decode_token_id,
    hash_password,
    password_fingerprint,
    verify_password,
)
from soukk_backend.domains.auth.authExceptions import InvalidToken
from soukk_backend.settings import settings

USER_ID = uuid.uuid4()
ONE_HOUR = timedelta(hours=1)


def test_password_hash_verifies_only_the_right_password():
    hashed = hash_password("Secret123!")
    assert hashed != "Secret123!"
    assert verify_password("Secret123!", hashed)
    assert not verify_password("wrong123", hashed)


def test_token_round_trip_returns_user_id():
    token = create_token(USER_ID, ACCESS_PURPOSE, ONE_HOUR)
    assert decode_token(token, ACCESS_PURPOSE) == USER_ID


def test_token_id_round_trip():
    token_id = uuid.uuid4()
    token = create_token(USER_ID, REFRESH_PURPOSE, ONE_HOUR, token_id=token_id)
    assert decode_token_id(token, REFRESH_PURPOSE) == token_id


def test_token_without_id_is_rejected_when_id_expected():
    token = create_token(USER_ID, REFRESH_PURPOSE, ONE_HOUR)
    with pytest.raises(InvalidToken):
        decode_token_id(token, REFRESH_PURPOSE)


@pytest.mark.parametrize(
    ("created_as", "used_as"),
    [(REFRESH_PURPOSE, ACCESS_PURPOSE), (ACCESS_PURPOSE, REFRESH_PURPOSE), (ACCESS_PURPOSE, PASSWORD_RESET_PURPOSE)],
)
def test_token_is_rejected_for_another_purpose(created_as, used_as):
    token = create_token(USER_ID, created_as, ONE_HOUR, token_id=uuid.uuid4())
    with pytest.raises(InvalidToken):
        decode_token(token, used_as)


def test_expired_token_is_rejected():
    token = create_token(USER_ID, ACCESS_PURPOSE, timedelta(seconds=-1))
    with pytest.raises(InvalidToken):
        decode_token(token, ACCESS_PURPOSE)


def test_tampered_token_is_rejected():
    header, _, signature = create_token(USER_ID, ACCESS_PURPOSE, ONE_HOUR).split(".")
    _, other_payload, _ = create_token(uuid.uuid4(), ACCESS_PURPOSE, ONE_HOUR).split(".")
    with pytest.raises(InvalidToken):
        decode_token(f"{header}.{other_payload}.{signature}", ACCESS_PURPOSE)


def test_token_signed_with_another_secret_is_rejected():
    forged = jwt.encode(
        {"sub": str(USER_ID), "purpose": ACCESS_PURPOSE},
        "not-the-real-secret-but-long-enough-for-hs256",
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidToken):
        decode_token(forged, ACCESS_PURPOSE)


def test_garbage_is_rejected():
    with pytest.raises(InvalidToken):
        decode_token("not-a-jwt", ACCESS_PURPOSE)


def test_fingerprint_is_carried_in_claims():
    token = create_token(USER_ID, PASSWORD_RESET_PURPOSE, ONE_HOUR, fingerprint="abc")
    assert decode_claims(token, PASSWORD_RESET_PURPOSE)["pwd"] == "abc"


def test_fingerprint_changes_when_password_changes():
    assert password_fingerprint(hash_password("Secret123!")) != password_fingerprint(
        hash_password("other1234")
    )
