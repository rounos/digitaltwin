import random
from typing import List
from fastapi import APIRouter, UploadFile, File
from app.models.schemas import (
    PersonaModel,
    TwinRespondRequest,
    TwinDraftResponse,
    TwinExplanation,
)

router = APIRouter()

# Προσωρινή in-memory αποθήκευση μέχρι να συνδεθεί η Postgres / persona store
CURRENT_PERSONA: dict = {}


@router.put("/persona", tags=["Persona"])
async def update_persona(persona: PersonaModel):
    global CURRENT_PERSONA
    CURRENT_PERSONA = persona.model_dump()
    return {"status": "saved", "persona_id": persona.persona_id}


@router.post("/twin/respond", response_model=TwinDraftResponse, tags=["Twin"])
async def generate_twin_response(payload: TwinRespondRequest):
    # TODO: Εδώ θα κουμπώσουν τα ai/, memory/, persona/ των συμφοιτητών σου
    msg_lower = payload.incoming_message.lower()
    is_unknown = "budget" in msg_lower or "τιμή" in msg_lower

    if is_unknown:
        return TwinDraftResponse(
            draft_id=random.randint(100, 999),
            status="needs_human_input",
            twin_reply="[Backend API] Δεν υπάρχουν τεκμήρια για το budget στο footprint. Παραπέμπω στον owner.",
            confidence_score=0.18,
            is_uncertain=True,
            explanation=TwinExplanation(
                applied_rules=["Anti-hallucination Guardrail: Άρνηση εικασίας"],
                retrieved_memories=["Καμία εγγραφή για οικονομικά στο Vector Store"],
                style_notes="Ουδέτερος, ασφαλής τόνος χωρίς εικασίες.",
            ),
        )

    return TwinDraftResponse(
        draft_id=random.randint(100, 999),
        status="pending_approval",
        twin_reply=(
            f"[Backend API] Καλησπέρα. Έλαβα το αίτημα: «{payload.incoming_message}». "
            "Δεν εγκρίνω go-live χωρίς red-teaming suite και περιορισμό του blast radius.\n\n- Μάρκος"
        ),
        confidence_score=0.94,
        is_uncertain=False,
        explanation=TwinExplanation(
            applied_rules=[
                "Μπλοκάρει οποιοδήποτε AI deployment χωρίς red-teaming",
                "Απαιτεί human-in-the-loop approval για ενέργειες με υψηλό blast radius",
            ],
            retrieved_memories=[
                "Red-Team Report 14/10: Κανένα release χωρίς automated adversarial evals."
            ],
            style_notes="Αναλυτικός, ευθύς, εστιασμένος στο ρίσκο.",
        ),
    )


@router.post("/twin/approve/{draft_id}", tags=["Twin"])
async def approve_draft(draft_id: int, edited_reply: str = ""):
    return {"status": "approved", "draft_id": draft_id, "final_reply": edited_reply}


@router.post("/ingest", tags=["Ingestion"])
async def ingest_files(files: List[UploadFile] = File(...)):
    filenames = [f.filename for f in files]
    return {
        "message": f"Αναλύθηκαν {len(filenames)} αρχεία ({', '.join(filenames)}) από το backend!",
        "count": len(filenames),
    }