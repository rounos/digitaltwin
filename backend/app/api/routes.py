"""Frontend-facing EchoMind API. The PersonaProfile is the persistence contract;
PersonaModel is the React-facing contract. No silent mock success responses.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from email import policy
from email.parser import BytesParser
from hashlib import sha256
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.ai.generator import generate_twin_response as generate_answer
from app.ai.llm import get_llm
from app.config import get_settings
from app.evaluation.evaluator import run_evaluation
from app.ingestion.chunking import chunk_document
from app.ingestion.pii import mask_pii
from app.memory.retriever import replace_memories, retrieve_memories
from app.models.documents import Document, SourceType
from app.models.schemas import PersonaModel, TwinDraftResponse, TwinRespondRequest
from app.persona.builder import build_persona
from app.persona.schema import PersonaProfile
from app.persona.store import PersonaStore

router = APIRouter()
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_SUFFIXES = {".txt", ".md", ".eml", ".json", ".jsonl", ".pdf"}


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return default


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    import os
    import tempfile
    fd, name = tempfile.mkstemp(prefix=".echomind-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(value, fp, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _store() -> PersonaStore:
    return PersonaStore(get_settings().persona_dir)


def _persona() -> PersonaProfile | None:
    return _store().load_latest()


def _ui_persona(profile: PersonaProfile | None) -> dict:
    if profile is None:
        return {
            "persona_id": "uninitialized", "persona_version": 0,
            "name": "Δεν έχει δημιουργηθεί persona", "role": "Ανέβασε τα δικά σου δεδομένα",
            "writing_style": {"tone": "Δεν υπάρχουν ακόμη δείγματα", "vocabulary_notes": ""},
            "decision_heuristics": [], "knowledge_facts": [],
            "preferences": [], "source_stats": {}, "evidence": [],
        }
    return profile.to_ui_dict()


@router.get("/persona", response_model=PersonaModel, tags=["Persona"])
async def get_persona():
    return _ui_persona(_persona())


@router.put("/persona", response_model=PersonaModel, tags=["Persona"])
async def update_persona(payload: PersonaModel):
    profile = _persona()
    if profile is None:
        raise HTTPException(status_code=409, detail="Πρώτα δημιούργησε persona μέσω ingestion")
    profile.apply_ui_update(payload.model_dump())
    return _store().save(profile).to_ui_dict()


def _document_from_upload(name: str, content: bytes) -> Document:
    """Read supported uploads in memory, redact PII before persisting chunks.
    .json/.jsonl is treated as textual evidence unless it is a recognised chat thread.
    """
    ext = Path(name).suffix.lower()
    text = ""
    kind = SourceType.DOCUMENT
    metadata: dict = {"file": name}
    if ext == ".pdf":
        import fitz
        try:
            with fitz.open(stream=content, filetype="pdf") as pdf:
                text = "\n".join(page.get_text() for page in pdf)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Μη έγκυρο PDF: {name}") from exc
    elif ext == ".eml":
        try:
            msg = BytesParser(policy=policy.default).parsebytes(content)
            part = msg.get_body(preferencelist=("plain",))
            text = part.get_content() if part else ""
            metadata["direction"] = "outgoing"  # uploaded by its owner, as labelled in UI
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Μη έγκυρο EML: {name}") from exc
        kind = SourceType.EMAIL
    else:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"Το {name} πρέπει να είναι UTF-8") from exc
        if ext in {".json", ".jsonl"}:
            kind = SourceType.CHAT
            try:
                rows = [json.loads(line) for line in text.splitlines() if line.strip()] if ext == ".jsonl" else json.loads(text)
                if isinstance(rows, dict):
                    rows = [rows]
                own_messages = []
                for thread in rows:
                    if isinstance(thread, dict) and isinstance(thread.get("messages"), list):
                        own_messages.extend(str(m.get("text", "")) for m in thread["messages"] if isinstance(m, dict) and m.get("owner") is True)
                if own_messages:
                    metadata["owner_messages"] = own_messages
            except (ValueError, TypeError):
                raise HTTPException(status_code=422, detail=f"Μη έγκυρο JSON: {name}")
        elif ext in {".txt", ".md"}:
            kind = SourceType.NOTE
    if not text.strip():
        raise HTTPException(status_code=422, detail=f"Το αρχείο {name} δεν περιέχει αναγνώσιμο κείμενο")
    cleaned, _ = mask_pii(text) if get_settings().mask_pii else (text, 0)
    stable = sha256((name + "\n" + cleaned).encode("utf-8")).hexdigest()[:16]
    return Document(id=f"upload-{stable}", title=name, source_type=kind, text=cleaned, metadata=metadata)


def _uploaded_documents() -> list[Document]:
    location = get_settings().uploads_dir / "documents.json"
    return [Document.model_validate(doc) for doc in _read_json(location, [])]


@router.post("/ingest", tags=["Ingestion"])
async def ingest_files(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Επίλεξε τουλάχιστον ένα αρχείο")
    incoming = []
    for file in files:
        name = Path(file.filename or "").name
        if not name or Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
            raise HTTPException(status_code=415, detail=f"Μη υποστηριζόμενος τύπος αρχείου: {name}")
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"Το αρχείο {name} υπερβαίνει τα 5 MB")
        incoming.append(_document_from_upload(name, content))
    stored = {d.id: d for d in _uploaded_documents()}
    for doc in incoming:
        stored[doc.id] = doc
    docs = list(stored.values())
    settings = get_settings()
    chunks = [c for d in docs for c in chunk_document(d, settings.chunk_max_chars, settings.chunk_overlap, settings.mask_pii)]
    # The memory store is replaced by the uploaded person's data, not mixed with the seeded demo personality.
    replace_memories([{"source": f"{mask_pii(d.title)[0]} / {c.id}", "content": c.text} for d in docs for c in chunks if c.doc_id == d.id])
    _write_json(settings.uploads_dir / "documents.json", [d.model_dump(mode="json") for d in docs])
    current = _persona()
    llm = get_llm(settings)
    profile, report = build_persona(docs, llm, mask=settings.mask_pii,
                                    owner_name=current.subject if current else "Ο χρήστης")
    if current is not None:
        profile.role = current.role
        # Owner-entered facts/rules survive subsequent uploads; seeded claims do not.
        profile.knowledge.extend(k for k in current.knowledge
                                 if "owner_manual_edit" in k.evidence_ids and
                                 k.statement not in {x.statement for x in profile.knowledge})
        profile.decision_rules.extend(r for r in current.decision_rules
                                      if "owner_manual_edit" in r.evidence_ids and
                                      r.uid not in {x.uid for x in profile.decision_rules})
    if llm is None:
        # Do not pretend we learned decision rules without an active LLM.
        profile.limits.append("Persona extraction incomplete without a configured LLM API key.")
    saved = _store().save(profile)
    return {
        "message": f"Εισήχθησαν {len(incoming)} αρχεία, {len(chunks)} τμήματα μνήμης. Persona v{saved.version}." +
                   (" Για πλήρη εξαγωγή αποφάσεων απαιτείται LLM API key." if llm is None else ""),
        "count": len(docs), "chunks": len(chunks), "persona_version": saved.version,
        "llm_calls": report.get("llm_calls", 0), "persona": saved.to_ui_dict(),
    }


@router.post("/twin/respond", response_model=TwinDraftResponse, tags=["Twin"])
async def generate_twin_response(payload: TwinRespondRequest):
    person = _persona()
    if person is None:
        raise HTTPException(status_code=409, detail="Δεν έχει δημιουργηθεί persona")
    memories = retrieve_memories(payload.incoming_message, top_k=3)
    result = generate_answer(payload.incoming_message, person.to_ui_dict(), memories)
    # Track generated drafts so that review is an actual, verifiable change of state.
    path = get_settings().drafts_file
    drafts = _read_json(path, {})
    drafts[str(result["draft_id"])] = {"status": result["status"], "incoming_message": payload.incoming_message,
                                        "twin_reply": result["twin_reply"],
                                        "confidence": round(result["confidence_score"] * 100)}
    _write_json(path, drafts)
    return TwinDraftResponse(**result)


class ReviewRequest(BaseModel):
    action: Literal["approved", "rejected"]
    edited_reply: str = Field(default="", max_length=20000)


@router.post("/twin/review/{draft_id}", tags=["Twin"])
async def review_draft(draft_id: int, review: ReviewRequest):
    settings = get_settings()
    drafts = _read_json(settings.drafts_file, {})
    draft = drafts.get(str(draft_id))
    if draft is None:
        raise HTTPException(status_code=404, detail="Δεν βρέθηκε αυτό το draft")
    if draft["status"] in {"approved", "rejected"}:
        raise HTTPException(status_code=409, detail="Το draft έχει ήδη ελεγχθεί")
    draft["status"] = review.action
    draft["final_reply"] = review.edited_reply if review.action == "approved" else ""
    drafts[str(draft_id)] = draft
    _write_json(settings.drafts_file, drafts)
    events = _read_json(settings.audit_file, [])
    events.insert(0, {"id": draft_id, "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                      "persona": _ui_persona(_persona())["name"], "prompt": mask_pii(draft["incoming_message"])[0],
                      "reply": draft["final_reply"], "action": review.action,
                      "confidence": draft.get("confidence", 0)})
    _write_json(settings.audit_file, events)
    return {"status": review.action, "draft_id": draft_id, "sent": False,
            "message": "Η απόφαση αποθηκεύτηκε. Δεν αποστέλλεται μήνυμα σε τρίτο."}


@router.get("/audit", tags=["Audit"])
async def audit_history():
    return {"events": _read_json(get_settings().audit_file, [])}


@router.get("/evaluation/latest", tags=["Evaluation"])
async def latest_evaluation():
    result = _read_json(get_settings().data_dir / "runtime" / "evaluation.json", None)
    profile = _persona()
    if result and profile and result.get("meta", {}).get("persona_version") != profile.version:
        result = None
    return {"available": bool(result), "result": result}


@router.post("/evaluation/run", tags=["Evaluation"])
async def execute_benchmark(limit: int = 5):
    if not 1 <= limit <= 20:
        raise HTTPException(status_code=422, detail="limit 1..20")
    if get_llm() is None:
        raise HTTPException(status_code=503, detail="Για πραγματική αξιολόγηση απαιτείται API key")

    async def call_twin(prompt: str):
        return (await generate_twin_response(TwinRespondRequest(incoming_message=prompt))).model_dump()

    result = await run_evaluation(call_twin, limit=limit)
    result["meta"] = {"evaluation_type": "holdout", "limit": limit,
                      "note": "Heuristic test-set score; not an independently calibrated fidelity probability.",
                      "persona_version": _persona().version if _persona() else 0}
    _write_json(get_settings().data_dir / "runtime" / "evaluation.json", result)
    return result
