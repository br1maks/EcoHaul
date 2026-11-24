import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from app.core.config import settings
from app.core.database import async_session_maker
from app.core.security import create_access_token, decode_token
from app.models import AuthAttemptBucket, OutboxMessage, User, VerificationCode
from app.services.auth_limits import reserve_attempt
from fastapi import HTTPException
from jose import jwt
from sqlalchemy import select, update

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def sign_in(client, identity=61001, **extra):
    response = await client.post(
        "/api/v1/auth/test",
        json={"telegram_id": identity, "first_name": "Test", "role": "CLIENT", **extra},
    )
    assert response.status_code == 200, response.text
    tokens = response.json()
    return tokens, {"Authorization": "Bearer " + tokens["access_token"]}


async def test_refresh_rotation_replay_revokes_whole_family(client):
    tokens, headers = await sign_in(client)
    rotated = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != tokens["refresh_token"]
    assert (await client.get("/api/v1/users/me", headers=headers)).status_code == 200
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).status_code == 401
    newer = {"Authorization": "Bearer " + rotated.json()["access_token"]}
    assert (await client.get("/api/v1/users/me", headers=newer)).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
        )
    ).status_code == 401


async def test_password_changed_after_verification_cannot_issue_stale_session(client):
    from uuid import UUID

    from app.services.sessions import issue_session

    tokens, _ = await sign_in(client, 74001, password="old-test-password")
    user_id = UUID(decode_token(tokens["access_token"])["sub"])
    async with async_session_maker() as pending_login:
        stale_user = await pending_login.get(User, user_id)
        verified_hash = stale_user.password_hash
        async with async_session_maker() as reset:
            await reset.execute(
                update(User).where(User.id == user_id).values(password_hash="changed-hash")
            )
            await reset.commit()
        with pytest.raises(HTTPException) as error:
            await issue_session(pending_login, stale_user, verified_password_hash=verified_hash)
        assert error.value.status_code == 401


async def test_logout_with_refresh_works_after_access_expired(client):
    tokens, headers = await sign_in(client, 62001)
    claims = jwt.get_unverified_claims(tokens["access_token"])
    claims["exp"] = int(datetime.now(timezone.utc).timestamp()) - 1
    expired = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert (
        await client.get("/api/v1/users/me", headers={"Authorization": "Bearer " + expired})
    ).status_code == 401
    response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 204
    assert (await client.get("/api/v1/users/me", headers=headers)).status_code == 401


async def test_session_owner_can_revoke_only_selected_session(client):
    first, headers = await sign_in(client, 63001)
    second, second_headers = await sign_in(client, 63001)
    foreign, foreign_headers = await sign_in(client, 63002)
    second_id = decode_token(second["access_token"])["sid"]
    assert (
        await client.delete("/api/v1/auth/sessions/" + second_id, headers=foreign_headers)
    ).status_code == 404
    sessions = await client.get("/api/v1/auth/sessions", headers=headers)
    assert sessions.status_code == 200 and len(sessions.json()) == 2
    assert all("refresh_digest" not in item for item in sessions.json())
    assert (
        await client.delete("/api/v1/auth/sessions/" + second_id, headers=headers)
    ).status_code == 204
    assert (await client.get("/api/v1/users/me", headers=second_headers)).status_code == 401
    assert (await client.get("/api/v1/users/me", headers=headers)).status_code == 200


async def test_block_then_unblock_does_not_resurrect_old_sessions(client):
    tokens, headers = await sign_in(client, 64001)
    _, admin = await sign_in(client, 64002, role="ADMIN")
    user_id = decode_token(tokens["access_token"])["sub"]
    assert (
        await client.patch("/api/v1/users/" + user_id, headers=admin, json={"is_active": False})
    ).status_code == 200
    assert (
        await client.patch("/api/v1/users/" + user_id, headers=admin, json={"is_active": True})
    ).status_code == 200
    assert (await client.get("/api/v1/users/me", headers=headers)).status_code == 401


async def test_password_change_revokes_all_existing_sessions(client):
    first, headers = await sign_in(client, 65001)
    second, second_headers = await sign_in(client, 65001)
    changed = await client.patch(
        "/api/v1/users/me", headers=headers, json={"password": "longer-new-password"}
    )
    assert changed.status_code == 200
    for credential in (headers, second_headers):
        assert (await client.get("/api/v1/users/me", headers=credential)).status_code == 401


async def test_signed_access_without_persisted_session_is_rejected(client):
    tokens, headers = await sign_in(client, 66001)
    user_id = decode_token(tokens["access_token"])["sub"]
    unbound = create_access_token(user_id, "CLIENT")
    assert (
        await client.get("/api/v1/users/me", headers={"Authorization": "Bearer " + unbound})
    ).status_code == 401


async def test_concurrent_attempt_reservations_enforce_exact_budget(client):
    results = await asyncio.gather(
        *(reserve_attempt("test_budget", "one-account", limit=3, seconds=60) for _ in range(10)),
        return_exceptions=True,
    )
    assert sum(item is None for item in results) == 3
    assert sum(isinstance(item, HTTPException) and item.status_code == 429 for item in results) == 7
    async with async_session_maker() as db:
        bucket = await db.scalar(
            select(AuthAttemptBucket).where(AuthAttemptBucket.scope == "test_budget")
        )
        assert bucket.attempts == 10


