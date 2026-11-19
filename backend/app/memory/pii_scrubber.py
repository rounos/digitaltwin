import re


def scrub_pii(text: str) -> str:
    """Αντικαθιστά emails, τηλέφωνα, IPs και IBAN με ασφαλή placeholders."""
    # Emails
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]", text)
    # Ελληνικά & διεθνή τηλέφωνα
    text = re.sub(r"(\+30\s?)?69\d{8}\b|\b2\d{9}\b", "[REDACTED_PHONE]", text)
    # IBAN
    text = re.sub(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", "[REDACTED_IBAN]", text)
    # IPv4 διευθύνσεις (εκτός localhost)
    text = re.sub(r"\b(?!127\.0\.0\.1)(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]", text)
    return text