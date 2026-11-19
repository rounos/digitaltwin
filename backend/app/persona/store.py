"""Versioned persona storage: one JSON file per version, so the owner can inspect, diff and roll back."""
from __future__ import annotations

import datetime as dt
import os
import re
import tempfile
from pathlib import Path

from app.persona.schema import DecisionRule, Fact, PersonaProfile, StyleProfile

_NAME = re.compile(r"persona_v(\d+)\.json$")


class PersonaStore:
    def __init__(self, directory: Path):
        self.dir = Path(directory)

    def versions(self) -> list[int]:
        if not self.dir.exists():
            return []
        return sorted(int(m.group(1)) for p in self.dir.iterdir() if (m := _NAME.search(p.name)))

    def _path(self, version: int) -> Path:
        return self.dir / f"persona_v{version:03d}.json"

    def save(self, profile: PersonaProfile) -> PersonaProfile:
        self.dir.mkdir(parents=True, exist_ok=True)
        existing = self.versions()
        profile.version = (existing[-1] + 1) if existing else 1
        profile.created_at = dt.datetime.now(dt.timezone.utc)
        fd, tmp = tempfile.mkstemp(dir=self.dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(profile.model_dump_json(indent=2))
        os.replace(tmp, self._path(profile.version))  # atomic: never leaves a half-written file
        return profile

    def load(self, version: int) -> PersonaProfile:
        return PersonaProfile.model_validate_json(self._path(version).read_text(encoding="utf-8"))

    def load_latest(self) -> PersonaProfile | None:
        v = self.versions()
        return self.load(v[-1]) if v else None

    def load_or_seed(self, subject: str = "Μάρκος Βλάχος") -> PersonaProfile:
        latest = self.load_latest()
        if latest is not None:
            return latest
        seed = PersonaProfile(
            subject=subject,
            role="AI Red Teamer & Adversarial Testing Lead",
            style=StyleProfile(tone_notes=["Αναλυτικός, σκεπτικιστής, ευθύς, με εστίαση στα edge cases και το ρίσκο"]),
            knowledge=[
                Fact(statement="Εξειδίκευση σε LLM Red Teaming, Prompt Injection & Guardrails", evidence_ids=["seed_01"]),
                Fact(statement="Χρησιμοποιεί garak, promptfoo και custom adversarial datasets", evidence_ids=["seed_02"]),
            ],
            decision_rules=[
                DecisionRule(
                    domain="ai_security",
                    condition="AI agent goes to production without red-teaming & injection suite",
                    action="Block deployment until adversarial evals pass",
                    risk_level="critical",
                    confidence=0.98,
                    evidence_ids=["seed_01"],
                ),
                DecisionRule(
                    domain="ai_security",
                    condition="Action has high blast radius (DB write, external emails)",
                    action="Require mandatory human-in-the-loop approval",
                    risk_level="high",
                    confidence=0.95,
                    evidence_ids=["seed_03"],
                ),
            ],
            limits=["Situations outside the evidence (budgets, new domains) are not covered."],
        )
        return self.save(seed)