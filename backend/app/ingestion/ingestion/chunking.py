"""Split Documents into Chunks. Short items (email, chat, decision) stay whole; long ones are split on paragraphs."""
from __future__ import annotations

from app.ingestion.pii import mask_pii
from app.models.documents import Chunk, Document


def split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    chunks, cur = [], ""
    for p in paragraphs:
        while len(p) > max_chars:  # a single oversized paragraph: hard split
            head, p = p[:max_chars], p[max_chars - overlap:]
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(head)
        if cur and len(cur) + len(p) + 2 > max_chars:
            chunks.append(cur)
            cur = cur[-overlap:] + "\n\n" + p if overlap else p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def chunk_document(doc: Document, max_chars: int = 1200, overlap: int = 150, mask: bool = True) -> list[Chunk]:
    # prepend the subject so that the topic stays attached to every chunk
    header = f"{doc.title}\n\n" if doc.title and doc.source_type.value in ("email", "document", "note") else ""
    out = []
    for i, part in enumerate(split_text(doc.text, max_chars, overlap)):
        text, n = mask_pii(header + part) if mask else (header + part, 0)
        out.append(Chunk(
            id=f"{doc.id}#{i}",
            doc_id=doc.id,
            source_type=doc.source_type,
            date=doc.date,
            text=text,
            pii_masked=n,
            metadata={k: v for k, v in doc.metadata.items() if k != "data"} | {"title": doc.title, "author": doc.author},
        ))
    return out
