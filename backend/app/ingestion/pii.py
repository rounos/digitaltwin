"""Rule-based PII masking (first line of defence). For names/addresses use NER (e.g. Presidio) later."""
import re

# order matters: more specific patterns first
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("IBAN", re.compile(r"\bGR\d{2}(?: ?\d{4}){5} ?\d{3}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("PHONE", re.compile(r"\+30[\s-]?\d{2,4}(?:[\s-]?\d{3,4}){2}")),
    ("PHONE", re.compile(r"\b(?:69\d{8}|2\d{9})\b")),
    ("AFM", re.compile(r"(?i)(?:ΑΦΜ|AFM)[:\s]*\d{9}\b")),
    ("AMKA", re.compile(r"\b(?:0[1-9]|[12]\d|3[01])(?:0[1-9]|1[0-2])\d{2}\d{5}\b")),
]


def mask_pii(text: str) -> tuple[str, int]:
    """Return (masked_text, number_of_items_masked). Emergency numbers (112, 166, 199) are left alone."""
    count = 0
    for label, pat in _PATTERNS:
        text, n = pat.subn(f"[{label}]", text)
        count += n
    return text, count
