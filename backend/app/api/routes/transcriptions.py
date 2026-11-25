from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user, issue_ticket
from app.core.config import get_settings
from app.db.database import get_db
from app.models.transcription import User
from app.repositories import transcriptions as repo
from app.schemas.transcription import (
    CreateTranscription,
    Envelope,
    Page,
    TranscriptionOut,
    UpdateTranscription,
)
from app.services.audio import proxy_audio, read_upload

router = APIRouter(prefix="/api/v1")


@router.get("/auth/me")
async def me(user: User = Depends(current_user)):
    return {"data": {"id": user.id, "name": user.name}}


@router.post("/auth/ticket")
async def ticket(
    purpose: Literal["websocket", "upload"] = "websocket",
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    return {
        "data": {
            "ticket": await issue_ticket(db, user.id, purpose),
            "expires_in": 60,
            "websocket_url": settings.transcription_websocket_url,
            "upload_url": settings.transcription_service_url + "/audio",
        }
    }


@router.post("/transcriptions", status_code=201, response_model=Envelope[TranscriptionOut])
async def create(
    body: CreateTranscription,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": await repo.create(db, user.id, body.model_dump())}


@router.get("/transcriptions", response_model=Envelope[Page])
async def listing(
    search: str = Query("", max_length=200),
    language: str | None = Query(None, max_length=16),
    status: Literal["completed", "failed"] | None = None,
    sort: Literal["created_at", "title", "duration"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1, le=100000),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return {
        "data": await repo.listing(
            db, user.id, search, language, status, sort, order, page, page_size
        )
    }


@router.post("/transcriptions/audio", status_code=201, response_model=Envelope[TranscriptionOut])
async def audio(
    file: UploadFile = File(...),
    title: str = Form("Audio upload", min_length=1, max_length=200),
    user: User = Depends(current_user),
):
    try:
        data = await read_upload(file)
        return await proxy_audio(data, file.content_type, user.id, title)
    finally:
        await file.close()


@router.get("/transcriptions/{record_id}", response_model=Envelope[TranscriptionOut])
async def get_record(
    record_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    return {"data": await repo.get_owned(db, user.id, record_id)}


@router.patch("/transcriptions/{record_id}", response_model=Envelope[TranscriptionOut])
async def update(
    record_id: UUID,
    body: UpdateTranscription,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await repo.get_owned(db, user.id, record_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    await db.commit()
    await db.refresh(record)
    return {"data": record}


@router.delete("/transcriptions/{record_id}")
async def delete_record(
    record_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    record = await repo.get_owned(db, user.id, record_id)
    await db.delete(record)
    await db.commit()
    return {"data": {"deleted": True}}


@router.get("/dashboard/stats")
async def stats(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return {"data": await repo.stats(db, user.id)}
