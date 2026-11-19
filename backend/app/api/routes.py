from typing import List
from fastapi import APIRouter, UploadFile, File

from app.ai.generator import generate_twin_response as run_twin_pipeline
from app.config import get_settings
from app.evaluation.evaluator import run_evaluation
from app.memory.retriever import ingest_documents, retrieve_memories
from app.models.schemas import (
    PersonaModel,
    TwinRespondRequest,
    TwinDraftResponse,
    TwinExplanation,
)
from app.persona.store import PersonaStore

router = APIRouter()


def _get_store() -> PersonaStore:
    return PersonaStore(get_settings().persona_dir)


@router.get("/persona", tags=["Persona"])
async def get_persona():
    profile = _get_store().load_or_seed()
    return profile.to_ui_dict()


@router.put("/persona", tags=["Persona"])
async def update_persona(persona: PersonaModel):
    store = _get_store()
    profile = store.load_or_seed()
    profile.apply_ui_update(persona.model_dump())
    saved = store.save(profile)
    return {"status": "saved", "persona_id": f"v{saved.version:03d}"}


@router.post("/twin/respond", response_model=TwinDraftResponse, tags=["Twin"])
async def generate_twin_response(payload: TwinRespondRequest):
    profile = _get_store().load_or_seed()
    persona_dict = profile.to_ui_dict()
    memories = retrieve_memories(payload.incoming_message, top_k=3)

    result = run_twin_pipeline(
        incoming_message=payload.incoming_message,
        persona=persona_dict,
        retrieved_memories=memories,
    )

    return TwinDraftResponse(
        draft_id=result["draft_id"],
        status=result["status"],
        twin_reply=result["twin_reply"],
        confidence_score=result["confidence_score"],
        is_uncertain=result["is_uncertain"],
        explanation=TwinExplanation(**result["explanation"]),
    )


@router.post("/twin/approve/{draft_id}", tags=["Twin"])
async def approve_draft(draft_id: int, edited_reply: str = ""):
    return {"status": "approved", "draft_id": draft_id, "final_reply": edited_reply}


@router.post("/ingest", tags=["Ingestion"])
async def ingest_files(files: List[UploadFile] = File(...)):
    docs = []
    filenames = []
    for f in files:
        raw_bytes = await f.read()
        text = raw_bytes.decode("utf-8", errors="ignore")
        docs.append({"filename": f.filename or "document.txt", "text": text})
        filenames.append(f.filename or "document.txt")

    chunks_added = ingest_documents(docs)
    return {
        "message": f"Αναλύθηκαν {len(filenames)} αρχεία ({', '.join(filenames)}) και προστέθηκαν {chunks_added} καθαρισμένα memory chunks!",
        "count": len(filenames),
        "chunks_added": chunks_added,
    }


@router.get("/evaluation/run", tags=["Evaluation"])
async def execute_benchmark(limit: int = 5):
    async def _call_twin(prompt: str):
        res = await generate_twin_response(TwinRespondRequest(incoming_message=prompt))
        return res.model_dump()

    return await run_evaluation(_call_twin, limit=limit)