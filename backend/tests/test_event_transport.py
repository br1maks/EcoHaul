import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.websocket.connection_manager import ConnectionManager


class Socket:
    def __init__(self, fail=False):
        self.messages = []
        self.fail = fail
        self.closed = None

    async def close(self, code):
        self.closed = code

    async def send_json(self, message):
        if self.fail:
            raise ConnectionError("closed")
        self.messages.append(message)


@pytest.mark.asyncio
async def test_partial_socket_failure_is_reported_without_losing_other_tabs():
    manager = ConnectionManager()
    user_id = uuid4()
    good, broken = Socket(), Socket(fail=True)
    manager.active_connections[user_id] = {good, broken}
    with pytest.raises(ConnectionError):
        await manager.send_personal_message(user_id, {"event_id": "stable-id"})
    assert good.messages == [{"event_id": "stable-id"}]
    assert manager.active_connections[user_id] == {good}
    assert broken.closed == 1011
    assert await manager.send_personal_message(uuid4(), {}) == 0


@pytest.mark.asyncio
async def test_dispatch_loop_recovers_after_database_failure(monkeypatch):
    from app.services import outbox_dispatcher as dispatcher

    attempts = []

    async def dispatch(channel):
        attempts.append(channel)
        if len(attempts) == 1:
            raise ConnectionError("database unavailable")
        raise asyncio.CancelledError()

    async def no_wait(seconds):
        return None

    monkeypatch.setattr(dispatcher, "dispatch_one", dispatch)
    monkeypatch.setattr(dispatcher.asyncio, "sleep", no_wait)
    with pytest.raises(asyncio.CancelledError):
        await dispatcher.dispatch_forever("websocket")
    assert attempts == ["websocket", "websocket"]


@pytest.mark.asyncio
async def test_lifespan_stops_dispatchers_before_closing_resources(monkeypatch):
    from app import main

    started, stopped = [], []
    ready, forever = asyncio.Event(), asyncio.Event()

    async def dispatch(channel):
        started.append(channel)
        if len(started) == 3:
            ready.set()
        try:
            await forever.wait()
        finally:
            stopped.append(channel)

    async def init():
        pass

    async def close():
        assert len(stopped) == 3

    monkeypatch.setattr(main, "dispatch_forever", dispatch)
    monkeypatch.setattr(main, "init_redis", init)
    monkeypatch.setattr(main, "close_redis", close)
    monkeypatch.setattr(main, "engine", SimpleNamespace(dispose=close))
    monkeypatch.setattr(main, "setup_logging", lambda **kwargs: None)
    async with main.lifespan(main.app):
        await asyncio.wait_for(ready.wait(), timeout=2)
    assert set(stopped) == {"websocket", "telegram", "cache"}
