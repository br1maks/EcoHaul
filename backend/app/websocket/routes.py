import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.websocket.connection_manager import manager
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

logger = logging.getLogger(__name__)

router = APIRouter()

from app.services.sessions import consume_websocket_ticket, validate_socket_session


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: str = Query(
        ..., min_length=20, max_length=128, description="Одноразовый билет из /auth/ws-ticket"
    ),
):
    user_id = None
    try:
        origin = websocket.headers.get("origin")
        if origin is not None and origin not in settings.ALLOWED_ORIGINS:
            raise ValueError("Origin not allowed")
        user_id, session_id, deadline = await consume_websocket_ticket(ticket)

        await manager.connect(user_id, websocket)

        await websocket.send_json(
            {
                "type": "CONNECTED",
                "data": {"message": "WebSocket соединение установлено", "user_id": str(user_id)},
            }
        )

        while True:
            await validate_socket_session(session_id, deadline)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=min(
                        settings.WS_AUTH_CHECK_SECONDS,
                        max(0.01, (deadline - datetime.now(timezone.utc)).total_seconds()),
                    ),
                )
            except asyncio.TimeoutError:
                continue
            await validate_socket_session(session_id, deadline)

            message_type = data.get("type")

            if message_type == "PING":
                await websocket.send_json(
                    {"type": "PONG", "data": {"timestamp": data.get("data", {}).get("timestamp")}}
                )

            elif message_type == "MARK_READ":
                notification_id = data.get("notification_id")
                if notification_id:
                    from uuid import UUID

                    from app.core.database import async_session_maker
                    from app.models.notification import Notification
                    from sqlalchemy import update

                    try:
                        async with async_session_maker() as db:
                            stmt = (
                                update(Notification)
                                .where(
                                    Notification.id == UUID(notification_id),
                                    Notification.user_id == user_id,
                                )
                                .values(is_read=True, read_at=datetime.now(timezone.utc))
                            )
                            await db.execute(stmt)
                            await db.commit()

                            logger.info(
                                f"Уведомление {notification_id} отмечено как прочитанное для пользователя {user_id}"
                            )

                    except Exception as e:
                        logger.error(f"Ошибка обновления уведомления {notification_id}: {e}")
                else:
                    logger.warning(f"MARK_READ без notification_id от пользователя {user_id}")

            else:
                logger.warning(f"Неизвестный тип сообщения от {user_id}: {message_type}")

    except ValueError as e:
        logger.error(f"WebSocket auth error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

    finally:
        if user_id:
            manager.disconnect(user_id, websocket)
