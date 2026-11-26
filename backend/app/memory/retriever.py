import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from .pii_scrubber import scrub_pii

from app.config import get_settings

# Resolve dynamically so tests, Windows and Docker share the same data-directory contract.
def _memory_file() -> Path:
    return get_settings().memories_file


DEFAULT_MEMORIES: List[Dict[str, str]] = [
    {
        "source": "Red-Team Report 14/10",
        "content": "Κανένα AI agent release σε production χωρίς automated adversarial evals (promptfoo & garak suite).",
    },
    {
        "source": "Audit Note 18/10",
        "content": "Τα system prompts δεν αποτελούν security boundary — σπάνε σε <5 λεπτά με roleplay ή encoding χωρίς εξωτερικό classifier.",
    },
    {
        "source": "Incident Review 29/10",
        "content": "Ο περιορισμός του blast radius προηγείται της αυτοματοποίησης: κάθε write action ή external email απαιτεί human-in-the-loop approval.",
    },
    {
        "source": "Slack Security Thread 02/11",
        "content": "Σε customer-facing LLMs απαιτούμε πάντα ξεχωριστό input/output guardrail layer και PII/DLP filtering πριν επιστραφεί απάντηση.",
    },
    {
        "source": "Architecture Review 08/11",
        "content": "Απορρίπτουμε αόριστες υποσχέσεις ασφαλείας — ζητάμε μετρήσιμα failure rates, jailbreak pass-rates και audit logs.",
    },
]


def _load_memories() -> List[Dict[str, str]]:
    if not _memory_file().exists():
        _save_memories(DEFAULT_MEMORIES)
        return list(DEFAULT_MEMORIES)
    try:
        with open(_memory_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else list(DEFAULT_MEMORIES)
    except (json.JSONDecodeError, OSError):
        return list(DEFAULT_MEMORIES)


def _save_memories(memories: List[Dict[str, str]]) -> None:
    _memory_file().parent.mkdir(parents=True, exist_ok=True)
    with open(_memory_file(), "w", encoding="utf-8") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def get_all_memories() -> List[Dict[str, str]]:
    return _load_memories()


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[\wάέήίόύώΆΈΉΊΌΎΏ]{3,}", text.lower())
    stopwords = {"και", "για", "την", "των", "της", "του", "στο", "στην", "ένα", "μια", "δεν", "που", "είναι", "από", "the", "and", "for"}
    return {w for w in words if w not in stopwords}


def retrieve_memories(query: str, top_k: int = 3) -> List[str]:
    """
    Ανακτά τις πιο σχετικές μνήμες για το ερώτημα (RAG retrieval).
    Αν δεν βρεθεί κανένα κοινό token (π.χ. άσχετο θέμα όπως budget), επιστρέφει κενή λίστα
    ώστε να ενεργοποιηθεί το anti-hallucination guardrail.
    """
    memories = _load_memories()
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: List[tuple[int, str]] = []
    for item in memories:
        formatted = f"{item['source']}: {item['content']}"
        mem_tokens = _tokenize(formatted)
        overlap = len(query_tokens & mem_tokens)
        if overlap > 0:
            scored.append((overlap, formatted))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:top_k]]


def ingest_documents(documents: List[Dict[str, str]]) -> int:
    """
    Δέχεται λίστα από {"filename": str, "text": str}, καθαρίζει PII,
    σπάει το κείμενο σε chunks και τα προσθέτει στο persistent memory store.
    """
    memories = _load_memories()
    added_count = 0

    for doc in documents:
        filename = doc.get("filename", "uploaded_doc")
        clean_text = scrub_pii(doc.get("text", "")).strip()
        if not clean_text:
            continue

        # Χωρισμός σε παραγράφους / chunks
        chunks = [c.strip() for c in re.split(r"\n{2,}|(?<=[.!;])\s+", clean_text) if len(c.strip()) > 20]
        if not chunks:
            chunks = [clean_text]

        for idx, chunk in enumerate(chunks[:15], start=1):
            memories.append({
                "source": f"Ingested ({filename} #{idx})",
                "content": chunk,
            })
            added_count += 1

    _save_memories(memories)
    return added_count

def replace_memories(items: List[Dict[str, str]]) -> None:
    """Replace demo memories with the owner's uploaded, PII-scrubbed source records."""
    _save_memories(items)
