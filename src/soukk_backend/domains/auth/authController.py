from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.core.rateLimit import limiter
from soukk_backend.core.tasks.emailTask import (
    send_password_reset_email_task,
    send_verification_email_task,
)
from soukk_backend.core.tasks.enqueue import enqueue
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
from soukk_backend.settings.appSettings import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# The refresh token lives only in this HttpOnly cookie, out of reach of the
# page's JavaScript. It is sent only to /auth routes.
REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/auth"


def send_tokens(response: Response, tokens: authService.SessionTokens) -> TokenResponse:
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return TokenResponse(access_token=tokens.access_token)


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True, secure=True, samesite="lax"
    )


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
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await authService.register(db, data)
    except EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="Email already registered")
    except PhoneAlreadyExists:
        raise HTTPException(status_code=409, detail="Phone number already registered")

    link = authService.build_verification_link(user)
    await enqueue(send_verification_email_task, user.email, user.first_name, link)

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
    db: AsyncSession = Depends(get_db),
):
    user = await authService.claim_verification_email(db, data.email)
    if user is not None:
        link = authService.build_verification_link(user)
        await enqueue(send_verification_email_task, user.email, user.first_name, link)

    return MessageResponse(message="If the account needs verification, an email has been sent")


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_login)
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await authService.login(db, data)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    except EmailNotVerified:
        raise HTTPException(status_code=403, detail="Email not verified")

    return send_tokens(response, await authService.start_session(db, user, data.login_type))


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_refresh)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    try:
        tokens = await authService.refresh_session(db, refresh_token)
    except InvalidToken:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return send_tokens(response, tokens)


@router.post("/logout", status_code=204)
@limiter.limit(settings.rate_limit_logout)
async def logout(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token is not None:
        await authService.end_session(db, refresh_token)
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/forgot-password", status_code=202, response_model=MessageResponse)
@limiter.limit(settings.rate_limit_forgot_password)
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await authService.claim_password_reset_email(db, data.email)
    if user is not None:
        link = authService.build_password_reset_link(user)
        await enqueue(send_password_reset_email_task, user.email, user.first_name, link)

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
    response: Response,
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        tokens = await authService.change_password(db, user, data)
    except InvalidCredentials:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    return send_tokens(response, tokens)