async def test_admin_bad_password_budget_survives_error_responses(client):
    await sign_in(
        client, 67001, role="ADMIN", email="admin-limit@example.test", password="correct-password"
    )
    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/admin/login",
            json={"email": "ADMIN-LIMIT@example.test", "password": "wrong"},
        )
        assert response.status_code == 401
    response = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin-limit@example.test", "password": "correct-password"},
    )
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0


async def challenge(client, headers, purpose="account_verification"):
    response = await client.post(
        "/api/v1/verification/send-code-test", headers=headers, json={"purpose": purpose}
    )
    assert response.status_code == 200, response.text
    return response.json()["code"]


async def verify(client, headers, code, purpose="account_verification"):
    return await client.post(
        "/api/v1/verification/verify-code", headers=headers, json={"code": code, "purpose": purpose}
    )


async def test_wrong_codes_consume_latest_challenge_budget(client):
    _, headers = await sign_in(client, 68001)
    code = await challenge(client, headers)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(3):
        assert (await verify(client, headers, wrong)).status_code == 401
    assert (await verify(client, headers, code)).status_code == 429
    async with async_session_maker() as db:
        record = await db.scalar(select(VerificationCode))
        assert record.attempts == 3 and not record.is_used and not hasattr(record, "code")


async def test_parallel_correct_code_is_consumed_once(client):
    _, headers = await sign_in(client, 69001)
    code = await challenge(client, headers)
    responses = await asyncio.gather(verify(client, headers, code), verify(client, headers, code))
    assert sorted(response.status_code for response in responses) == [200, 401]
    async with async_session_maker() as db:
        assert (await db.scalar(select(VerificationCode))).attempts == 1


async def test_resend_invalidates_old_code_and_cooldown_is_enforced(client):
    _, headers = await sign_in(client, 70001)
    await challenge(client, headers)
    limited = await client.post("/api/v1/verification/send-code-test", headers=headers, json={})
    assert limited.status_code == 429 and "Retry-After" in limited.headers
    async with async_session_maker() as db:
        await db.execute(
            update(AuthAttemptBucket)
            .where(AuthAttemptBucket.scope == "verification_cooldown")
            .values(window_started_at=datetime.now(timezone.utc) - timedelta(seconds=61))
        )
        await db.commit()
    second = await challenge(client, headers)
    async with async_session_maker() as db:
        records = (
            await db.scalars(select(VerificationCode).order_by(VerificationCode.created_at))
        ).all()
        assert records[0].is_used and not records[1].is_used
    # Code generation can randomly repeat; the digest still binds it to the new challenge.
    assert (await verify(client, headers, second)).status_code == 200


async def test_real_code_delivery_is_encrypted_and_purpose_bound(client, monkeypatch):
    from app.services.verification_challenges import delivery_cipher

    _, headers = await sign_in(client, 2**40)
    monkeypatch.setattr(settings, "TELEGRAM_ENABLED", True)
    response = await client.post("/api/v1/verification/send-code", headers=headers, json={})
    assert response.status_code == 200
    async with async_session_maker() as db:
        record = await db.scalar(select(VerificationCode))
        message = await db.scalar(select(OutboxMessage))
        assert record.telegram_id == 2**40
        assert "text" not in message.payload and "encrypted_text" in message.payload
        text = delivery_cipher().decrypt(message.payload["encrypted_text"].encode()).decode()
        code = text.split(": ", 1)[1].split("\n")[0]
    assert (await verify(client, headers, code, purpose="2fa")).status_code == 401
    assert (await verify(client, headers, code)).status_code == 200


async def test_websocket_ticket_is_single_use_and_session_bound(client):
    from app.services.sessions import consume_websocket_ticket, validate_socket_session

    tokens, headers = await sign_in(client, 72001)
    issued = await client.post("/api/v1/auth/ws-ticket", headers=headers)
    assert issued.status_code == 200
    ticket = issued.json()["ticket"]
    assert tokens["access_token"] not in ticket
    user_id, session_id, deadline = await consume_websocket_ticket(ticket)
    assert str(user_id) == decode_token(tokens["access_token"])["sub"]
    with pytest.raises(ValueError):
        await consume_websocket_ticket(ticket)
    assert (
        await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    ).status_code == 204
    with pytest.raises(ValueError):
        await validate_socket_session(session_id, deadline)


async def test_parallel_ticket_requests_release_auth_connections_before_budget_reservation(client):
    _, headers = await sign_in(client, 73001)
    responses = await asyncio.wait_for(
        asyncio.gather(
            *(client.post("/api/v1/auth/ws-ticket", headers=headers) for _ in range(20))
        ),
        timeout=15,
    )
    assert all(response.status_code == 200 for response in responses)
    assert len({response.json()["ticket"] for response in responses}) == 20
