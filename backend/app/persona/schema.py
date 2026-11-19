"""The inspectable persona model. Every learned item carries evidence_ids pointing at source documents."""
from __future__ import annotations

import datetime as dt
import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field

Domain = Literal["ai_security", "cybersecurity", "medical", "crisis", "time_management", "general"]
Level = Literal["low", "medium", "high", "critical", "varies"]


def _uid(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:8]


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

    @computed_field
    @property
    def uid(self) -> str:
        return _uid(self.domain, self.condition.lower())


class ExtractionResult(BaseModel):
    knowledge: list[Fact]
    preferences: list[Preference]
    risk_attitudes: list[RiskAttitude]
    decision_rules: list[DecisionRule]
    tone_notes: list[str]


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
    role: str = "AI Red Teamer & Adversarial Testing Lead"
    version: int = 0
    created_at: dt.datetime | None = None
    source_stats: dict[str, int] = Field(default_factory=dict)
    style: StyleProfile = Field(default_factory=StyleProfile)
    knowledge: list[Fact] = Field(default_factory=list)
    preferences: list[Preference] = Field(default_factory=list)
    risk_attitudes: list[RiskAttitude] = Field(default_factory=list)
    decision_rules: list[DecisionRule] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)

    def to_ui_dict(self) -> dict[str, Any]:
        """Μετατρέπει το PersonaProfile στη μορφή JSON που περιμένει το React UI."""
        tone = ", ".join(self.style.tone_notes) if self.style.tone_notes else "Αναλυτικός, ευθύς, risk-focused"
        return {
            "persona_id": f"v{self.version:03d}",
            "name": self.subject,
            "role": self.role,
            "writing_style": {
                "tone": tone,
                "vocabulary_notes": "Ακριβής τεχνική ορολογία βασισμένη στο ψηφιακό αποτύπωμα.",
            },
            "decision_heuristics": [
                f"IF {r.condition} THEN {r.action} (risk: {r.risk_level})" for r in self.decision_rules
            ],
            "knowledge_facts": [k.statement for k in self.knowledge],
        }

    def apply_ui_update(self, payload: dict[str, Any]) -> None:
        """Ενημερώνει το PersonaProfile από edits του χρήστη στο Tab 2 του UI."""
        if "name" in payload:
            self.subject = payload["name"]
        if "role" in payload:
            self.role = payload["role"]
        tone = payload.get("writing_style", {}).get("tone")
        if tone:
            self.style.tone_notes = [t.strip() for t in tone.split(",") if t.strip()]
        if "knowledge_facts" in payload:
            self.knowledge = [
                Fact(statement=f, evidence_ids=["manual_ui_edit"]) for f in payload["knowledge_facts"] if f.strip()
            ]
        if "decision_heuristics" in payload:
            updated_rules = []
            for h in payload["decision_heuristics"]:
                if not h.strip():
                    continue
                updated_rules.append(
                    DecisionRule(
                        domain="ai_security",
                        condition=h.strip(),
                        action="Enforce rule",
                        risk_level="high",
                        confidence=1.0,
                        evidence_ids=["manual_ui_edit"],
                    )
                )
            self.decision_rules = updated_rules