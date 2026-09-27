from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.core.email import send_verification_email
from soukk_backend.database import get_db
from soukk_backend.domains.auth import authService
from soukk_backend.domains.auth.authExceptions import (
    EmailAlreadyExists,
    InvalidVerificationToken,
    PhoneAlreadyExists,
)
from soukk_backend.domains.auth.authRequestSchema import RegisterRequest, ResendVerificationRequest
from soukk_backend.domains.auth.authResponseSchema import (
    EmailExistsResponse,
    MessageResponse,
    RegisterResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/email-exists", response_model=EmailExistsResponse)
async def email_exists(email: EmailStr, db: AsyncSession = Depends(get_db)):
    exists = await authService.email_exists(db, email)
    return EmailExistsResponse(exists=exists)


@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await authService.register(db, data)
    except EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="Email already registered")
    except PhoneAlreadyExists:
        raise HTTPException(status_code=409, detail="Phone number already registered")

    link = authService.build_verification_link(user)
    background_tasks.add_task(send_verification_email, user.email, link)

    return RegisterResponse(message="User created, please verify your account", user=user)


@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    try:
        await authService.verify_email(db, token)
    except InvalidVerificationToken:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    return MessageResponse(message="Email verified")


@router.post("/resend-verification", status_code=202, response_model=MessageResponse)
async def resend_verification(
    data: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await authService.get_unverified_user(db, data.email)
    if user is not None:
        link = authService.build_verification_link(user)
        background_tasks.add_task(send_verification_email, user.email, link)

    return MessageResponse(message="If the account needs verification, an email has been sent")
