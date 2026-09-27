from fastapi import APIRouter, Depends, HTTPException
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from soukk_backend.database import get_db
from soukk_backend.domains.auth import authService
from soukk_backend.domains.auth.authExceptions import EmailAlreadyExists, PhoneAlreadyExists
from soukk_backend.domains.auth.authRequestSchema import RegisterRequest
from soukk_backend.domains.auth.authResponseSchema import EmailExistsResponse, RegisterResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/email-exists", response_model=EmailExistsResponse)
async def email_exists(email: EmailStr, db: AsyncSession = Depends(get_db)):
    exists = await authService.email_exists(db, email)
    return EmailExistsResponse(exists=exists)


@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await authService.register(db, data)
    except EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="Email already registered")
    except PhoneAlreadyExists:
        raise HTTPException(status_code=409, detail="Phone number already registered")

    return RegisterResponse(message="User created, please verify your account", user=user)
