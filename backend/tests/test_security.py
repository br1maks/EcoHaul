import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
from uuid import uuid4

import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password,
    validate_telegram_init_data, verify_password, verify_telegram_auth_date,
)


def signed_data(auth_date=None, **extra):
    values = {"auth_date": str(auth_date if auth_date is not None else int(time.time())),
              "user": json.dumps({"id": 12345, "first_name": "Test"}), **extra}
    key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    signature = hmac.new(key, "\n".join(f"{k}={v}" for k, v in sorted(values.items())).encode(), hashlib.sha256).hexdigest()
    return urlencode({**values, "hash": signature})


def test_valid_telegram_signature_and_user():
    valid, user, error = validate_telegram_init_data(signed_data())
    assert valid and user["id"] == 12345 and error is None


@pytest.mark.parametrize("age", [86401, -3600])
def test_reject_expired_and_future_telegram_data(age):
    valid, user, error = validate_telegram_init_data(signed_data(int(time.time()) - age))
    assert not valid and user is None


def test_reject_tampered_telegram_user():
    assert not validate_telegram_init_data(signed_data().replace("12345", "99999"))[0]


@pytest.mark.parametrize("value", ["", "auth_date=invalid", "auth_date=-1"])
def test_reject_invalid_auth_date(value):
    assert not verify_telegram_auth_date(value)


def test_password_salted_and_verified():
    first, second = hash_password("correct-horse"), hash_password("correct-horse")
    assert first != second
    assert verify_password("correct-horse", first)
    assert not verify_password("wrong", first)


def test_tokens_have_distinct_purposes():
    user_id = str(uuid4())
    access = decode_token(create_access_token(user_id, "CLIENT"))
    refresh = decode_token(create_refresh_token(user_id))
    assert access["sub"] == refresh["sub"] == user_id
    assert access["type"] == "access" and refresh["type"] == "refresh"
    assert decode_token("invalid.token") is None


def test_new_password_hash_does_not_truncate_long_unicode_input():
    password = 'я' * 72 + 'one'
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password('я' * 72 + 'two', hashed)


def test_legacy_bcrypt_record_remains_verifiable():
    import bcrypt
    legacy = bcrypt.hashpw(b'legacy-password', bcrypt.gensalt()).decode()
    assert verify_password('legacy-password', legacy)
    assert not verify_password('wrong', legacy)
