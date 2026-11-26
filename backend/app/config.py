from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel

_HERE = Path(__file__).resolve()
_BACKEND_DIR = _HERE.parents[1]  # backend/
_REPO_ROOT = _BACKEND_DIR.parent if (_BACKEND_DIR.parent / "data").exists() else _BACKEND_DIR


def _resolve_dir(env_var: str, default_rel: str) -> Path:
    val = os.getenv(env_var)
    if val: 
        return Path(val)
    docker_path = Path("/app") / default_rel
    if docker_path.exists():
        return docker_path
    return _REPO_ROOT / default_rel


class Settings(BaseModel):
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or None
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-6-luna")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    mask_pii: bool = os.getenv("MASK_PII", "true").lower() in ("1", "true", "yes")

    data_dir: Path = _resolve_dir("DATA_DIR", "data")
    persona_dir: Path = _resolve_dir("PERSONA_DIR", "data/persona")
    synthetic_dir: Path = _resolve_dir("SYNTHETIC_DIR", "data/synthetic")
    scenarios_dir: Path = _resolve_dir("SCENARIOS_DIR", "data/synthetic/scenarios")
    ground_truth_dir: Path = _resolve_dir("GROUND_TRUTH_DIR", "data/ground_truth")
    footprint_dir: Path = _resolve_dir("FOOTPRINT_DIR", "data/synthetic/footprint")
    uploads_dir: Path = _resolve_dir("UPLOADS_DIR", "data/runtime/uploads")
    memories_file: Path = _resolve_dir("MEMORIES_FILE", "data/memories.json")
    audit_file: Path = _resolve_dir("AUDIT_FILE", "data/runtime/audit.json")
    drafts_file: Path = _resolve_dir("DRAFTS_FILE", "data/runtime/drafts.json")
    chunk_max_chars: int = 1200
    chunk_overlap: int = 150
    embedder: str = os.getenv("EMBEDDER", "hash")
    embed_model: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.persona_dir.mkdir(parents=True, exist_ok=True)
    return s