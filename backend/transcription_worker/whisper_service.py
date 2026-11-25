import asyncio
import os

# Fixed FFmpeg argv below; shell disabled and decode timeout enforced.
import subprocess  # nosec B404
import tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from fastapi import HTTPException

from app.core.config import get_settings


class WhisperService:
    """One inference at a time per process; no unbounded executor work queue."""

    def __init__(self):
        self.model = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")
        self.lock = asyncio.Lock()

    def load(self):
        import whisper

        settings = get_settings()
        self.model = whisper.load_model(settings.whisper_model, device=settings.whisper_device)

    def transcribe(self, samples):
        settings = get_settings()
        if not np.any(np.abs(samples) > 0.006):
            return {"text": "", "language": "auto", "segments": []}
        return self.model.transcribe(
            samples,
            task="transcribe",
            language=None if settings.whisper_language == "auto" else settings.whisper_language,
            fp16=settings.whisper_device != "cpu",
            condition_on_previous_text=False,
            verbose=False,
            temperature=0,
        )

    async def infer(self, samples):
        async with self.lock:
            return await asyncio.get_running_loop().run_in_executor(
                self.executor, self.transcribe, samples
            )

    async def file(self, content):
        samples = await asyncio.to_thread(decode_audio, content)
        return await self.infer(samples), len(samples) / 16000

    async def close(self):
        await asyncio.to_thread(self.executor.shutdown, wait=True, cancel_futures=True)


def decode_audio(content):
    settings = get_settings()
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as file:
            path = file.name
            file.write(content)
        # Decode at most limit+1 seconds, preventing compressed-audio expansion bombs.
        command = [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
            path,
            "-t",
            str(settings.max_session_duration + 1),
            "-f",
            "f32le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "pipe:1",
        ]
        result = subprocess.run(command, capture_output=True, timeout=45, check=True)  # nosec B603
        samples = np.frombuffer(result.stdout, dtype="<f4").copy()
        if not samples.size or not np.isfinite(samples).all():
            raise HTTPException(422, "No valid audio samples found")
        if samples.size > settings.max_session_duration * 16000:
            raise HTTPException(413, "Audio exceeds the maximum session duration")
        return samples
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(422, "Audio could not be decoded") from exc
    finally:
        if path:
            os.unlink(path)
