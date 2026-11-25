import httpx
from fastapi import HTTPException

from app.core.config import get_settings


async def read_upload(file):
    settings = get_settings()
    allowed = {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/x-m4a",
        "audio/webm",
        "video/webm",
        "audio/ogg",
        "audio/flac",
        "audio/x-flac",
    }
    if file.content_type not in allowed:
        raise HTTPException(415, "Use WAV, MP3, M4A, WebM, OGG or FLAC audio")
    data = await file.read(settings.max_audio_size_mb * 1024 * 1024 + 1)
    if not data:
        raise HTTPException(422, "Audio file is empty")
    if len(data) > settings.max_audio_size_mb * 1024 * 1024:
        raise HTTPException(413, "Audio exceeds the upload limit")
    valid = (
        data.startswith((b"RIFF", b"ID3", b"OggS", b"fLaC", b"\x1aE\xdf\xa3"))
        or data[4:8] == b"ftyp"
        or (len(data) >= 2 and data[0] == 255 and data[1] & 224 == 224)
    )
    if not valid:
        raise HTTPException(422, "Unrecognized audio content")
    return data


async def proxy_audio(data, content_type, owner_id, title):
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                settings.transcription_service_url + "/internal/audio",
                headers={"Authorization": f"Bearer {settings.transcription_service_api_key}"},
                files={"file": ("audio", data, content_type)},
                data={"owner_id": str(owner_id), "title": title},
            )
        if response.is_error:
            raise HTTPException(
                response.status_code if response.status_code < 500 else 502,
                "Audio processing failed; verify the file and worker availability",
            )
        return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Transcription worker is unavailable") from exc
