"""Record local PCM audio, stream it to the worker and display transcript events.

Install optional sounddevice first. Set STT_ACCESS_TOKEN in the environment.
Run from backend: python -m scripts.test_microphone --seconds 10
"""

import argparse
import asyncio
import json
import os

import httpx
import websockets

from app.core.config import get_settings


async def run(seconds):
    import sounddevice as sd

    settings = get_settings()
    token = os.environ.get("STT_ACCESS_TOKEN")
    if not token:
        raise SystemExit("Set STT_ACCESS_TOKEN to your provisioned user token")
    print(f"Recording {seconds} seconds from the default microphone…")
    samples = await asyncio.to_thread(
        sd.rec, seconds * 16000, samplerate=16000, channels=1, dtype="int16", blocking=True
    )
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/auth/ticket", headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        ticket = response.json()["data"]
    async with websockets.connect(
        ticket["websocket_url"], origin=settings.cors_origins[0]
    ) as socket:
        await socket.send(
            json.dumps({"type": "auth", "ticket": ticket["ticket"], "title": "Microphone test"})
        )
        ready = json.loads(await socket.recv())
        if ready["type"] != "ready":
            raise RuntimeError(ready)
        for start in range(0, len(samples), 8000):
            await socket.send(samples[start : start + 8000].astype("<i2").tobytes())
        await socket.send(json.dumps({"type": "stop"}))
        async for message in socket:
            event = json.loads(message)
            print(event)
            if event["type"] in ("final", "error"):
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, choices=range(1, 301), default=10)
    asyncio.run(run(parser.parse_args().seconds))
