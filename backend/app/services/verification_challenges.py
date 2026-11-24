import base64
import hashlib
import hmac
from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import settings
from app.models import OutboxMessage, User, VerificationCode
from app.services.auth_limits import reserve_attempt
from app.services.verification_service import VerificationService
from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


def delivery_cipher():
    key = hmac.new(
        settings.SECRET_KEY.encode(), b"verification-delivery:v1", hashlib.sha256
    ).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def code_digest(challenge: VerificationCode, code: str):
    context = f"verification-code:v1:{challenge.id}:{challenge.user_id}:{challenge.purpose}:{code}"
    return hmac.new(settings.SECRET_KEY.encode(), context.encode(), hashlib.sha256).hexdigest()


async def issue_challenge(db: AsyncSession, user: User, purpose: str, *, test=False):
    if not test and not settings.TELEGRAM_ENABLED:
        raise HTTPException(status_code=503, detail="Отправка кодов временно недоступна")
    await db.commit()
    await reserve_attempt("verification_send_account", str(user.id), limit=6, seconds=900)
    await reserve_attempt("verification_send_purpose", f"{user.id}:{purpose}", limit=3, seconds=900)
    await reserve_attempt("verification_cooldown", f"{user.id}:{purpose}", limit=1, seconds=60)
    await db.refresh(user, with_for_update=True)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь недоступен")
    await db.execute(
        update(VerificationCode)
        .where(
            VerificationCode.user_id == user.id,
            VerificationCode.purpose == purpose,
            VerificationCode.is_used.is_(False),
        )
        .values(is_used=True, used_at=datetime.now(timezone.utc))
    )
    code = VerificationService.generate_code()
    challenge = VerificationCode(
        id=uuid4(),
        user_id=user.id,
        purpose=purpose,
        telegram_id=user.telegram_id,
        expires_at=VerificationService.get_expiry_time(),
        code_digest="",
    )
    challenge.code_digest = code_digest(challenge, code)
    db.add(challenge)
    if not test:
        text = f"Код EcoHaul: {code}\nДействителен 15 минут. Никому не сообщайте этот код."
        db.add(
            OutboxMessage(
                channel="telegram",
                stream=f"verification:{user.id}:{purpose}",
                payload={
                    "telegram_id": user.telegram_id,
                    "verification_code_id": str(challenge.id),
                    "encrypted_text": delivery_cipher().encrypt(text.encode()).decode(),
                },
            )
        )
    await db.commit()
    return code


async def consume_challenge(db: AsyncSession, user: User, purpose: str, code: str):
    await db.commit()
    await reserve_attempt("verification_check_account", str(user.id), limit=10, seconds=900)
    await db.refresh(user, with_for_update=True)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь недоступен")
    challenge = await db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.user_id == user.id,
            VerificationCode.purpose == purpose,
        )
        .order_by(VerificationCode.created_at.desc(), VerificationCode.id.desc())
        .limit(1)
        .with_for_update(of=VerificationCode)
    )
    if challenge is None or challenge.is_used or challenge.is_expired:
        raise HTTPException(status_code=401, detail="Код не найден, использован или истёк")
    if challenge.attempts >= challenge.max_attempts:
        raise HTTPException(
            status_code=429,
            detail="Попытки исчерпаны. Запросите новый код",
            headers={"Retry-After": "60"},
        )
    challenge.increment_attempts()
    if not hmac.compare_digest(challenge.code_digest, code_digest(challenge, code)):
        await db.commit()
        raise HTTPException(status_code=401, detail="Код не найден или неверен")
    challenge.mark_as_used()
    if purpose == "account_verification":
        user.is_telegram_verified = True
    await db.commit()
