import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qsl
from uuid import uuid4

import bcrypt
from app.core.config import settings
from jose import JWTError, jwt

PASSWORD_PREFIX = "bcrypt_sha256$"


def hash_password(password: str) -> str:
    prepared = base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())
    return PASSWORD_PREFIX + bcrypt.hashpw(prepared, bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if hashed_password.startswith(PASSWORD_PREFIX):
            prepared = base64.b64encode(hashlib.sha256(plain_password.encode("utf-8")).digest())
            return bcrypt.checkpw(prepared, hashed_password[len(PASSWORD_PREFIX) :].encode("ascii"))
        # Compatibility for existing bcrypt records; migrate after successful login.
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("ascii"))
    except (ValueError, TypeError, UnicodeError):
        return False


def _token(user_id: str, purpose: str, *, session_id=None, role=None, expires_at=None):
    instant = datetime.now(timezone.utc)
    lifetime = (
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        if purpose == "access"
        else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload = {
        "sub": user_id,
        "type": purpose,
        "jti": str(uuid4()),
        "exp": expires_at or instant + lifetime,
        "iat": instant,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    if session_id:
        payload["sid"] = str(session_id)
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: str, role: str, session_id=None) -> str:
    return _token(user_id, "access", session_id=session_id, role=role)


def create_refresh_token(user_id: str, session_id=None, expires_at=None) -> str:
    return _token(user_id, "refresh", session_id=session_id, expires_at=expires_at)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "require_exp": True,
                "require_iat": True,
                "require_sub": True,
                "require_jti": True,
                "require_iss": True,
                "require_aud": True,
            },
        )
    except JWTError:
        return None


def create_tokens(user_id: str, role: str, session_id=None, expires_at=None) -> dict:
    return {
        "access_token": create_access_token(user_id, role, session_id),
        "refresh_token": create_refresh_token(user_id, session_id, expires_at),
        "token_type": "bearer",
    }


def parse_telegram_init_data(init_data: str) -> dict:
    return dict(parse_qsl(init_data))


def verify_telegram_init_data(init_data: str) -> bool:
    try:
        parsed = parse_telegram_init_data(init_data)

        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return False

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

        secret_key = hmac.new(
            key=b"WebAppData", msg=settings.BOT_TOKEN.encode(), digestmod=hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            key=secret_key, msg=data_check_string.encode(), digestmod=hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(calculated_hash, received_hash)

    except Exception:
        return False


def extract_telegram_user(init_data: str) -> Optional[dict]:
    parsed = parse_telegram_init_data(init_data)
    user_json = parsed.get("user")

    if not user_json:
        return None

    try:
        return json.loads(user_json)
    except json.JSONDecodeError:
        return None


def verify_telegram_auth_date(init_data: str, max_age_seconds: int = 300) -> bool:
    try:
        parsed = parse_telegram_init_data(init_data)
        auth_date_str = parsed.get("auth_date")

        if not auth_date_str:
            return False

        auth_date = int(auth_date_str)
        current_time = int(datetime.now(timezone.utc).timestamp())

        return 0 <= (current_time - auth_date) <= max_age_seconds

    except (ValueError, TypeError):
        return False


def validate_telegram_init_data(
    init_data: str, max_age_seconds: int = 300
) -> tuple[bool, Optional[dict], Optional[str]]:
    if not verify_telegram_init_data(init_data):
        return False, None, "Invalid Telegram signature"

    if not verify_telegram_auth_date(init_data, max_age_seconds):
        return False, None, "Telegram data expired"

    user_data = extract_telegram_user(init_data)
    if not user_data:
        return False, None, "No user data in init_data"

    if "id" not in user_data:
        return False, None, "User ID missing"

    return True, user_data, None
