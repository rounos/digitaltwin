"""Deterministic style measurements from the owner's own writing (outgoing emails, own chat lines)."""
from __future__ import annotations

import re
import statistics
from collections import Counter

from app.models.documents import Document, SourceType
from app.persona.schema import PatternShare, StyleChannel, StyleProfile

_EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
_GREEK = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")
_LATIN = re.compile(r"[A-Za-z]")
_WORD = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
_SENT = re.compile(r"[.!?;\u037e]+(?:\s|$)|\n+")
_QUESTION = re.compile(r"[?;\u037e](?:\s|$)")
_GREET = re.compile(r"^(Hi|Hello|Hey|Dear)\s+[\w.]+(,|!)?", re.I)
_STOP = set("that this with have will from your what when they them there their about would could should "
            "και για στο στη την του των ένα μια δεν είναι αλλά πως που και".split())


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text, re.UNICODE)


def _greeting(text: str) -> str | None:
    first = text.strip().splitlines()[0] if text.strip() else ""
    m = _GREET.match(first)
    return f"{m.group(1).capitalize()} <name>{m.group(2) or ''}" if m else None


def _signoff(text: str, owner: str = "Eleni") -> str | None:
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if len(lines) >= 2 and lines[-1] == owner:
        return lines[-2]
    return None


def _shares(items: list[str | None], top: int = 3) -> list[PatternShare]:
    valid = [i for i in items if i]
    if not valid:
        return []
    c = Counter(valid)
    return [PatternShare(pattern=p, share=round(n / len(items), 3)) for p, n in c.most_common(top)]


def _core(text: str, owner: str = "Eleni") -> str:
    """Email body without the greeting line and the sign-off block (those are measured separately)."""
    lines = text.strip().splitlines()
    if lines and _GREET.match(lines[0]):
        lines = lines[1:]
    if len(lines) >= 2 and lines[-1].strip() == owner:
        lines = lines[:-2]
    return "\n".join(lines).strip()


def _channel(name: str, texts: list[str], greetings=None, signoffs=None, raw: list[str] | None = None) -> StyleChannel | None:
    raw = raw or texts
    pairs = [(t, r) for t, r in zip(texts, raw) if t.strip()]
    if not pairs:
        return None
    texts, raw = [p[0] for p in pairs], [p[1] for p in pairs]
    n_words = [len(_words(t)) for t in texts]
    total_words = max(sum(n_words), 1)
    sentences = [s for t in texts for s in _SENT.split(t) if s.strip()]
    sent_words = [len(_words(s)) for s in sentences] or [0]
    joined = "\n".join(texts)
    greek, latin = len(_GREEK.findall(joined)), len(_LATIN.findall(joined))
    letters = max(greek + latin, 1)
    bullets = sum(1 for t in texts if re.search(r"^\s*[-•*]\s", t, re.M))
    top_words = [w for w, _ in Counter(w.lower() for w in _WORD.findall(joined) if w.lower() not in _STOP).most_common(10)]
    med = statistics.median(n_words)
    examples = sorted((r for t, r in zip(texts, raw) if len(_words(t)) >= 5), key=lambda r: abs(len(_words(r)) - med))[:3]
    return StyleChannel(
        channel=name,
        n_samples=len(texts),
        avg_words_per_message=round(statistics.mean(n_words), 1),
        avg_words_per_sentence=round(statistics.mean(sent_words), 1),
        exclamations_per_100_words=round(100 * joined.count("!") / total_words, 2),
        emoji_per_message=round(len(_EMOJI.findall(joined)) / len(texts), 2),
        question_rate=round(sum(1 for t in texts if _QUESTION.search(t)) / len(texts), 2),
        bullet_rate=round(bullets / len(texts), 2),
        greetings=_shares(greetings or []),
        signoffs=_shares(signoffs or []),
        language_share={"el": round(greek / letters, 2), "en": round(latin / letters, 2)},
        top_words=top_words,
        example_snippets=[e.strip() for e in examples],
    )


def compute(docs: list[Document]) -> StyleProfile:
    emails = [d.text for d in docs if d.source_type == SourceType.EMAIL and d.metadata.get("direction") == "outgoing"]
    chat_lines = [m for d in docs if d.source_type == SourceType.CHAT for m in d.metadata.get("owner_messages", [])]
    return StyleProfile(
        email=_channel("email", [_core(t) for t in emails], [_greeting(t) for t in emails], [_signoff(t) for t in emails], raw=emails),
        chat=_channel("chat", chat_lines),
    )
