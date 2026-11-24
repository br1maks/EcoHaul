from typing import Literal, Optional

from app.api.dependencies import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.verification_challenges import consume_challenge, issue_challenge
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/verification", tags=["Верификация"])


class SendCodeRequest(BaseModel):
    purpose: Literal["account_verification", "password_reset", "2fa"] = Field(
        "account_verification", description="Назначение кода"
    )


class VerifyCodeRequest(BaseModel):
    code: str = Field(..., pattern=r"^[0-9]{6}$", description="6-значный код")
    purpose: Literal["account_verification", "password_reset", "2fa"] = Field(
        "account_verification", description="Назначение кода"
    )


class VerificationResponse(BaseModel):
    success: bool
    message: str
    sent_to: Optional[str] = None
    expires_in_minutes: int = 15


@router.post("/send-code", response_model=VerificationResponse)
async def send_verification_code(
    data: SendCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await issue_challenge(db, current_user, data.purpose)
    return VerificationResponse(
        success=True,
        message="Код поставлен в очередь отправки в Telegram",
        sent_to="Telegram",
        expires_in_minutes=15,
    )


@router.post("/send-code-test", response_model=dict)
async def send_verification_code_test(
    data: SendCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not (settings.DEBUG and settings.ENABLE_DEV_AUTH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    code = await issue_challenge(db, current_user, data.purpose, test=True)
    return {
        "success": True,
        "message": "Код сгенерирован (ТЕСТОВЫЙ РЕЖИМ)",
        "code": code,
        "telegram_id": current_user.telegram_id,
        "expires_in_minutes": 15,
        "purpose": data.purpose,
    }


@router.post("/verify-code")
async def verify_code(
    data: VerifyCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await consume_challenge(db, current_user, data.purpose, data.code)
    return {
        "success": True,
        "message": "Код подтверждён",
        "is_verified": current_user.is_telegram_verified,
    }


@router.get("/status")
async def get_verification_status(
    current_user: User = Depends(get_current_active_user),
):
    return {
        "telegram_id": current_user.telegram_id,
        "telegram_username": current_user.telegram_username,
        "is_verified": current_user.is_telegram_verified,
    }
