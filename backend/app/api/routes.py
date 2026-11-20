from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import (
    PersonaModel,
    TwinRespondRequest,
    TwinDraftResponse,
)
from app.ai.generator import generate_twin_response as ai_generate_twin_response
from app.ai.llm import get_llm
from app.config import get_settings
from app.evaluation.evaluator import run_evaluation
from app.ingestion.pipeline import run as run_ingestion_pipeline
from app.persona.builder import build_persona
from app.persona.store import PersonaStore

router = APIRouter()


def _get_active_persona() -> dict:
    """Φορτώνει την τελευταία version από το PersonaStore (χωρίς seed mock δεδομένα)."""
    settings = get_settings()
    store = PersonaStore(settings.persona_dir)
    latest = store.load_latest()
    if latest is None:
        return {
            "persona_id": "uninitialized",
            "name": "Άγνωστος Χρήστης (Δεν έχει γίνει ingestion)",
            "role": "Δεν έχουν φορτωθεί δεδομένα footprint",
            "writing_style": {"tone": "Ουδέτερος", "vocabulary_notes": ""},
            "decision_heuristics": [],
            "knowledge_facts": [],
        }
    return latest.model_dump()


def _retrieve_relevant_memories(query: str) -> List[str]:
    """Ανακτά μνήμες από το memory/retriever.py."""
    try:
        from app.memory.retriever import retrieve_memories
        hits = retrieve_memories(query, top_k=3)
        return [h["text"] if isinstance(h, dict) and "text" in h else str(h) for h in hits]
    except Exception:
        return []


@router.get("/persona", tags=["Persona"])
async def get_persona():
    return _get_active_persona()


@router.put("/persona", tags=["Persona"])
async def update_persona(persona: PersonaModel):
    settings = get_settings()
    store = PersonaStore(settings.persona_dir)
    latest = store.load_latest()
    if latest:
        latest.subject = persona.name
        latest.role = persona.role
        saved = store.save(latest)
        return {"status": "saved", "version": saved.version}
    return {"status": "no_persona_found"}


@router.post("/twin/respond", response_model=TwinDraftResponse, tags=["Twin"])
async def generate_twin_response(payload: TwinRespondRequest):
    try:
        active_persona = _get_active_persona()
        memories = _retrieve_relevant_memories(payload.incoming_message)
        result = ai_generate_twin_response(
            incoming_message=payload.incoming_message,
            persona=active_persona,
            retrieved_memories=memories,
        )
        return TwinDraftResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Twin Inference Error: {str(exc)}")


@router.post("/twin/approve/{draft_id}", tags=["Twin"])
async def approve_draft(draft_id: int, edited_reply: str = ""):
    return {"status": "approved", "draft_id": draft_id, "final_reply": edited_reply}


@router.post("/ingest", tags=["Ingestion"])
async def ingest_files(files: List[UploadFile] = File(default=[])):
    """
    Αποθηκεύει τα ανεβασμένα αρχεία (.txt, .json, .eml, .md) στον φάκελο footprint,
    τρέχει το πλήρες ingestion pipeline (chunking + vector store)
    και χτίζει νέο PersonaProfile μέσω stylometry + LLM extraction.
    """
    try:
        settings = get_settings()
        fp_dir = settings.footprint_dir
        saved_names = []

        for f in files:
            content = await f.read()
            if not content:
                continue
            fname = f.filename or "uploaded.txt"
            if fname.endswith(".eml"):
                target = fp_dir / "emails" / fname
            elif fname.endswith((".json", ".jsonl")):
                target = fp_dir / "chats" / "chats.jsonl"
            elif fname.endswith((".txt", ".md")):
                target = fp_dir / "notes" / f"{Path(fname).stem}.md"
            else:
                target = fp_dir / "documents" / fname

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            saved_names.append(fname)

        # 1. Φόρτωση & Chunking αποκλειστικά από το footprint_dir
        docs, chunks = run_ingestion_pipeline(settings)

        # 2. Αποθήκευση chunks στη μνήμη (VectorStore / memories.json)
        try:
            from app.memory.vector_store import VectorStore
            vs = VectorStore(settings.memories_file)
            vs.add_chunks(chunks)
        except Exception:
            pass

        # 3. Χτίσιμο Persona (Stylometry + LLM Extraction) & αποθήκευση
        llm = get_llm(settings)
        profile, report = build_persona(docs, llm, mask=settings.mask_pii)
        store = PersonaStore(settings.persona_dir)
        saved_profile = store.save(profile)

        return {
            "message": f"Ολοκληρώθηκε το ingestion ({len(docs)} έγγραφα, {len(chunks)} chunks). Δημιουργήθηκε persona v{saved_profile.version}!",
            "count": len(docs),
            "chunks": len(chunks),
            "persona_version": saved_profile.version,
            "llm_calls": report.get("llm_calls", 0),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion Error: {str(exc)}")


@router.get("/evaluation/run", tags=["Evaluation"])
async def execute_benchmark(limit: int = 5):
    async def _call_twin(prompt: str):
        res = await generate_twin_response(TwinRespondRequest(incoming_message=prompt))
        return res.model_dump()

    return await run_evaluation(_call_twin, limit=limit)