"""Orchestrates persona building: stylometry (no LLM) + LLM extraction passes + grounding check."""
from __future__ import annotations

import sys
from collections import defaultdict

from app.ai.llm import StructuredLLM, get_llm
from app.config import Settings, get_settings
from app.ingestion.parsers import OWNER_NAME
from app.ingestion.pipeline import load_documents
from app.models.documents import Document, SourceType
from app.persona import extractor, stylometry
from app.persona.schema import PersonaProfile
from app.persona.store import PersonaStore

DEFAULT_LIMITS = [
    "Situations outside the evidence (new domains, missing data) are not covered by the learned rules.",
    "Style is measured from emails and chats only; other channels may differ.",
]


def build_persona(docs: list[Document], llm: StructuredLLM | None, mask: bool = True, max_chars: int = 12000, owner_name: str | None = None) -> tuple[PersonaProfile, dict]:
    profile = PersonaProfile(subject=owner_name or OWNER_NAME, limits=list(DEFAULT_LIMITS))
    profile.source_stats = {t.value: sum(1 for d in docs if d.source_type == t) for t in SourceType}
    profile.style = stylometry.compute(docs, owner=owner_name or OWNER_NAME)  # deterministic, always available
    report = {"llm_calls": 0}

    if llm is not None:
        # pass A: decision rules, one pass per domain so patterns are not mixed across domains
        by_domain: dict[str, list[Document]] = defaultdict(list)
        for d in docs:
            if d.source_type == SourceType.DECISION:
                by_domain[d.metadata.get("domain", "general")].append(d)
        for domain_docs in by_domain.values():
            for res in extractor.extract(llm, extractor.SYSTEM_RULES, domain_docs, mask, max_chars):
                extractor.merge(profile, res)
                report["llm_calls"] += 1
        # pass B: personal knowledge, preferences, tone from notes + documents + the owner's own writing
        general = [d for d in docs if d.source_type in (SourceType.NOTE, SourceType.DOCUMENT)
                   and d.metadata.get("note_type") != "decision_log"]
        general += [d for d in docs if d.source_type == SourceType.CHAT and d.metadata.get("owner_messages")]
        general += [d for d in docs if d.source_type == SourceType.EMAIL and d.metadata.get("direction") == "outgoing"]
        for res in extractor.extract(llm, extractor.SYSTEM_GENERAL, general, mask, max_chars):
            extractor.merge(profile, res)
            report["llm_calls"] += 1

    report["dropped"] = extractor.sanitize(profile, {d.id for d in docs})
    return profile, report


def main(argv: list[str]) -> None:
    s: Settings = get_settings()
    llm = None if "--no-llm" in argv else get_llm(s)
    if llm is None:
        print("[persona] no LLM configured (OPENAI_API_KEY missing or --no-llm): stylometry only", file=sys.stderr)
    docs = load_documents(s)
    profile, report = build_persona(docs, llm, s.mask_pii)
    saved = PersonaStore(s.persona_dir).save(profile)
    print(f"persona v{saved.version} saved to {s.persona_dir}")
    print(f"rules={len(saved.decision_rules)} preferences={len(saved.preferences)} knowledge={len(saved.knowledge)} "
          f"llm_calls={report['llm_calls']} dropped={report['dropped']}")


if __name__ == "__main__":
    main(sys.argv[1:])