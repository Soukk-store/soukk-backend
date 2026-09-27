from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.core.email import send_password_reset_email, send_verification_email
from soukk_backend.core.rateLimit import limiter
from soukk_backend.database import get_db
from soukk_backend.domains.auth import authService
from soukk_backend.domains.auth.authDependencies import get_current_user
from soukk_backend.domains.auth.authExceptions import (
    EmailAlreadyExists,
    EmailNotVerified,
    InvalidCredentials,
    InvalidToken,
    PhoneAlreadyExists,
)
from soukk_backend.domains.auth.authRequestSchema import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
)
from soukk_backend.domains.auth.authResponseSchema import (
    EmailExistsResponse,
    MessageResponse,
    RegisterResponse,
    TokenResponse,
    UserOut,
)
from soukk_backend.domains.users.userModel import User
from soukk_backend.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/email-exists", response_model=EmailExistsResponse)
@limiter.limit(settings.rate_limit_email_exists)
async def email_exists(request: Request, email: EmailStr, db: AsyncSession = Depends(get_db)):
    exists = await authService.email_exists(db, email)
    return EmailExistsResponse(exists=exists)


@router.post("/register", status_code=201, response_model=RegisterResponse)
@limiter.limit(settings.rate_limit_register)
async def register(
    request: Request,
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
    except InvalidToken:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    return MessageResponse(message="Email verified")


@router.post("/resend-verification", status_code=202, response_model=MessageResponse)
@limiter.limit(settings.rate_limit_resend)
async def resend_verification(
    request: Request,
    data: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await authService.claim_verification_email(db, data.email)
    if user is not None:
        link = authService.build_verification_link(user)
        background_tasks.add_task(send_verification_email, user.email, link)

    return MessageResponse(message="If the account needs verification, an email has been sent")


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_login)
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await authService.login(db, data)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    except EmailNotVerified:
        raise HTTPException(status_code=403, detail="Email not verified")

    return await authService.start_session(db, user, data.login_type)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_refresh)
async def refresh(request: Request, data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await authService.refresh_session(db, data.refresh_token)
    except InvalidToken:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


@router.post("/logout", status_code=204)
@limiter.limit(settings.rate_limit_logout)
async def logout(request: Request, data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await authService.end_session(db, data.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/forgot-password", status_code=202, response_model=MessageResponse)
@limiter.limit(settings.rate_limit_forgot_password)
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await authService.claim_password_reset_email(db, data.email)
    if user is not None:
        link = authService.build_password_reset_link(user)
        background_tasks.add_task(send_password_reset_email, user.email, link)

    return MessageResponse(message="If an account exists for this email, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_reset_password)
async def reset_password(
    request: Request, data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    try:
        await authService.reset_password(db, data.token, data.password)
    except InvalidToken:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    return MessageResponse(message="Password has been reset, please log in again")



@router.post("/change-password", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_change_password)
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await authService.change_password(db, user, data)
    except InvalidCredentials:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
