"""Parsers: raw files -> Document objects. One function per source format."""
from __future__ import annotations

import datetime as dt
import json
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

from app.models.documents import Document, SourceType

OWNER_EMAIL = "eleni.markou@aegeanstructures.example"
OWNER_NAME = "Eleni"


def _read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def parse_eml(path: Path) -> Document:
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    body_part = msg.get_body(preferencelist=("plain",))
    body = body_part.get_content().strip() if body_part else ""
    sender = getaddresses([msg["From"] or ""])[0][1]
    recipients = [a for _, a in getaddresses([msg["To"] or ""])]
    try:
        date = parsedate_to_datetime(msg["Date"]) if msg["Date"] else None
    except (TypeError, ValueError):
        date = None
    return Document(
        id=path.stem,
        source_type=SourceType.EMAIL,
        date=date,
        title=str(msg["Subject"] or ""),
        author=sender,
        participants=[sender, *recipients],
        text=body,
        metadata={"direction": "outgoing" if sender == OWNER_EMAIL else "incoming", "file": path.name},
    )


def parse_emails_dir(directory: Path) -> list[Document]:
    return [parse_eml(p) for p in sorted(directory.glob("*.eml"))]


def parse_chats_jsonl(path: Path) -> list[Document]:
    """One Document per chat thread; the owner's own lines are kept identifiable for style learning."""
    docs = []
    for t in _read_jsonl(path):
        lines = [f"{m['from']}: {m['text']}" for m in t["messages"]]
        owner_lines = [m["text"] for m in t["messages"] if m["from"] == OWNER_NAME]
        docs.append(Document(
            id=t["id"],
            source_type=SourceType.CHAT,
            date=dt.datetime.fromisoformat(t["messages"][0]["ts"]),
            title="chat with " + ", ".join(p for p in t["participants"] if p != OWNER_NAME),
            author=OWNER_NAME,
            participants=t["participants"],
            text="\n".join(lines),
            metadata={"owner_messages": owner_lines, "n_messages": len(lines)},
        ))
    return docs


def _split_front_matter(raw: str) -> tuple[dict[str, str], str]:
    if raw.startswith("---\n"):
        end = raw.find("\n---\n", 4)
        if end != -1:
            meta = {}
            for line in raw[4:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            return meta, raw[end + 5:].strip()
    return {}, raw.strip()


def parse_note_md(path: Path) -> Document:
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"))
    date = dt.datetime.fromisoformat(meta["date"]) if meta.get("date") else None
    return Document(
        id=path.stem,
        source_type=SourceType.NOTE,
        date=date,
        title=meta.get("title", path.stem),
        author=OWNER_NAME,
        text=body,
        metadata={"note_type": meta.get("type", "note")},
    )


def parse_notes_dir(directory: Path) -> list[Document]:
    return [parse_note_md(p) for p in sorted(directory.glob("*.md"))]


def parse_document_md(path: Path) -> Document:
    text = path.read_text(encoding="utf-8").strip()
    title = text.splitlines()[0].lstrip("# ").strip() if text else path.stem
    return Document(id=path.stem, source_type=SourceType.DOCUMENT, title=title, author=OWNER_NAME, text=text)


def parse_documents_dir(directory: Path) -> list[Document]:
    return [parse_document_md(p) for p in sorted(directory.glob("*.md"))]


def parse_history_decisions(path: Path) -> list[Document]:
    """Past, labelled situations -> decision Documents. Refuses the evaluation answer key."""
    if "evaluation" in path.parts:
        raise PermissionError("ingestion must never read the evaluation directory")
    docs = []
    for r in _read_jsonl(path):
        a = r["answer"]
        text = (f"Situation: {r['situation']}\nRisk level: {a['risk_level']}\n"
                f"Decision: {a['decision']}\nWhy: {a['rationale']}")
        docs.append(Document(
            id=f"decision-{r['scenario_id']}",
            source_type=SourceType.DECISION,
            date=dt.datetime.fromisoformat(r["date"]),
            title=f"{r['domain']}/{r['type']}",
            author=OWNER_NAME,
            text=text,
            metadata={"scenario_id": r["scenario_id"], "domain": r["domain"], "scenario_type": r["type"],
                      "risk_level": a["risk_level"], "data": r["data"]},
        ))
    return docs
