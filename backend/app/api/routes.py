from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import (
    PersonaModel,
    TwinRespondRequest,
    TwinDraftResponse,
)
from app.ai.generator import generate_twin_response as ai_generate_twin_response
from app.evaluation.evaluator import run_evaluation

router = APIRouter()

CURRENT_PERSONA: dict = {
    "persona_id": "default_user",
    "name": "Μάρκος Βλάχος",
    "role": "AI Red Teamer & Adversarial Testing Lead",
    "writing_style": {
        "tone": "Αναλυτικός, σκεπτικιστής, ευθύς, με εστίαση στα edge cases και το ρίσκο",
        "vocabulary_notes": "Χρησιμοποιεί ορολογία AI safety (jailbreaks, prompt injection, blast radius, evals), χωρίς περιττές ευγένες.",
    },
    "decision_heuristics": [
        "Μπλοκάρει οποιοδήποτε AI deployment αν δεν έχει περάσει red-teaming & prompt injection suite",
        "Απαιτεί πάντα human-in-the-loop approval για ενέργειες με υψηλό blast radius (π.χ. DB write, external emails)",
        "Απορρίπτει αόριστες υποσχέσεις ασφαλείας — ζητάει μετρήσιμα failure rates και adversarial logs",
    ],
    "knowledge_facts": [
        "Εξειδίκευση σε LLM Red Teaming, Prompt Injection, Jailbreak evaluation και Guardrails",
        "Χρησιμοποιεί garak, promptfoo και custom adversarial datasets για stress-testing μοντέλων",
    ],
}


def _retrieve_relevant_memories(query: str) -> List[str]:
    """Προσπαθεί να ανακτήσει μνήμες από το memory/retriever.py, αλλιώς επιστρέφει κενή λίστα."""
    try:
        from app.memory.retriever import retrieve_memories
        hits = retrieve_memories(query, top_k=3)
        return [h["text"] if isinstance(h, dict) and "text" in h else str(h) for h in hits]
    except Exception:
        return []

@router.get("/persona", tags=["Persona"])
async def get_persona():
    return CURRENT_PERSONA

@router.put("/persona", tags=["Persona"])
async def update_persona(persona: PersonaModel):
    global CURRENT_PERSONA
    CURRENT_PERSONA = persona.model_dump()
    return {"status": "saved", "persona_id": persona.persona_id}


@router.post("/twin/respond", response_model=TwinDraftResponse, tags=["Twin"])
async def generate_twin_response(payload: TwinRespondRequest):
    try:
        memories = _retrieve_relevant_memories(payload.incoming_message)
        result = ai_generate_twin_response(
            incoming_message=payload.incoming_message,
            persona=CURRENT_PERSONA,
            retrieved_memories=memories,
        )
        return TwinDraftResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Twin Inference Error: {str(exc)}")


@router.post("/twin/approve/{draft_id}", tags=["Twin"])
async def approve_draft(draft_id: int, edited_reply: str = ""):
    return {"status": "approved", "draft_id": draft_id, "final_reply": edited_reply}


@router.post("/ingest", tags=["Ingestion"])
async def ingest_files(files: List[UploadFile] = File(...)):
    filenames = []
    for f in files:
        content = (await f.read()).decode("utf-8", errors="ignore").strip()
        if content:
            snippet = f"[{f.filename}]: {content[:300]}"
            CURRENT_PERSONA.setdefault("knowledge_facts", []).append(snippet)
        filenames.append(f.filename)

    return {
        "message": f"Ενσωματώθηκαν {len(filenames)} αρχεία ({', '.join(filenames)}) στη μνήμη του Twin!",
        "count": len(filenames),
    }


@router.get("/evaluation/run", tags=["Evaluation"])
async def execute_benchmark(limit: int = 5):
    async def _call_twin(prompt: str):
        res = await generate_twin_response(TwinRespondRequest(incoming_message=prompt))
        return res.model_dump()

    return await run_evaluation(_call_twin, limit=limit)