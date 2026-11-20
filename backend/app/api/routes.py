import os
import json
import random
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from google import genai
from google.genai import types
from app.models.schemas import (
    PersonaModel,
    TwinRespondRequest,
    TwinDraftResponse,
)
from app.evaluation.evaluator import run_evaluation

router = APIRouter()

# Default προφίλ (αντικαθίσταται όποτε πατάς "Αποθήκευση Προφίλ" στο Tab 2)
CURRENT_PERSONA: dict = {
    "persona_id": "default_user",
    "name": "Μάρκος Βλάχος",
    "role": "AI Red Teamer & Adversarial Testing Lead",
    "writing_style": {
        "tone": "Αναλυτικός, σκεπτικιστής, ευθύς, με εστίαση στα edge cases και το ρίσκο",
        "vocabulary_notes": "Χρησιμοποιεί ορολογία AI safety (jailbreaks, prompt injection, blast radius, evals), χωρίς περιττές ευγένειες.",
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


def _get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Λείπει το GEMINI_API_KEY από το .env")
    return genai.Client(api_key=api_key)

@router.put("/persona", tags=["Persona"])
async def update_persona(persona: PersonaModel):
    global CURRENT_PERSONA
    CURRENT_PERSONA = persona.model_dump()
    return {"status": "saved", "persona_id": persona.persona_id}


@router.post("/twin/respond", response_model=TwinDraftResponse, tags=["Twin"])
async def generate_twin_response(payload: TwinRespondRequest):
    try:
        client = _get_gemini_client()
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        draft_id = random.randint(100, 999)

        system_instruction = f"""
Είσαι το Digital Twin του χρήστη με τα εξής στοιχεία:
- Όνομα: {CURRENT_PERSONA.get('name')}
- Ρόλος: {CURRENT_PERSONA.get('role')}
- Ύφος γραφής: {json.dumps(CURRENT_PERSONA.get('writing_style'), ensure_ascii=False)}
- Κανόνες Απόφασης (Decision Heuristics): {json.dumps(CURRENT_PERSONA.get('decision_heuristics'), ensure_ascii=False)}
- Γνώσεις (Knowledge Facts): {json.dumps(CURRENT_PERSONA.get('knowledge_facts'), ensure_ascii=False)}

Οδηγίες:
1. Απάντησε αυστηρά στο ύφος και τη γλώσσα του εισερχόμενου μηνύματος, εφαρμόζοντας τους Κανόνες Απόφασης.
2. Αν το μήνυμα ρωτάει για εμπιστευτικά οικονομικά στοιχεία, budgets ή δεδομένα που ΔΕΝ υπάρχουν στις Γνώσεις σου (anti-hallucination), αρνήσου να μαντέψεις, θέσε confidence_score <= 0.25, is_uncertain = true, και status = "needs_human_input".
3. Διαφορετικά, θέσε status = "pending_approval", is_uncertain = false και υψηλό confidence_score (0.85 - 0.98).
4. Χρησιμοποίησε draft_id = {draft_id}.
"""

        response = client.models.generate_content(
            model=model_name,
            contents=f"Εισερχόμενο μήνυμα:\n{payload.incoming_message}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=TwinDraftResponse,
                temperature=0.3,
            ),
        )

        if not response.text:
            raise RuntimeError("Κενή απόκριση από το Gemini API")

        data = json.loads(response.text)
        data["draft_id"] = draft_id
        return TwinDraftResponse(**data)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gemini Inference Error: {str(exc)}")


@router.post("/twin/approve/{draft_id}", tags=["Twin"])
async def approve_draft(draft_id: int, edited_reply: str = ""):
    return {"status": "approved", "draft_id": draft_id, "final_reply": edited_reply}


@router.post("/ingest", tags=["Ingestion"])
async def ingest_files(files: List[UploadFile] = File(...)):
    filenames = []
    for f in files:
        content = (await f.read()).decode("utf-8", errors="ignore").strip()
        if content:
            # Προσθέτει σύνοψη του αρχείου στις ενεργές γνώσεις της persona
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