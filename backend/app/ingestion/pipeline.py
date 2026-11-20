"""Orchestrates ingestion: raw files on disk -> Documents -> Chunks (ready for embeddings in memory/)."""
from __future__ import annotations

from collections import Counter

from app.config import Settings, get_settings
from app.ingestion import parsers
from app.ingestion.chunking import chunk_document
from app.models.documents import Chunk, Document


def load_documents(settings: Settings | None = None) -> list[Document]:
    s = settings or get_settings()
    fp = s.footprint_dir
    docs: list[Document] = []
    docs += parsers.parse_emails_dir(fp / "emails")
    if (fp / "chats" / "chats.jsonl").exists():
        docs += parsers.parse_chats_jsonl(fp / "chats" / "chats.jsonl")
    docs += parsers.parse_notes_dir(fp / "notes")
    docs += parsers.parse_documents_dir(fp / "documents")
    return docs


def build_chunks(docs: list[Document], settings: Settings | None = None) -> list[Chunk]:
    s = settings or get_settings()
    chunks: list[Chunk] = []
    for d in docs:
        chunks += chunk_document(d, s.chunk_max_chars, s.chunk_overlap, s.mask_pii)
    return chunks


def run(settings: Settings | None = None) -> tuple[list[Document], list[Chunk]]:
    docs = load_documents(settings)
    return docs, build_chunks(docs, settings)


if __name__ == "__main__":
    docs, chunks = run()
    print(f"documents: {len(docs)}  chunks: {len(chunks)}  pii masked: {sum(c.pii_masked for c in chunks)}")
    for k, v in sorted(Counter(d.source_type.value for d in docs).items()):
        print(f"  {k:9s} {v}")