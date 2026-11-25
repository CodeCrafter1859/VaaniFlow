from unittest.mock import patch

import pytest
from fastapi import HTTPException

from transcription_worker.whisper_service import decode_audio


async def test_body_limit_before_parsing(client):
    result = await client.post(
        "/api/v1/transcriptions",
        content=b"x" * 512001,
        headers={"Content-Type": "application/json"},
    )
    assert result.status_code == 413


def test_decode_rejects_empty_and_expansion():
    from types import SimpleNamespace

    with patch(
        "transcription_worker.whisper_service.subprocess.run",
        return_value=SimpleNamespace(stdout=b""),
    ):
        with pytest.raises(HTTPException) as error:
            decode_audio(b"RIFFfake")
        assert error.value.status_code == 422
