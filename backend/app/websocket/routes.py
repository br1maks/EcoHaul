import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import jwt, JWTError

from app.core.config import settings
from app.websocket.connection_manager import manager
from app.core.database import async_session_maker
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

async def get_current_user_from_token(token: str) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "access":
            raise ValueError("Invalid token type: expected access token")

        user_id_str = payload.get("sub")

        if user_id_str is None:
            raise ValueError("Invalid token payload: missing user_id")
        
        user_id = UUID(user_id_str)
        async with async_session_maker() as db:
            user = await db.get(User, user_id)
            if user is None or not user.is_active:
                raise ValueError("User is unavailable")
        return user_id

    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise ValueError("Could not validate credentials")
    except ValueError as e:
        logger.error(f"Invalid user_id in token: {e}")
        raise ValueError("Invalid user_id in token")
    

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token для аутентификации")
):
    user_id = None
    try:
        user_id = await get_current_user_from_token(token)

        await manager.connect(user_id, websocket)

        await websocket.send_json({
            "type": "CONNECTED",
            "data": {
                "message": "WebSocket соединение установлено",
                "user_id": str(user_id)
            }
        })

        while True:
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "PING":
                await websocket.send_json({
                    "type": "PONG",
                    "data": {"timestamp": data.get("data", {}).get("timestamp")}
                })

            elif message_type == "MARK_READ":
                notification_id = data.get("notification_id")
                if notification_id:
                    from sqlalchemy.ext.asyncio import AsyncSession
                    from app.core.database import async_session_maker
                    from app.models.notification import Notification
                    from sqlalchemy import select, update
                    from uuid import UUID

                    try:
                        async with async_session_maker() as db:
                            stmt = (
                                update(Notification)
                                .where(
                                    Notification.id == UUID(notification_id),
                                    Notification.user_id == user_id
                                )
                                .values(is_read=True, read_at=datetime.now(timezone.utc))
                            )
                            await db.execute(stmt)
                            await db.commit()

                            logger.info(f"Уведомление {notification_id} отмечено как прочитанное для пользователя {user_id}")

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
