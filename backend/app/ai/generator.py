import random
from typing import Dict, Any, List
from .llm_client import call_llm_json, configured_provider

CONFIDENCE_THRESHOLD = 0.45


def build_prompts(
    incoming_message: str,
    persona: Dict[str, Any],
    retrieved_memories: List[str],
) -> tuple[str, str]:
    name = persona.get("name", "Χρήστης")
    role = persona.get("role", "")
    writing_style = persona.get("writing_style", {})
    heuristics = persona.get("decision_heuristics", [])
    facts = persona.get("knowledge_facts", [])

    rules_block = "\n".join(f"- {r}" for r in heuristics) or "- Αξιολόγησε το ρίσκο πριν απαντήσεις."
    facts_block = "\n".join(f"- {f}" for f in facts) or "- Δεν υπάρχουν καταχωρημένα facts."
    memories_block = "\n".join(f"- {m}" for m in retrieved_memories) or "- Καμία σχετική ανάμνηση."

    system_prompt = f"""Είσαι το Digital Twin του/της {name} ({role}).
Απαντάς ΑΠΟΚΛΕΙΣΤΙΚΑ στο ύφος, το λεξιλόγιο και τη λογική αποφάσεων του ατόμου αυτού.

ΥΦΟΣ ΓΡΑΦΗΣ:
- Tone: {writing_style.get("tone", "Αναλυτικός, ευθύς")}
- Vocabulary: {writing_style.get("vocabulary_notes", "Τεχνική ακρίβεια")}

ΚΑΝΟΝΕΣ ΑΠΟΦΑΣΕΩΝ (DECISION HEURISTICS):
{rules_block}

ΓΝΩΣΕΙΣ & FACTS:
{facts_block}

ΑΝΑΚΤΗΜΕΝΕΣ ΜΝΗΜΕΣ (RAG CONTEXT):
{memories_block}

ΑΥΣΤΗΡΟΙ ΚΑΝΟΝΕΣ ANTI-HALLUCINATION:
1. Βασίσου ΜΟΝΟ στους παραπάνω κανόνες, γνώσεις και μνήμες. ΜΗΝ εφευρίσκεις ποσά, ημερομηνίες, συμφωνίες ή στοιχεία που δεν αναφέρονται.
2. Αν το ερώτημα ζητά πληροφορία που ΔΕΝ καλύπτεται από το context (π.χ. οικονομικά/budget/άγνωστα γεγονότα), θέσε confidence_score < 0.35, is_uncertain = true και δήλωσε ρητά ότι παραπέμπεις το θέμα στον ίδιο τον {name}.
3. Επίστρεψε ΜΟΝΟ έγκυρο JSON με ακριβώς τα εξής πεδία:
{{
  "twin_reply": "η απάντηση στα ελληνικά υπογεγραμμένη ως - {name.split()[0]}",
  "confidence_score": 0.0-1.0,
  "is_uncertain": boolean,
  "explanation": {{
    "applied_rules": ["κανόνας 1 που εφαρμόστηκε"],
    "retrieved_memories": ["μνήμη 1 που χρησιμοποιήθηκε"],
    "style_notes": "σύντομη περιγραφή ύφους"
  }}
}}"""

    user_prompt = f"Εισερχόμενο μήνυμα:\n\"\"\"\n{incoming_message}\n\"\"\""
    return system_prompt, user_prompt


def _fallback_response(incoming_message: str, persona: Dict[str, Any], retrieved_memories: List[str]) -> Dict[str, Any]:
    """A truthful no-API fallback: NEVER invent a confident AI decision."""
    return {
        "twin_reply": (
            "Η σύνδεση με το AI απέτυχε. Ελέγξτε το κλειδί, την πρόσβαση στο μοντέλο και τα backend logs."
            if configured_provider() else
            "Δεν υπάρχει διαθέσιμη σύνδεση με μοντέλο AI. Ορίστε νέο OPENAI_API_KEY στο τοπικό .env."
        ),
        "confidence_score": 0.0,
        "is_uncertain": True,
        "explanation": {
            "applied_rules": [],
            "retrieved_memories": retrieved_memories,
            "style_notes": "Η παραγωγή απάντησης δεν εκτελέστηκε (χωρίς LLM).",
        },
    }


def generate_twin_response(
    incoming_message: str,
    persona: Dict[str, Any],
    retrieved_memories: List[str],
) -> Dict[str, Any]:
    """
    Κεντρικό entry point του ai/ module.
    Επιστρέφει πλήρες payload συμβατό με το /api/twin/respond του frontend.
    """
    system_prompt, user_prompt = build_prompts(incoming_message, persona, retrieved_memories)
    llm_result = call_llm_json(system_prompt, user_prompt)

    if not llm_result or "twin_reply" not in llm_result:
        result = _fallback_response(incoming_message, persona, retrieved_memories)
    else:
        confidence = float(llm_result.get("confidence_score", 0.5))
        is_uncertain = bool(llm_result.get("is_uncertain", False)) or (confidence < CONFIDENCE_THRESHOLD)
        explanation = llm_result.get("explanation", {})

        if is_uncertain:
            first_name = persona.get("name", "Μάρκος").split()[0]
            llm_result["twin_reply"] = (
                f"Δεν έχω επαρκή δεδομένα στο αποτύπωμά μου για να απαντήσω με βεβαιότητα. "
                f"Παραπέμπω το αίτημα στον ίδιο τον {first_name}."
            )

        result = {
            "twin_reply": llm_result["twin_reply"],
            "confidence_score": round(max(0.0, min(1.0, confidence)), 2),
            "is_uncertain": is_uncertain,
            "explanation": {
                "applied_rules": explanation.get("applied_rules") or persona.get("decision_heuristics", [])[:2],
                "retrieved_memories": explanation.get("retrieved_memories") or retrieved_memories[:2],
                "style_notes": explanation.get("style_notes") or persona.get("writing_style", {}).get("tone", ""),
            },
        }

    return {
        "draft_id": random.randint(100000, 999999),
        "status": "needs_human_input" if result["is_uncertain"] else "pending_approval",
        **result,
    }