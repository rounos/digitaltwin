"""Central settings, read from environment variables (never hard-code keys or paths)."""
import os
from dataclasses import dataclass
from pathlib import Path


def _default_data_dir() -> Path:
    # backend/app/config.py -> repo root is 3 levels up -> <root>/data/synthetic
    return Path(__file__).resolve().parents[2] / "data" / "synthetic"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    mask_pii: bool
    chunk_max_chars: int
    chunk_overlap: int
    openai_api_key: str | None  # read from .env, never committed
    openai_model: str
    persona_dir: Path
    memory_dir: Path
    embedder: str  # auto | openai | hash
    embed_model: str

    @property
    def footprint_dir(self) -> Path:
        return self.data_dir / "footprint"

    @property
    def history_file(self) -> Path:
        return self.data_dir / "scenarios" / "history_decisions.jsonl"

    @property
    def test_scenarios_file(self) -> Path:
        return self.data_dir / "scenarios" / "test_scenarios.jsonl"

    # ONLY the evaluation module may read this directory (it holds the answer key).
    @property
    def evaluation_dir(self) -> Path:
        return self.data_dir / "evaluation"


def get_settings() -> Settings:
    return Settings(
        data_dir=Path(os.getenv("DATA_DIR", str(_default_data_dir()))),
        mask_pii=os.getenv("MASK_PII", "true").lower() in ("1", "true", "yes"),
        chunk_max_chars=int(os.getenv("CHUNK_MAX_CHARS", "1200")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "150")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),  # use any model your hackathon key allows
        persona_dir=Path(os.getenv("PERSONA_DIR", str(_default_data_dir().parent / "persona"))),
        memory_dir=Path(os.getenv("MEMORY_DIR", str(_default_data_dir().parent / "memory"))),
        embedder=os.getenv("EMBEDDER", "auto").lower(),
        embed_model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
    )
