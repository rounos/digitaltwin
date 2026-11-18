"""The inspectable persona model. Every learned item carries evidence_ids pointing at source documents."""
from __future__ import annotations

import datetime as dt
import hashlib
from typing import Literal

from pydantic import BaseModel, Field, computed_field

Domain = Literal["medical", "crisis", "time_management", "general"]
Level = Literal["low", "medium", "high", "critical", "varies"]


def _uid(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:8]


# ---- items the LLM extracts (kept free of defaults / dicts so they work as strict structured output) ----
class Fact(BaseModel):
    statement: str
    evidence_ids: list[str]


class Preference(BaseModel):
    topic: str
    statement: str
    evidence_ids: list[str]


class RiskAttitude(BaseModel):
    domain: Domain
    stance: str
    evidence_ids: list[str]


class DecisionRule(BaseModel):
    domain: Domain
    condition: str
    action: str
    risk_level: Level
    confidence: float
    evidence_ids: list[str]

    @computed_field  # stable id so the owner/UI can refer to one rule
    @property
    def uid(self) -> str:
        return _uid(self.domain, self.condition.lower())


class ExtractionResult(BaseModel):
    knowledge: list[Fact]
    preferences: list[Preference]
    risk_attitudes: list[RiskAttitude]
    decision_rules: list[DecisionRule]
    tone_notes: list[str]


# ---- deterministic style measurements (no LLM) ----
class PatternShare(BaseModel):
    pattern: str
    share: float


class StyleChannel(BaseModel):
    channel: str
    n_samples: int
    avg_words_per_message: float
    avg_words_per_sentence: float
    exclamations_per_100_words: float
    emoji_per_message: float
    question_rate: float
    bullet_rate: float
    greetings: list[PatternShare] = Field(default_factory=list)
    signoffs: list[PatternShare] = Field(default_factory=list)
    language_share: dict[str, float] = Field(default_factory=dict)
    top_words: list[str] = Field(default_factory=list)
    example_snippets: list[str] = Field(default_factory=list)


class StyleProfile(BaseModel):
    email: StyleChannel | None = None
    chat: StyleChannel | None = None
    tone_notes: list[str] = Field(default_factory=list)


class PersonaProfile(BaseModel):
    subject: str
    version: int = 0
    created_at: dt.datetime | None = None
    source_stats: dict[str, int] = Field(default_factory=dict)
    style: StyleProfile = Field(default_factory=StyleProfile)
    knowledge: list[Fact] = Field(default_factory=list)
    preferences: list[Preference] = Field(default_factory=list)
    risk_attitudes: list[RiskAttitude] = Field(default_factory=list)
    decision_rules: list[DecisionRule] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)  # what the twin should admit it does not know
