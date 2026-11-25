import asyncio
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select, update

from app.core.auth import consume_ticket, issue_ticket
from app.core.config import Settings
from app.models.transcription import Ticket, User, utcnow


async def test_expired_ticket(database):
    async with database() as db:
        user = await db.scalar(select(User))
        ticket = await issue_ticket(db, user.id, "upload")
        await db.execute(update(Ticket).values(expires_at=utcnow() - timedelta(seconds=1)))
        await db.commit()
        with pytest.raises(HTTPException):
            await consume_ticket(db, ticket, "upload")


async def test_ticket_atomic_under_race(database):
    async with database() as db:
        user = await db.scalar(select(User))
        ticket = await issue_ticket(db, user.id, "websocket")

    async def claim():
        async with database() as db:
            try:
                await consume_ticket(db, ticket, "websocket")
                return True
            except HTTPException:
                return False

    assert sorted(await asyncio.gather(claim(), claim())) == [False, True]


def test_production_rejects_insecure_settings():
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env="production")


async def test_cors_and_headers(client):
    response = await client.get("/health", headers={"Origin": "https://evil.test"})
    assert "access-control-allow-origin" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    response = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
