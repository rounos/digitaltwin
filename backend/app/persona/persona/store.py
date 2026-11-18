"""Versioned persona storage: one JSON file per version, so the owner can inspect, diff and roll back."""
from __future__ import annotations

import datetime as dt
import os
import re
import tempfile
from pathlib import Path

from app.persona.schema import PersonaProfile

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
