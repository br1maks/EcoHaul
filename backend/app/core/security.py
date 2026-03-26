
import hmac
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qsl

from jose import jwt, JWTError
import bcrypt

from app.core.config import settings

def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')

    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')

    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    hashed_bytes = hashed_password.encode('utf-8')

    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None

def create_tokens(user_id: str, role: str) -> dict:
    return {
        "access_token": create_access_token(user_id, role),
        "refresh_token": create_refresh_token(user_id),
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

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=settings.BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
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

def verify_telegram_auth_date(init_data: str, max_age_seconds: int = 86400) -> bool:
    try:
        parsed = parse_telegram_init_data(init_data)
        auth_date_str = parsed.get("auth_date")

        if not auth_date_str:
            return False

        auth_date = int(auth_date_str)
        current_time = int(datetime.now(timezone.utc).timestamp())

        return (current_time - auth_date) <= max_age_seconds

    except (ValueError, TypeError):
        return False

def validate_telegram_init_data(init_data: str, max_age_seconds: int = 86400) -> tuple[bool, Optional[dict], Optional[str]]:
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
