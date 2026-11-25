import asyncio
import json
import logging
import time

import numpy as np
from fastapi import HTTPException, WebSocketDisconnect

from app.core.auth import consume_ticket
from app.core.config import get_settings
from app.db.database import Session
from app.repositories.transcriptions import create
from app.schemas.transcription import TranscriptionOut
from app.utils.text import merge_overlap


async def handle_socket(ws):
    settings = get_settings()
    if ws.headers.get("origin") not in settings.cors_origins:
        await ws.close(code=1008)
        return
    await ws.accept()
    owner = None
    text = ""
    language = "auto"
    count = 0
    saved = False
    acquired = False
    title = "Live recording"
    try:
        auth = await asyncio.wait_for(ws.receive_json(), timeout=10)
        if not isinstance(auth, dict) or auth.get("type") != "auth":
            raise HTTPException(401, "Authenticate before sending audio")
        title = str(auth.get("title", title)).strip()[:200] or title
        async with Session() as db:
            owner = await consume_ticket(db, auth.get("ticket"), "websocket")
        if ws.app.state.active >= settings.max_worker_sessions:
            raise HTTPException(503, "Worker is busy; try again shortly")
        ws.app.state.active += 1
        acquired = True
        await ws.send_json(
            {"type": "ready", "sample_rate": 16000, "max_duration": settings.max_session_duration}
        )
        buffer = np.empty(0, dtype=np.float32)
        window = int(settings.audio_chunk_duration * 16000)
        overlap = int(settings.audio_overlap_duration * 16000)
        paused = False
        fresh = 0
        deadline = time.monotonic() + settings.max_session_duration * 2 + 60
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise HTTPException(408, "Session time limit reached")
            message = await asyncio.wait_for(ws.receive(), timeout=min(60, remaining))
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect()
            if message.get("bytes") is not None:
                data = message["bytes"]
                if paused:
                    continue
                if not data or len(data) % 2 or len(data) > 32000:
                    raise HTTPException(422, "Send PCM16 mono frames of at most one second")
                samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768
                count += len(samples)
                fresh += len(samples)
                if count > settings.max_session_duration * 16000:
                    raise HTTPException(413, "Recording duration limit exceeded")
                buffer = np.concatenate((buffer, samples))
                if len(buffer) >= window:
                    result = await ws.app.state.whisper.infer(buffer)
                    text = merge_overlap(text, result["text"].strip())
                    language = (
                        result.get("language", language) if result["text"].strip() else language
                    )
                    await ws.send_json(
                        {
                            "type": "partial",
                            "text": text,
                            "language": language,
                            "duration": count / 16000,
                        }
                    )
                    buffer = buffer[-overlap:] if overlap else np.empty(0, dtype=np.float32)
                    fresh = 0
                continue
            raw = message.get("text", "")
            if len(raw) > 1024:
                raise HTTPException(422, "Control frame too large")
            control = json.loads(raw)
            kind = control.get("type") if isinstance(control, dict) else None
            if kind in ("pause", "resume"):
                paused = kind == "pause"
            elif kind == "stop":
                if fresh:
                    result = await ws.app.state.whisper.infer(buffer)
                    text = merge_overlap(text, result["text"].strip())
                    if result["text"].strip():
                        language = result.get("language", language)
                async with Session() as db:
                    record = await create(
                        db,
                        owner,
                        dict(
                            title=title,
                            text=text,
                            language=language,
                            duration=count / 16000,
                            status="completed",
                        ),
                    )
                    saved = True
                    await ws.send_json(
                        {
                            "type": "final",
                            "text": text,
                            "language": language,
                            "record": TranscriptionOut.model_validate(record).model_dump(
                                mode="json"
                            ),
                        }
                    )
                await ws.close(code=1000)
                return
            else:
                raise HTTPException(422, "Unknown control message")
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        message = (
            str(exc.detail) if isinstance(exc, HTTPException) else "Recording failed or timed out"
        )
        logging.getLogger(__name__).warning("Socket ended: %s", type(exc).__name__)
        try:
            await ws.send_json({"type": "error", "message": message, "text": text})
            await ws.close(code=1008)
        except (RuntimeError, WebSocketDisconnect):
            pass
    finally:
        if acquired:
            ws.app.state.active -= 1
        if owner and count and not saved:
            try:
                async with Session() as db:
                    await create(
                        db,
                        owner,
                        dict(
                            title=title,
                            text=text,
                            language=language,
                            duration=count / 16000,
                            status="failed",
                        ),
                    )
            except Exception:
                logging.getLogger(__name__).error("Failed to persist interrupted session")
