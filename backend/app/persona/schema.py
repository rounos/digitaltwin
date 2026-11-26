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
    role: str = "Δεν έχει προσδιοριστεί"
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
        """Stable frontend contract, with structured evidence available for inspection."""
        tone = ", ".join(self.style.tone_notes) or "Δεν έχει εξαχθεί ακόμη ύφος γραφής"
        return {
            "persona_id": f"v{self.version:03d}",
            "persona_version": self.version,
            "name": self.subject,
            "role": self.role,
            "writing_style": {
                "tone": tone,
                "vocabulary_notes": "Συμπεράσματα μόνο από τα δεδομένα του χρήστη.",
            },
            "decision_heuristics": [self._rule_label(r) for r in self.decision_rules],
            "knowledge_facts": [k.statement for k in self.knowledge],
            "preferences": [p.statement for p in self.preferences],
            "source_stats": self.source_stats,
            "evidence": [{"type": "rule", "text": r.condition, "evidence_ids": r.evidence_ids}
                         for r in self.decision_rules] +
                        [{"type": "knowledge", "text": k.statement, "evidence_ids": k.evidence_ids}
                         for k in self.knowledge],
        }

    @staticmethod
    def _rule_label(rule: DecisionRule) -> str:
        if "owner_manual_edit" in rule.evidence_ids:
            return rule.condition
        return f"IF {rule.condition} THEN {rule.action} (risk: {rule.risk_level})"

    def apply_ui_update(self, payload: dict[str, Any]) -> None:
        """Apply owner edits without re-writing unchanged extracted evidence/decisions."""
        self.subject = (payload.get("name") or self.subject).strip()
        self.role = (payload.get("role") or self.role).strip()
        tone = (payload.get("writing_style") or {}).get("tone", "").strip()
        if tone:
            self.style.tone_notes = [tone]
        if "knowledge_facts" in payload:
            old = {k.statement: k for k in self.knowledge}
            self.knowledge = [old.get(s, Fact(statement=s, evidence_ids=["owner_manual_edit"]))
                              for s in dict.fromkeys(payload["knowledge_facts"]) if s.strip()]
        if "decision_heuristics" in payload:
            old = {self._rule_label(r): r for r in self.decision_rules}
            self.decision_rules = [old.get(s, DecisionRule(
                domain="general", condition=s, action="Owner supplied decision preference",
                risk_level="varies", confidence=1.0, evidence_ids=["owner_manual_edit"]))
                for s in dict.fromkeys(payload["decision_heuristics"]) if s.strip()]
