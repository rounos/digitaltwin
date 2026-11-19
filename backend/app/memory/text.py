"""Shared tokenizer: lowercase, accent-insensitive (Greek 'σεισμός' == 'σεισμος'), words of 2+ letters (single digits kept: '9 km' matters)."""
import re
import unicodedata

_WORD = re.compile(r"\w+", re.UNICODE)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall(strip_accents(text.lower())) if len(w) >= 2 or w.isdigit()]
