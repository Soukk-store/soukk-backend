from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.domains.users.userModel import User


async def set_image(db: AsyncSession, user: User, key: str | None) -> User:
    user.image = key
    await db.commit()
    await db.refresh(user)
    return user
