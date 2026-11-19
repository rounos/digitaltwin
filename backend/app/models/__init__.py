from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    EMAIL = "email"
    CHAT = "chat"
    NOTE = "note"
    DOCUMENT = "document"
    DECISION = "decision"


class Document(BaseModel):
    id: str
    source_type: SourceType
    title: str = ""
    text: str
    date: dt.datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)