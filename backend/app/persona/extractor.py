"""LLM-based extraction of knowledge, preferences, risk attitudes and decision rules, with grounding checks."""
from __future__ import annotations

import json
import re

from app.ai.llm import StructuredLLM
from app.ingestion.pii import mask_pii
from app.models.documents import Document
from app.persona.schema import ExtractionResult, PersonaProfile

SYSTEM_RULES = """You build an inspectable profile of ONE person from evidence about their past decisions.
Infer the decision rules they follow: the condition (use numeric thresholds only when the examples support them),
the action they take, the risk level they assign, and your confidence (0-1; high only when several examples agree).
Use ONLY the evidence provided. Never invent facts. Every item must cite evidence_ids copied exactly from the
[brackets] of the documents that support it. Leave lists empty when the evidence has nothing for them.
Write conditions and actions in English. tone_notes may stay empty in this pass."""

SYSTEM_GENERAL = """You build an inspectable profile of ONE person from their notes, documents, emails and chats.
Extract: knowledge (stable facts and expertise about them), preferences (habits and how they like things done),
risk_attitudes (how cautious or bold they are per domain), decision_rules (only if clearly supported), and
tone_notes (short observations about how they write and sound, in English).
Use ONLY the evidence provided. Never invent facts. Every item must cite evidence_ids copied exactly from the
[brackets] of the documents that support it. Leave lists empty when the evidence has nothing for them."""


def render_docs(docs: list[Document], mask: bool, max_chars: int = 12000) -> list[str]:
    """Render documents as '[id] ...' blocks and pack them into batches under max_chars."""
    batches, cur = [], ""
    for d in docs:
        text = mask_pii(d.text)[0] if mask else d.text
        extra = ""
        if "data" in d.metadata:
            extra = "\nData: " + json.dumps(d.metadata["data"], ensure_ascii=False)
            if mask: extra = mask_pii(extra)[0]
        block = f"[{d.id}] ({d.source_type.value}, {d.date.date() if d.date else 'n/a'}) {mask_pii(d.title)[0] if mask else d.title}\n{text}{extra}\n\n"
        if cur and len(cur) + len(block) > max_chars:
            batches.append(cur)
            cur = ""
        cur += block
    if cur:
        batches.append(cur)
    return batches


def extract(llm: StructuredLLM, system: str, docs: list[Document], mask: bool, max_chars: int = 12000) -> list[ExtractionResult]:
    return [llm.parse(system, batch, ExtractionResult) for batch in render_docs(docs, mask, max_chars)]


def _key(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()[:90]


def merge(profile: PersonaProfile, res: ExtractionResult) -> None:
    """Fold one extraction result into the profile, de-duplicating and unioning evidence."""
    def fold(target: list, items: list, keyfn):
        index = {keyfn(x): x for x in target}
        for it in items:
            k = keyfn(it)
            if k in index:
                old = index[k]
                old.evidence_ids = sorted(set(old.evidence_ids) | set(it.evidence_ids))
                if hasattr(old, "confidence"):
                    old.confidence = max(old.confidence, it.confidence)
            else:
                target.append(it)
                index[k] = it

    fold(profile.knowledge, res.knowledge, lambda x: _key(x.statement))
    fold(profile.preferences, res.preferences, lambda x: _key(x.topic + x.statement))
    fold(profile.risk_attitudes, res.risk_attitudes, lambda x: x.domain + _key(x.stance))
    fold(profile.decision_rules, res.decision_rules, lambda x: x.domain + _key(x.condition) + _key(x.action))
    for n in res.tone_notes:
        if _key(n) not in {_key(t) for t in profile.style.tone_notes}:
            profile.style.tone_notes.append(n)


def sanitize(profile: PersonaProfile, valid_ids: set[str]) -> dict[str, int]:
    """Grounding check: drop hallucinated evidence ids, then drop items left without any evidence."""
    dropped = {"evidence_ids": 0, "items": 0}
    for attr in ("knowledge", "preferences", "risk_attitudes", "decision_rules"):
        kept = []
        for it in getattr(profile, attr):
            good = [e for e in it.evidence_ids if e in valid_ids]
            dropped["evidence_ids"] += len(it.evidence_ids) - len(good)
            it.evidence_ids = good
            if hasattr(it, "confidence"):
                it.confidence = min(max(it.confidence, 0.0), 1.0)
            if good:
                kept.append(it)
            else:
                dropped["items"] += 1
        setattr(profile, attr, kept)
    return dropped