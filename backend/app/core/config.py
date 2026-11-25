from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore"
    )
    app_name: str = "Speech to Text API"
    app_env: str = "development"
    debug: bool = False
    # Intentional service bind; TLS/firewall at deployment edge.
    host: str = "0.0.0.0"  # nosec B104
    port: int = 8000
    database_url: str = "postgresql+asyncpg://postgres:your_password@localhost:5432/speech_to_text"
    database_ssl: bool = False
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_language: str = "auto"
    audio_sample_rate: int = 16000
    audio_chunk_duration: float = 3
    audio_overlap_duration: float = 1
    max_session_duration: int = 300
    max_audio_size_mb: int = 10
    max_worker_sessions: int = 4
    transcription_service_url: str = "http://localhost:8001"
    transcription_websocket_url: str = "ws://localhost:8001/ws/transcribe"
    transcription_service_api_key: str = "replace_with_secure_key"
    test_access_token: str = ""
    test_user_name: str = "Shared test account"
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"

    @model_validator(mode="after")
    def validate_config(self):
        if self.audio_sample_rate != 16000:
            raise ValueError("Whisper requires AUDIO_SAMPLE_RATE=16000")
        if not 0 <= self.audio_overlap_duration < self.audio_chunk_duration <= 30:
            raise ValueError("Require 0 <= overlap < chunk <= 30 seconds")
        if min(self.max_session_duration, self.max_audio_size_mb, self.max_worker_sessions) <= 0:
            raise ValueError("Resource limits must be positive")
        if self.app_env == "production":
            if (
                len(self.transcription_service_api_key) < 32
                or "replace" in self.transcription_service_api_key
            ):
                raise ValueError("Set a random worker secret of at least 32 characters")
            if not self.database_ssl or not self.database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("Production requires PostgreSQL with DATABASE_SSL=true")
            if not self.cors_origins or any(
                not x.startswith("https://") for x in self.cors_origins
            ):
                raise ValueError("Production requires explicit HTTPS origins")
            if not self.transcription_service_url.startswith(
                "https://"
            ) or not self.transcription_websocket_url.startswith("wss://"):
                raise ValueError("Production worker requires HTTPS and WSS")
        return self


@lru_cache
def get_settings():
    return Settings()
