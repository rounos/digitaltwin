import random
from typing import Dict, Any, List
from .llm_client import call_llm_json

CONFIDENCE_THRESHOLD = 0.45


def build_prompts(
    incoming_message: str,
    persona: Dict[str, Any],
    retrieved_memories: List[str],
) -> tuple[str, str]:
    name = persona.get("name", "Μάρκος Βλάχος")
    role = persona.get("role", "AI Red Teamer")
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


def _fallback_response(
    incoming_message: str,
    persona: Dict[str, Any],
    retrieved_memories: List[str],
) -> Dict[str, Any]:
    """Τοπικό fallback αν δεν υπάρχει ενεργό API key στο .env."""
    first_name = persona.get("name", "Μάρκος").split()[0]
    heuristics = persona.get("decision_heuristics", [])
    msg_lower = incoming_message.lower()

    unknown_triggers = ("budget", "τιμή", "κόστος", "μισθ", "συμβόλαιο", "τιμολόγιο")
    if any(k in msg_lower for k in unknown_triggers) and not retrieved_memories:
        return {
            "twin_reply": f"Δεν έχω δεδομένα στο αποτύπωμά μου για οικονομικά στοιχεία ή εμπορικές συμφωνίες. Παραπέμπω το θέμα στον ίδιο τον {first_name}.",
            "confidence_score": 0.19,
            "is_uncertain": True,
            "explanation": {
                "applied_rules": ["Anti-hallucination Guardrail: Παραδοχή άγνοιας όταν λείπουν τεκμήρια"],
                "retrieved_memories": ["Καμία σχετική εγγραφή στο Vector/Memory Store"],
                "style_notes": "Ουδέτερος, ασφαλής τόνος χωρίς εικασίες.",
            },
        }

    applied = heuristics[:2] if heuristics else ["Έλεγχος ρίσκου και blast radius πριν από κάθε έγκριση"]
    memories_used = retrieved_memories[:2] if retrieved_memories else ["Εφαρμογή βασικού προφίλ χωρίς ειδικό RAG hit"]

    return {
        "twin_reply": (
            f"Καλησπέρα. Δεν δίνω έγκριση αν δεν ελεγχθούν πρώτα τα edge cases, τα guardrails και τα σχετικά logs. "
            f"Προχωράμε μόνο με μετρήσιμα τεκμήρια και human-in-the-loop έλεγχο.\n\n- {first_name}"
        ),
        "confidence_score": 0.91,
        "is_uncertain": False,
        "explanation": {
            "applied_rules": applied,
            "retrieved_memories": memories_used,
            "style_notes": persona.get("writing_style", {}).get("tone", "Αναλυτικός, ευθύς"),
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
        "draft_id": random.randint(100, 999),
        "status": "needs_human_input" if result["is_uncertain"] else "pending_approval",
        **result,
    }