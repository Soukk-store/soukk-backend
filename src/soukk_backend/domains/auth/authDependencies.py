from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.core.security import ACCESS_PURPOSE
from soukk_backend.database import get_db
from soukk_backend.domains.auth import authService
from soukk_backend.domains.auth.authExceptions import InvalidToken
from soukk_backend.domains.users.userModel import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        return await authService.get_user_from_token(db, credentials.credentials, ACCESS_PURPOSE)
    except InvalidToken:
        raise unauthorized
