from unittest.mock import AsyncMock

import numpy as np
import pytest
from fastapi import WebSocketDisconnect
from sqlalchemy import select

from app.core.auth import issue_ticket
from app.models.transcription import Transcription, User
from transcription_worker import websocket_handler as handler


class Socket:
    def __init__(self, frames, ticket, origin="http://localhost:5173"):
        from types import SimpleNamespace

        self.headers = {"origin": origin}
        self.frames = iter(frames)
        self.ticket = ticket
        self.sent = []
        self.app = SimpleNamespace(
            state=SimpleNamespace(
                active=0,
                whisper=SimpleNamespace(
                    infer=AsyncMock(return_value={"text": "नमस्ते hello", "language": "hi"})
                ),
            )
        )
        self.closed = None

    async def accept(self):
        pass

    async def receive_json(self):
        return {"type": "auth", "ticket": self.ticket}

    async def receive(self):
        try:
            return next(self.frames)
        except StopIteration:
            raise WebSocketDisconnect()

    async def send_json(self, value):
        self.sent.append(value)

    async def close(self, code):
        self.closed = code


async def make_ticket(database):
    async with database() as db:
        user = await db.scalar(select(User).where(User.name == "Alice"))
        return await issue_ticket(db, user.id, "websocket")


async def test_stream_flush_dedupe_and_persist(database, monkeypatch):
    monkeypatch.setattr(handler, "Session", database)
    frame = {"type": "websocket.receive", "bytes": (np.ones(16000, dtype="<i2") * 1000).tobytes()}
    socket = Socket(
        [frame] * 4 + [{"type": "websocket.receive", "text": '{"type":"stop"}'}],
        await make_ticket(database),
    )
    await handler.handle_socket(socket)
    assert [m["type"] for m in socket.sent] == ["ready", "partial", "final"]
    assert socket.sent[-1]["text"] == "नमस्ते hello"
    assert socket.sent[-1]["record"]["duration"] == 4
    async with database() as db:
        assert (await db.scalar(select(Transcription))).status == "completed"
    assert socket.app.state.active == 0


@pytest.mark.parametrize(
    "frames",
    [
        [{"type": "websocket.receive", "bytes": b"odd"}],
        [{"type": "websocket.receive", "text": "{bad"}],
    ],
)
async def test_bad_frames(database, monkeypatch, frames):
    monkeypatch.setattr(handler, "Session", database)
    socket = Socket(frames, await make_ticket(database))
    await handler.handle_socket(socket)
    assert socket.sent[-1]["type"] == "error"
    assert socket.app.state.active == 0


async def test_reject_origin(database):
    socket = Socket([], "invalid", origin="https://evil.test")
    await handler.handle_socket(socket)
    assert socket.closed == 1008 and not socket.sent


async def test_disconnect_records_failure(database, monkeypatch):
    monkeypatch.setattr(handler, "Session", database)
    socket = Socket(
        [{"type": "websocket.receive", "bytes": b"\x00\x01" * 100}], await make_ticket(database)
    )
    await handler.handle_socket(socket)
    async with database() as db:
        assert (await db.scalar(select(Transcription))).status == "failed"
