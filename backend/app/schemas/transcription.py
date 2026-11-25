from datetime import datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    data: T


class CreateTranscription(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(default="", max_length=100000)
    language: str = Field(default="auto", pattern=r"^[a-z]{2,3}(-[a-z]{2,3})?$|^auto$")
    duration: float = Field(default=0, ge=0, le=86400, allow_inf_nan=False)
    status: Literal["completed", "failed"] = "completed"


class UpdateTranscription(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    text: str | None = Field(default=None, max_length=100000)

    @model_validator(mode="after")
    def no_nulls(self):
        if not self.model_fields_set or any(
            getattr(self, k) is None for k in self.model_fields_set
        ):
            raise ValueError("Supply a non-null title or text")
        return self


class TranscriptionOut(CreateTranscription):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    items: list[TranscriptionOut]
    total: int
    page: int
    page_size: int
