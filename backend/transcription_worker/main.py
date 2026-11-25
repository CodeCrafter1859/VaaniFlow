import asyncio
import secrets
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, WebSocket

from app.core.auth import consume_ticket
from app.core.config import get_settings
from app.db.database import Session, engine
from app.repositories.transcriptions import create
from app.schemas.transcription import Envelope, TranscriptionOut
from app.services.audio import read_upload
from app.utils.http import configure_app
from transcription_worker.websocket_handler import handle_socket
from transcription_worker.whisper_service import WhisperService


@asynccontextmanager
async def lifespan(app):
    app.state.whisper = WhisperService()
    app.state.active = 0
    await asyncio.to_thread(app.state.whisper.load)
    yield
    await app.state.whisper.close()
    await engine.dispose()


app = FastAPI(title="Whisper worker", lifespan=lifespan)
configure_app(app)


@app.get("/health")
async def health():
    return {"data": {"status": "ready" if getattr(app.state, "whisper", None) else "loading"}}


@app.websocket("/ws/transcribe")
async def websocket(ws: WebSocket):
    await handle_socket(ws)


async def upload_owner(x_upload_ticket: str = Header(...)):
    async with Session() as db:
        return await consume_ticket(db, x_upload_ticket, "upload")


async def process(file, title, owner):
    if app.state.active >= get_settings().max_worker_sessions:
        await file.close()
        raise HTTPException(503, "Worker is busy; try again shortly")
    app.state.active += 1
    try:
        content = await read_upload(file)
        result, duration = await app.state.whisper.file(content)
        async with Session() as db:
            record = await create(
                db,
                owner,
                dict(
                    title=title,
                    text=result["text"].strip(),
                    language=result.get("language", "auto"),
                    duration=duration,
                    status="completed",
                ),
            )
            return {"data": TranscriptionOut.model_validate(record)}
    finally:
        app.state.active -= 1
        await file.close()


@app.post("/audio", status_code=201, response_model=Envelope[TranscriptionOut])
async def audio(
    file: UploadFile = File(...),
    title: str = Form("Audio upload", min_length=1, max_length=200),
    owner: UUID = Depends(upload_owner),
):
    return await process(file, title, owner)


async def service_auth(authorization: str = Header("")):
    expected = "Bearer " + get_settings().transcription_service_api_key
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(401, "Invalid service credential")


@app.post(
    "/internal/audio",
    status_code=201,
    dependencies=[Depends(service_auth)],
    response_model=Envelope[TranscriptionOut],
)
async def internal_audio(
    owner_id: UUID = Form(...),
    file: UploadFile = File(...),
    title: str = Form("Audio upload", min_length=1, max_length=200),
):
    return await process(file, title, owner_id)
