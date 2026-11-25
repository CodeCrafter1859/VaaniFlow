from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import issue_ticket
from app.models.transcription import User
from transcription_worker import main, websocket_handler


async def test_worker_upload_success_and_ticket_replay(database, monkeypatch):
    monkeypatch.setattr(main, "Session", database)
    main.app.state.active = 0
    main.app.state.whisper = SimpleNamespace(
        file=AsyncMock(return_value=({"text": "hello नमस्ते", "language": "hi"}, 2.5))
    )
    async with database() as db:
        user = await db.scalar(select(User))
        ticket = await issue_ticket(db, user.id, "upload")
    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://worker"
    ) as client:
        response = await client.post(
            "/audio",
            headers={"X-Upload-Ticket": ticket},
            files={"file": ("test.wav", b"RIFFtest", "audio/wav")},
        )
        assert response.status_code == 201
        assert response.json()["data"]["text"] == "hello नमस्ते"
        response = await client.post(
            "/audio",
            headers={"X-Upload-Ticket": ticket},
            files={"file": ("test.wav", b"RIFFtest", "audio/wav")},
        )
        assert response.status_code == 401
        response = await client.post(
            "/internal/audio",
            data={"owner_id": str(user.id)},
            files={"file": ("test.wav", b"RIFFtest", "audio/wav")},
        )
        assert response.status_code == 401
    assert main.app.state.active == 0


async def test_actual_websocket_adapter(database, monkeypatch):
    monkeypatch.setattr(websocket_handler, "Session", database)
    main.app.state.active = 0
    main.app.state.whisper = SimpleNamespace(
        infer=AsyncMock(return_value={"text": "hello", "language": "en"})
    )
    async with database() as db:
        user = await db.scalar(select(User))
        ticket = await issue_ticket(db, user.id, "websocket")
    # No lifespan context: avoid loading real model; exercise the actual ASGI websocket route.
    client = TestClient(main.app)
    with client.websocket_connect(
        "/ws/transcribe", headers={"Origin": "http://localhost:5173"}
    ) as ws:
        ws.send_json({"type": "auth", "ticket": ticket})
        assert ws.receive_json()["type"] == "ready"
        ws.send_bytes(b"\x00\x01" * 1600)
        ws.send_json({"type": "stop"})
        event = ws.receive_json()
        assert event["type"] == "final"
        assert event["record"]["status"] == "completed"
