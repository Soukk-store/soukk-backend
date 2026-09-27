import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from soukk_backend.domains.auth.authExceptions import InvalidToken
from soukk_backend.settings import settings

password_hash = PasswordHash.recommended()

EMAIL_VERIFY_PURPOSE = "email_verify"
ACCESS_PURPOSE = "access"
REFRESH_PURPOSE = "refresh"
PASSWORD_RESET_PURPOSE = "password_reset"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def password_fingerprint(hashed_password: str) -> str:
    # Changes whenever the password changes, so a reset token that carries
    # it stops working once it has been used.
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


def create_token(
    user_id: uuid.UUID,
    purpose: str,
    expires_in: timedelta,
    token_id: uuid.UUID | None = None,
    fingerprint: str | None = None,
) -> str:
    expires_at = datetime.now(UTC) + expires_in
    payload = {"sub": str(user_id), "purpose": purpose, "exp": expires_at}
    if token_id is not None:
        payload["jti"] = str(token_id)
    if fingerprint is not None:
        payload["pwd"] = fingerprint
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, purpose: str) -> uuid.UUID:
    return _read_uuid_claim(decode_claims(token, purpose), "sub")


def decode_token_id(token: str, purpose: str) -> uuid.UUID:
    return _read_uuid_claim(decode_claims(token, purpose), "jti")


def decode_claims(token: str, purpose: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as error:
        raise InvalidToken() from error
    # All tokens share one secret, so the purpose claim is what stops
    # e.g. a refresh token from being used as an access token.
    if payload.get("purpose") != purpose:
        raise InvalidToken()
    return payload


def _read_uuid_claim(payload: dict, claim: str) -> uuid.UUID:
    try:
        return uuid.UUID(payload[claim])
    except (KeyError, ValueError) as error:
        raise InvalidToken() from error
