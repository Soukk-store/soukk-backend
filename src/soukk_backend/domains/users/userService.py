import logging
import uuid

from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.core import storage
from soukk_backend.core.images import OUTPUT_CONTENT_TYPE, process_avatar
from soukk_backend.domains.users import userRepository
from soukk_backend.domains.users.userExceptions import ImageTooLarge
from soukk_backend.domains.users.userModel import User
from soukk_backend.settings.appSettings import settings

logger = logging.getLogger(__name__)


async def update_image(db: AsyncSession, user: User, upload: UploadFile) -> User:
    # Read one byte past the limit: enough to know it's too big without
    # loading the whole file into memory.
    data = await upload.read(settings.image_max_bytes + 1)
    if len(data) > settings.image_max_bytes:
        raise ImageTooLarge()

    # Decoding and resizing are CPU-heavy; keep them off the event loop.
    image = await run_in_threadpool(process_avatar, data, settings.image_size_px)

    # A new key on every upload: the old URL keeps working until the database
    # points at the new one, and no cache can serve the previous image.
    key = f"users/{user.id}/{uuid.uuid4().hex}.webp"
    await storage.put(key, image, OUTPUT_CONTENT_TYPE)

    old_key = user.image
    try:
        user = await userRepository.set_image(db, user, key)
    except Exception:
        await db.rollback()
        await _delete_quietly(key)
        raise

    if old_key is not None:
        await _delete_quietly(old_key)
    return user


async def remove_image(db: AsyncSession, user: User) -> User:
    old_key = user.image
    if old_key is None:
        return user
    user = await userRepository.set_image(db, user, None)
    await _delete_quietly(old_key)
    return user


async def _delete_quietly(key: str) -> None:
    # The database is already right; a leftover object only costs storage,
    # so it must not fail the request.
    try:
        await storage.delete(key)
    except Exception:
        logger.exception("Failed to delete image %s from storage", key)
