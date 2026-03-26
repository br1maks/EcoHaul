from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/verification", tags=["Верификация"])

class SendCodeRequest(BaseModel):
    purpose: Literal["account_verification", "password_reset", "2fa"] = Field(
        "account_verification",
        description="Назначение кода"
    )

class VerifyCodeRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, description="6-значный код")
    purpose: Literal["account_verification", "password_reset", "2fa"] = Field(
        "account_verification",
        description="Назначение кода"
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
    code = VerificationService.generate_code()
    expires_at = VerificationService.get_expiry_time()

    verification_code = VerificationCode(
        user_id=current_user.id,
        code=code,
        email=None,
        telegram_id=current_user.telegram_id,
        purpose=data.purpose,
        expires_at=expires_at,
    )
    db.add(verification_code)
    await db.commit()

    success = await VerificationService.send_code_via_telegram(
        telegram_id=current_user.telegram_id,
        code=code,
        purpose=data.purpose
    )
    sent_to = f"Telegram (ID: {current_user.telegram_id})"

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось отправить код. Попробуйте позже."
        )

    return VerificationResponse(
        success=True,
        message=f"Код отправлен на {sent_to}",
        sent_to=sent_to,
        expires_in_minutes=15
    )

@router.post("/send-code-test", response_model=dict)
async def send_verification_code_test(
    data: SendCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    code = VerificationService.generate_code()
    expires_at = VerificationService.get_expiry_time()

    verification_code = VerificationCode(
        user_id=current_user.id,
        code=code,
        email=None,
        telegram_id=current_user.telegram_id,
        purpose=data.purpose,
        expires_at=expires_at,
    )
    db.add(verification_code)
    await db.commit()

    return {
        "success": True,
        "message": "Код сгенерирован (ТЕСТОВЫЙ РЕЖИМ)",
        "code": code,
        "telegram_id": current_user.telegram_id,
        "expires_in_minutes": 15,
        "purpose": data.purpose
    }

@router.post("/verify-code")
async def verify_code(
    data: VerifyCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(VerificationCode).where(
        VerificationCode.user_id == current_user.id,
        VerificationCode.code == data.code,
        VerificationCode.purpose == data.purpose,
    ).order_by(VerificationCode.created_at.desc())

    result = await db.execute(stmt)
    verification_code = result.scalar_one_or_none()

    if not verification_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Код не найден или неверный"
        )

    if verification_code.attempts >= verification_code.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Превышено количество попыток. Запросите новый код."
        )

    verification_code.increment_attempts()

    if verification_code.is_expired:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код истёк. Запросите новый код."
        )

    if verification_code.is_used:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код уже был использован"
        )

    verification_code.mark_as_used()

    if data.purpose == "account_verification":
        current_user.is_telegram_verified = True

    await db.commit()

    return {
        "success": True,
        "message": "Аккаунт успешно подтверждён!" if data.purpose == "account_verification" else "Код подтверждён!",
        "is_verified": current_user.is_telegram_verified
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
