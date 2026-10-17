from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.core.rateLimit import limiter
from soukk_backend.database import get_db
from soukk_backend.domains.auth.authDependencies import get_current_user
from soukk_backend.domains.auth.authResponseSchema import UserOut
from soukk_backend.domains.users import userService
from soukk_backend.domains.users.userExceptions import ImageTooLarge, InvalidImage
from soukk_backend.domains.users.userModel import User
from soukk_backend.settings.appSettings import settings

router = APIRouter(prefix="/users", tags=["users"])

IMAGE_TOO_LARGE_DETAIL = f"Image must be at most {settings.image_max_bytes // (1024 * 1024)} MB"


@router.put("/me/image", response_model=UserOut)
@limiter.limit(settings.rate_limit_image_upload)
async def update_image(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await userService.update_image(db, user, file)
    except ImageTooLarge:
        raise HTTPException(status_code=413, detail=IMAGE_TOO_LARGE_DETAIL)
    except InvalidImage:
        raise HTTPException(status_code=422, detail="File must be a JPEG, PNG or WebP image")


@router.delete("/me/image", response_model=UserOut)
@limiter.limit(settings.rate_limit_image_upload)
async def remove_image(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await userService.remove_image(db, user)
