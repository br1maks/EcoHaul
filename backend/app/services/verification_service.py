
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx

from app.core.config import settings

class VerificationService:

    CODE_LENGTH = 6
    CODE_EXPIRY_MINUTES = 15

    @staticmethod
    def generate_code() -> str:
        return ''.join(secrets.choice(string.digits) for _ in range(VerificationService.CODE_LENGTH))

    @staticmethod
    async def send_code_via_email(
        email: str,
        code: str,
        purpose: Literal["account_verification", "password_reset", "2fa"] = "account_verification"
    ) -> bool:
        try:
            if purpose == "account_verification":
                subject = "Подтверждение аккаунта - EcoHaul"
                body = f"""
Добро пожаловать в EcoHaul!

Ваш код подтверждения аккаунта: {code}

Код действителен в течение 15 минут.

Если вы не регистрировались в EcoHaul, проигнорируйте это письмо.
                """
            elif purpose == "password_reset":
                subject = "Восстановление доступа - EcoHaul"
                body = f"""
Запрошено восстановление доступа к вашему аккаунту EcoHaul.

Ваш код восстановления: {code}

Код действителен в течение 15 минут.

Если вы не запрашивали восстановление доступа, проигнорируйте это письмо.
                """
            else:
                subject = "Код двухфакторной аутентификации - EcoHaul"
                body = f"""
Ваш код для входа в EcoHaul: {code}

Код действителен в течение 15 минут.
                """

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = settings.SMTP_FROM_EMAIL
            message["To"] = email

            text_part = MIMEText(body, "plain", "utf-8")
            message.attach(text_part)

            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_USE_TLS,
            )

            return True

        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    @staticmethod
    async def send_code_via_telegram(
        telegram_id: int,
        code: str,
        purpose: Literal["account_verification", "password_reset", "2fa"] = "account_verification"
    ) -> bool:
        try:
            if purpose == "account_verification":
                text = f"""
🔐 *Подтверждение аккаунта*

Ваш код подтверждения: `{code}`

Код действителен 15 минут.
                """
            elif purpose == "password_reset":
                text = f"""
🔑 *Восстановление доступа*

Ваш код восстановления: `{code}`

Код действителен 15 минут.
                """
            else:
                text = f"""
🔐 *Код для входа*

Ваш код: `{code}`

Код действителен 15 минут.
                """

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": telegram_id,
                        "text": text.strip(),
                        "parse_mode": "Markdown"
                    },
                    timeout=10.0
                )

                return response.status_code == 200

        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False

    @staticmethod
    def get_expiry_time() -> datetime:
        return datetime.now(timezone.utc) + timedelta(
            minutes=VerificationService.CODE_EXPIRY_MINUTES
        )
