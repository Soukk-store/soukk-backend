import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from soukk_backend.domains.auth.authExceptions import InvalidVerificationToken
from soukk_backend.settings import settings

password_hash = PasswordHash.recommended()

EMAIL_VERIFY_PURPOSE = "email_verify"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_email_verification_token(user_id: uuid.UUID) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.email_verify_expire_minutes)
    payload = {"sub": str(user_id), "purpose": EMAIL_VERIFY_PURPOSE, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_email_verification_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        # The purpose claim stops other tokens (e.g. future login tokens)
        # signed with the same secret from being used to verify an email.
        if payload.get("purpose") != EMAIL_VERIFY_PURPOSE:
            raise InvalidVerificationToken()
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as error:
        raise InvalidVerificationToken() from error
