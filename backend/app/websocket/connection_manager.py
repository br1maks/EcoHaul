from typing import Dict, Set, Optional
import asyncio
from uuid import UUID
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket):
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket подключён для пользователя {user_id}. Всего соединений: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: UUID, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                logger.info(f"Все соединения пользователя {user_id} закрыты")
            else:
                logger.info(f"WebSocket отключён для {user_id}. Осталось соединений: {len(self.active_connections[user_id])}")
    
    async def send_personal_message(self, user_id: UUID, message: dict) -> int:
        # Offline users recover persistent state/inbox through HTTP after reconnect.
        connections = tuple(self.active_connections.get(user_id, ()))

        async def send(websocket: WebSocket) -> bool:
            try:
                async with asyncio.timeout(3):
                    await websocket.send_json(message)
                return True
            except Exception:
                self.disconnect(user_id, websocket)
                try:
                    async with asyncio.timeout(1):
                        await websocket.close(code=1011)
                except Exception:
                    pass
                return False

        results = await asyncio.gather(*(send(connection) for connection in connections))
        if not all(results):
            # Preserve the intent for retry. Other tabs may have received this event;
            # stable event ids let them suppress a duplicate publication.
            raise ConnectionError("WebSocket transport failed")
        return len(results)

    async def broadcast(self, message: dict, exclude_user: Optional[UUID] = None):
        for user_id in list(self.active_connections.keys()):
            if exclude_user and user_id == exclude_user:
                continue
            await self.send_personal_message(user_id, message)

    async def send_to_users(self, user_ids: list[UUID], message: dict):
        sent_count = 0
        for user_id in user_ids:
            if self.is_user_online(user_id):
                await self.send_personal_message(user_id, message)
                sent_count += 1

        logger.info(f"Сообщение отправлено {sent_count} из {len(user_ids)} пользователей")
        return sent_count

    def get_online_users_count(self) -> int:
        return len(self.active_connections)

    def is_user_online(self, user_id: UUID) -> bool:
        return user_id in self.active_connections

manager = ConnectionManager()
