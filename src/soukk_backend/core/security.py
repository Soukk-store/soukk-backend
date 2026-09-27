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


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_token(user_id: uuid.UUID, purpose: str, expires_in: timedelta) -> str:
    expires_at = datetime.now(UTC) + expires_in
    payload = {"sub": str(user_id), "purpose": purpose, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, purpose: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        # All tokens share one secret, so the purpose claim is what stops
        # e.g. a refresh token from being used as an access token.
        if payload.get("purpose") != purpose:
            raise InvalidToken()
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as error:
        raise InvalidToken() from error
